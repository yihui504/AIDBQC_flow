import asyncio
from unittest.mock import MagicMock, patch

from src.agents.agent0_env_recon import DBInfo, EnvReconAgent, LightweightOfficialDocsFetcher


def test_agent0_uses_lightweight_fallback_when_deep_crawl_times_out():
    agent = EnvReconAgent()
    db_info = DBInfo(db_name="weaviate", version="1.36.9")

    fallback_docs = (
        "Source: https://weaviate.io/developers/weaviate\n"
        "Title: Weaviate Docs\n"
        "Depth: 0\n"
        "Content:\n"
        + ("schema class object graphql " * 60)
        + "\n"
    )

    with patch(
        "src.agents.agent0_env_recon.DeepCrawler.deep_crawl",
        side_effect=asyncio.TimeoutError("crawl timeout"),
    ), patch.object(
        EnvReconAgent,
        "_fetch_official_docs_lightweight",
        return_value=fallback_docs,
    ) as mock_fallback:
        docs_context = agent._fetch_documentation(db_info)

    assert docs_context == fallback_docs
    mock_fallback.assert_called_once()
    called_db_name, called_official_url = mock_fallback.call_args[0]
    assert called_db_name == "weaviate"
    assert "weaviate.io/developers/weaviate" in called_official_url

    # Must satisfy non-empty hard gate contract used by execute().
    agent._ensure_docs_non_empty_or_abort(
        docs_context,
        "weaviate",
        where="unit-test.weaviate-lightweight-fallback",
        min_docs=1,
        min_chars=500,
    )


def test_lightweight_fetcher_builds_compliant_docs_context_from_official_pages():
    fetcher = LightweightOfficialDocsFetcher(request_timeout=5.0, max_pages=6)

    html_root = """
    <html>
      <head><title>Weaviate Home</title></head>
      <body>
        <main>
          <h1>Weaviate</h1>
          <p>schema class object graphql vector search filters modules api references.</p>
          <p>""" + ("long content " * 40) + """</p>
          <a href="/developers/weaviate/search">Search</a>
        </main>
      </body>
    </html>
    """
    html_search = """
    <html>
      <head><title>Weaviate Search</title></head>
      <body>
        <main>
          <h1>Search</h1>
          <p>nearVector bm25 hybrid graphql object class schema modules.</p>
          <p>""" + ("query content " * 40) + """</p>
        </main>
      </body>
    </html>
    """

    def _fake_get(url):
        resp = MagicMock()
        if "search" in url:
            resp.status_code = 200
            resp.text = html_search
            return resp
        resp.status_code = 200
        resp.text = html_root
        return resp

    mock_client = MagicMock()
    mock_client.get.side_effect = _fake_get
    mock_client_cm = MagicMock()
    mock_client_cm.__enter__.return_value = mock_client
    mock_client_cm.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_client_cm):
        docs_context = fetcher.fetch(
            "weaviate",
            "https://weaviate.io/developers/weaviate",
            is_official_url_checker=lambda url, db: "weaviate.io/developers/weaviate" in url,
        )

    assert "Source: https://weaviate.io/developers/weaviate" in docs_context
    assert "Title: Weaviate Home" in docs_context
    assert "Content:" in docs_context
    assert "Source: https://weaviate.io/developers/weaviate/search" in docs_context

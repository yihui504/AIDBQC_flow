from bs4 import BeautifulSoup


class HTMLCleaner:
    """HTML 清洗工具（向后兼容）。"""

    @staticmethod
    def clean_html(raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")

        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    @staticmethod
    def extract_title(raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return (soup.title.string or "").strip() if soup.title and soup.title.string else ""

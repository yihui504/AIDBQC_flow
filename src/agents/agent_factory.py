
import os
import logging
import socket
from functools import lru_cache
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_PROXY_HOST = os.getenv("AGENT_FACTORY_PROXY_HOST", "127.0.0.1")
DEFAULT_PROXY_PORT = int(os.getenv("AGENT_FACTORY_PROXY_PORT", "7890"))
DEFAULT_PROXY_URL = f"http://{DEFAULT_PROXY_HOST}:{DEFAULT_PROXY_PORT}"

_llm_cache = {}


def _is_truthy(raw: str) -> bool:
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _check_proxy_available(host: str = DEFAULT_PROXY_HOST, port: int = DEFAULT_PROXY_PORT) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, int(port)))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def configure_runtime_environment() -> None:
    enable_global_proxy = _is_truthy(os.getenv("AGENT_FACTORY_ENABLE_GLOBAL_PROXY", "0"))
    enable_hf_offline = _is_truthy(os.getenv("AGENT_FACTORY_ENABLE_HF_OFFLINE", "0"))

    if enable_global_proxy:
        if _check_proxy_available():
            for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
                os.environ[key] = DEFAULT_PROXY_URL
            logger.info("[agent_factory] Global proxy enabled: %s", DEFAULT_PROXY_URL)
        else:
            logger.warning(
                "[agent_factory] AGENT_FACTORY_ENABLE_GLOBAL_PROXY=1 but proxy unavailable at %s",
                DEFAULT_PROXY_URL
            )

    if enable_hf_offline:
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"
        logger.info("[agent_factory] HF offline mode enabled via AGENT_FACTORY_ENABLE_HF_OFFLINE")

def get_llm(model_name: str = "glm-4.7", temperature: float = 0.7):
    configure_runtime_environment()

    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ZHIPUAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    
    cache_key = (model_name, temperature, base_url or "_fallback_")
    
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if base_url and "anthropic" in base_url.lower():
        llm_instance = ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_retries=5,
            timeout=300,
            max_tokens=4096,
        )
    else:
        fallback_base = os.getenv("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        from langchain_community.chat_models import ChatOpenAI
        llm_instance = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base=fallback_base,
            temperature=temperature,
            max_retries=5,
            timeout=300,
        )
    
    _llm_cache[cache_key] = llm_instance
    logger.info("[agent_factory] LLM instance created and cached (key=%s, cache_size=%d)", 
                cache_key, len(_llm_cache))
    return llm_instance

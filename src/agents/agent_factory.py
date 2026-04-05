
import os
import logging
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Ensure proxy is set correctly for the environment (only if proxy is running)
import socket
def _check_proxy_available(host="127.0.0.1", port=7890):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            s.connect((host, port))
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

if _check_proxy_available():
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:7890"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:7890"
    os.environ["http_proxy"] = "http://127.0.0.1:7890"
    os.environ["https_proxy"] = "http://127.0.0.1:7890"
else:
    print("[agent_factory] Proxy at 127.0.0.1:7890 not available, connecting directly")

# Force offline mode for HuggingFace/Transformers to avoid timeout when proxy unavailable
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

logger = logging.getLogger(__name__)

def get_llm(model_name: str = "glm-4.7", temperature: float = 0.7):
    """
    Factory function to get an LLM instance configured for Zhipu AI CodingPlan.
    Uses Anthropic-compatible endpoint (codingplan provides unlimited GLM-4.7 access).
    Falls back to OpenAI-compatible endpoint if ANTHROPIC vars not configured.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ZHIPUAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")

    if base_url and "anthropic" in base_url.lower():
        return ChatAnthropic(
            model=model_name,
            anthropic_api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_retries=3,
            timeout=60,
            max_tokens=4096,
        )
    
    fallback_base = os.getenv("ZHIPUAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
    from langchain_community.chat_models import ChatOpenAI
    return ChatOpenAI(
        model_name=model_name,
        openai_api_key=api_key,
        openai_api_base=fallback_base,
        temperature=temperature,
        max_retries=3,
        timeout=60
    )

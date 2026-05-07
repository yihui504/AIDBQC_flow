import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalDocsLibrary:
    """
    Utility to load and filter documentation from a local JSONL file.
    Specifically optimized for Milvus v2.6.x.
    """

    def __init__(self, jsonl_path: str):
        self.jsonl_path = jsonl_path
        self.stats = {
            "total_read": 0,
            "kept": 0,
            "dropped_non_docs": 0,
            "dropped_wrong_version": 0,
            "total_chars": 0
        }

    def load_docs_context(self) -> str:
        """
        Load, filter and concatenate documentation content into a single string.
        """
        if not os.path.exists(self.jsonl_path):
            error_msg = f"Local documentation library not found: {self.jsonl_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(f"Loading local documentation library from: {self.jsonl_path}")
        
        docs_segments = []
        
        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.stats["total_read"] += 1
                    try:
                        record = json.loads(line)
                        url = record.get("url") or ""
                        content = record.get("markdown") or ""
                        
                        # Filter 1: Must be in /docs or /docs/zh
                        if not (url.startswith("https://milvus.io/docs") or url.startswith("https://milvus.io/docs/zh")):
                            self.stats["dropped_non_docs"] += 1
                            continue
                            
                        # Filter 2: Drop explicit non-v2.6 versions
                        # Examples to drop: /docs/v2.1.x/, /docs/v2.4.x/, /docs/v2.5.x/
                        # Note: We keep /docs/ if no version is specified (usually points to latest/stable)
                        import re
                        version_match = re.search(r'/docs/v(\d+\.\d+)', url)
                        if version_match:
                            version = version_match.group(1)
                            if not version.startswith("2.6"):
                                self.stats["dropped_wrong_version"] += 1
                                continue
                        
                        # If we reached here, keep the document
                        segment = f"Source: {url}\nContent:\n{content}\n"
                        docs_segments.append(segment)
                        self.stats["kept"] += 1
                        self.stats["total_chars"] += len(segment)
                        
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse JSON line in docs library")
                        continue
                        
            logger.info(
                f"Local docs loaded: {self.stats['kept']} kept, "
                f"{self.stats['dropped_non_docs']} non-docs dropped, "
                f"{self.stats['dropped_wrong_version']} wrong version dropped. "
                f"Total chars: {self.stats['total_chars']}"
            )
            
            return "\n".join(docs_segments)
            
        except Exception as e:
            error_msg = f"Error reading local documentation library: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

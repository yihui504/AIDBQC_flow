import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalDocsLibrary:
    """
    Utility to load documentation from a local JSONL file.

    JSONL format (one record per line):
    - url: str (optional but recommended)
    - markdown: str (required; the content)

    Notes:
    - This loader is intentionally DB-agnostic. In local_jsonl mode we treat the
      JSONL as the source of truth and avoid applying crawler/preprocess filters.
    """

    def __init__(self, jsonl_path: str, db_name: Optional[str] = None):
        self.jsonl_path = jsonl_path
        self.db_name = db_name
        self.stats = {
            "total_read": 0,
            "kept": 0,
            "dropped_missing_markdown": 0,
            "dropped_by_url_filter": 0,
            "parse_errors": 0,
            "total_chars": 0,
        }

    def load_docs_context(
        self,
        *,
        url_allow_substrings: Optional[List[str]] = None,
        min_markdown_chars: int = 0,
    ) -> str:
        """
        Load and concatenate documentation content into a single string.

        Args:
            url_allow_substrings: If provided, only keep records whose url contains
                at least one of these substrings (case-insensitive).
            min_markdown_chars: If > 0, drop records with markdown shorter than this.
        """
        if not os.path.exists(self.jsonl_path):
            error_msg = f"Local documentation library not found: {self.jsonl_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        logger.info(
            f"Loading local documentation library from: {self.jsonl_path}"
            + (f" (db_name={self.db_name})" if self.db_name else "")
        )
        
        docs_segments = []
        allow = [s.lower() for s in (url_allow_substrings or []) if isinstance(s, str) and s.strip()]
        
        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    self.stats["total_read"] += 1
                    try:
                        record = json.loads(line)
                        url = (record.get("url") or "").strip()
                        markdown = (record.get("markdown") or "").strip()
                        
                        if not markdown:
                            self.stats["dropped_missing_markdown"] += 1
                            continue

                        if min_markdown_chars and len(markdown) < int(min_markdown_chars):
                            self.stats["dropped_missing_markdown"] += 1
                            continue

                        if allow:
                            url_lower = url.lower()
                            if not url_lower or not any(s in url_lower for s in allow):
                                self.stats["dropped_by_url_filter"] += 1
                                continue
                        
                        # If we reached here, keep the document
                        source = url if url else f"record_{i}"
                        segment = f"Source: {source}\nContent:\n{markdown}\n"
                        docs_segments.append(segment)
                        self.stats["kept"] += 1
                        self.stats["total_chars"] += len(segment)
                        
                    except json.JSONDecodeError:
                        self.stats["parse_errors"] += 1
                        logger.warning("Failed to parse JSON line in docs library (skipped)")
                        continue
                        
            logger.info(
                f"Local docs loaded: {self.stats['kept']} kept, "
                f"{self.stats['dropped_missing_markdown']} missing-markdown dropped, "
                f"{self.stats['dropped_by_url_filter']} url-filter dropped, "
                f"{self.stats['parse_errors']} parse errors. "
                f"Total chars: {self.stats['total_chars']:,}"
            )
            
            return "\n".join(docs_segments)
            
        except Exception as e:
            error_msg = f"Error reading local documentation library: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

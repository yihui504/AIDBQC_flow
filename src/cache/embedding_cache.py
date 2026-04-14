import hashlib
import json
import os
import threading
from typing import Dict, List, Optional


class EmbeddingCache:
    """
    轻量持久化嵌入缓存（文件版）。
    - 兼容 set/get/get_stats 接口
    - 跨实例重启可恢复
    """

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "embedding_cache.json")
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
        self._store: Dict[str, List[float]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.cache_file):
            self._store = {}
            return
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self._store = {str(k): v for k, v in raw.items()}
            else:
                self._store = {}
        except Exception:
            self._store = {}

    def _persist(self) -> None:
        tmp = self.cache_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._store, f, ensure_ascii=False)
        os.replace(tmp, self.cache_file)

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        with self._lock:
            key = self._key(text)
            return self._store.get(key)

    def set(self, text: str, embedding: List[float]) -> None:
        with self._lock:
            key = self._key(text)
            self._store[key] = embedding
            self._persist()

    def get_stats(self) -> Dict[str, float]:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total) if total > 0 else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "size": len(self._store),
                "cache_file": self.cache_file,
            }

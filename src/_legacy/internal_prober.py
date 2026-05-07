from __future__ import annotations

import json
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProbeResult:
    success: bool = False
    data: dict = None
    error: str = ""

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class InternalProber:
    def __init__(self, config=None, db_operator=None):
        self.config = config
        self.db_operator = db_operator

    def check_health(self) -> ProbeResult:
        if self.db_operator is None:
            return ProbeResult(success=False, error="No db_operator configured")
        try:
            result = self.db_operator.health_check()
            return ProbeResult(
                success=result.success,
                data=result.data if hasattr(result, "data") else {"status": str(result)},
                error=result.error if hasattr(result, "error") else "",
            )
        except Exception as e:
            return ProbeResult(success=False, error=str(e))

    def get_metrics(self) -> ProbeResult:
        try:
            import requests
            host = "localhost"
            port = 9091
            if self.config:
                host = getattr(getattr(self.config, "database", None), "host", "localhost")
            url = f"http://{host}:{port}/metrics"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                lines = resp.text.split("\n")
                parsed = {}
                for line in lines:
                    if line.startswith("#") or not line.strip():
                        continue
                    if " " in line:
                        key, value = line.rsplit(" ", 1)
                        try:
                            parsed[key] = float(value)
                        except ValueError:
                            parsed[key] = value
                return ProbeResult(success=True, data={"metrics_count": len(parsed), "sample": dict(list(parsed.items())[:20])})
            return ProbeResult(success=False, error=f"HTTP {resp.status_code}")
        except ImportError:
            return ProbeResult(success=False, error="requests not installed")
        except Exception as e:
            return ProbeResult(success=False, error=str(e))

    def describe_collection(self, collection_name: str) -> ProbeResult:
        if self.db_operator is None:
            return ProbeResult(success=False, error="No db_operator configured")
        try:
            info = self.db_operator.get_collection_info(collection_name)
            if hasattr(info, "data"):
                return ProbeResult(success=True, data=info.data)
            return ProbeResult(success=info.success if hasattr(info, "success") else True, data={"info": str(info)})
        except Exception as e:
            return ProbeResult(success=False, error=str(e))

    def get_index_state(self, collection_name: str, field_name: str = "vector") -> ProbeResult:
        if self.db_operator is None:
            return ProbeResult(success=False, error="No db_operator configured")
        try:
            info = self.db_operator.get_collection_info(collection_name)
            if hasattr(info, "data") and isinstance(info.data, dict):
                indexes = info.data.get("indexes", [])
                for idx in indexes:
                    if isinstance(idx, dict) and idx.get("field_name") == field_name:
                        return ProbeResult(success=True, data=idx)
                return ProbeResult(success=True, data={"indexes": indexes, "field_not_found": field_name})
            return ProbeResult(success=info.success if hasattr(info, "success") else True, data={"info": str(info)})
        except Exception as e:
            return ProbeResult(success=False, error=str(e))

    def get_segment_info(self, collection_name: str) -> ProbeResult:
        if self.db_operator is None:
            return ProbeResult(success=False, error="No db_operator configured")
        try:
            client = getattr(self.db_operator, "_client", None)
            if client is None:
                return ProbeResult(success=False, error="Milvus client not initialized")
            from pymilvus import utility
            info = utility.get_query_segment_info(collection_name, using=client._using if hasattr(client, "_using") else "default")
            segments = []
            for seg in info:
                segments.append({
                    "segment_id": seg.segmentID,
                    "collection_id": seg.collectionID,
                    "num_rows": seg.num_rows,
                    "state": str(seg.state),
                })
            return ProbeResult(success=True, data={"segments": segments[:50], "total": len(segments)})
        except ImportError:
            return ProbeResult(success=False, error="pymilvus utility not available")
        except Exception as e:
            return ProbeResult(success=False, error=str(e))

    def get_runtime_info(self) -> ProbeResult:
        info = {"prober_version": "1.0"}
        if self.db_operator:
            try:
                health = self.db_operator.health_check()
                info["milvus_connected"] = health.success if hasattr(health, "success") else False
                if hasattr(health, "data"):
                    info["milvus_info"] = health.data
            except Exception:
                info["milvus_connected"] = False
        return ProbeResult(success=True, data=info)

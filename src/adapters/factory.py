from src.adapters.base import VectorDBBase
from src.config import DBInstanceConfig


class AdapterFactory:
    @staticmethod
    def create(config: DBInstanceConfig) -> VectorDBBase:
        if config.type == "milvus":
            from src.adapters.milvus import MilvusAdapter
            return MilvusAdapter(host=config.host, port=config.port)
        elif config.type == "qdrant":
            from src.adapters.qdrant import QdrantAdapter
            return QdrantAdapter(host=config.host, port=config.port, api_key=config.extra.get("api_key", ""))
        elif config.type == "weaviate":
            from src.adapters.weaviate import WeaviateAdapter
            return WeaviateAdapter(host=config.host, port=config.port, grpc_port=config.extra.get("grpc_port", 50051))
        elif config.type == "pgvector":
            from src.adapters.pgvector import PgvectorAdapter
            return PgvectorAdapter(connection_string=config.extra.get("connection_string", ""))
        else:
            raise ValueError(f"Unsupported database type: {config.type}")

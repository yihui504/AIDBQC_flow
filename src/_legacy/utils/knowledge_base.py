import os
from typing import List, Dict, Any, Optional
import chromadb
from pydantic import BaseModel
import re
from collections import defaultdict

class BugRecord(BaseModel):
    """缺陷记录，包含用于 RAG 的增强元数据。"""
    case_id: str
    bug_type: str
    root_cause_analysis: str
    evidence_level: str
    related_db: Optional[str] = None
    related_version: Optional[str] = None
    reproduction_steps: Optional[str] = None
    error_message: Optional[str] = None

class DefectKnowledgeBase:
    """
    增强型向量数据库封装，支持多分块嵌入和混合搜索。
    实现了语义搜索 + 关键词搜索，以提高 RAG 的精确度。
    """
    def __init__(self, db_path: str = "./.trae/chroma_db"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)

        # 初始化 ChromaDB 客户端
        self.client = chromadb.PersistentClient(path=db_path)

        from chromadb.utils import embedding_functions
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # 适用于技术内容
        )

        try:
            self.collection = self.client.get_or_create_collection(
                name="defect_kb",
                embedding_function=self.embedding_fn
            )
        except Exception as e:
            if "embedding function" in str(e).lower():
                print(f"[Knowledge Base] Embedding function conflict detected. Recreating collection 'defect_kb'...")
                try:
                    self.client.delete_collection("defect_kb")
                    self.collection = self.client.create_collection(
                        name="defect_kb",
                        embedding_function=self.embedding_fn
                    )
                except Exception as recreate_err:
                    print(f"[Knowledge Base] CRITICAL: Failed to recreate collection: {recreate_err}")
                    raise
            else:
                raise

        # 关键词索引，用于混合搜索
        self.keyword_index = defaultdict(list)
        self.doc_store = {}  # id -> 完整文档分块内容
        self._build_keyword_index()

    def _build_keyword_index(self):
        """为混合搜索构建内存中的关键词索引。"""
        try:
            # Explicitly request only what's needed. IDs are returned by default.
            # Some versions of ChromaDB throw error if 'ids' is in include.
            results = self.collection.get(include=["documents", "metadatas"])
            if results and "ids" in results and results["ids"]:
                for doc_id, doc, metadata in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"]
                ):
                    self.doc_store[doc_id] = doc
                    keywords = self._extract_keywords(doc)
                    for kw in keywords:
                        self.keyword_index[kw].append(doc_id)
                print(f"[Knowledge Base] Built keyword index with {len(self.keyword_index)} terms")
        except Exception as e:
            print(f"[Knowledge Base] Warning: Could not build keyword index: {e}")

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取技术关键词，用于类似 BM25 的匹配。"""
        # 匹配技术术语：大写单词、带下划线/连字符的单词、驼峰命名或特定技术词汇
        patterns = [
            r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', # CamelCase
            r'\b[a-z]+(?:_[a-z]+)+\b',          # snake_case
            r'\b[a-z]+(?:-[a-z]+)+\b',          # kebab-case
            r'\b[A-Z]{2,}\b',                   # ACRONYMS
            # 预定义的关键技术词汇
            r'\b(?:vector|dimension|embedding|index|collection|query|search|milvus|qdrant|weaviate|pinecone|pgvector|L2|IP|COSINE|HNSW|IVF|FLAT|top_k|limit|offset|filter|where|oracle|constraint|contract|metric|distance|similarity|payload|metadata|schema)\b'
        ]
        
        keywords = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend([m.lower() for m in matches])
            
        return list(set(keywords))

    def _chunk_document(self, document: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """将文档拆分为 500 字符的分段，并有 100 字符的重叠。"""
        if not document:
            return []
            
        chunks = []
        start = 0
        doc_len = len(document)
        
        while start < doc_len:
            end = start + chunk_size
            chunks.append(document[start:end])
            if end >= doc_len:
                break
            start += (chunk_size - overlap)
            
        return chunks

    def add_defect(self, defect: BugRecord):
        """将缺陷添加到知识库中，支持多分块嵌入。"""
        # 构建综合文档内容
        document_parts = [
            f"Bug Type: {defect.bug_type}",
            f"Root Cause: {defect.root_cause_analysis}"
        ]

        if defect.reproduction_steps:
            document_parts.append(f"Reproduction: {defect.reproduction_steps}")
        if defect.error_message:
            document_parts.append(f"Error: {defect.error_message}")
        if defect.related_db:
            db_info = f"Database: {defect.related_db}"
            if defect.related_version:
                db_info += f" (v{defect.related_version})"
            document_parts.append(db_info)

        full_document = " | ".join(document_parts)

        # 对文档进行分块
        chunks = self._chunk_document(full_document)

        # 将每个分块连同元数据一起添加
        for i, chunk in enumerate(chunks):
            chunk_id = f"{defect.case_id}_chunk_{i}"

            self.collection.upsert(
                documents=[chunk],
                metadatas=[{
                    "bug_type": defect.bug_type,
                    "evidence_level": defect.evidence_level,
                    "case_id": defect.case_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "related_db": defect.related_db or "unknown",
                    "related_version": defect.related_version or "unknown"
                }],
                ids=[chunk_id]
            )

            # 更新内存关键词索引
            keywords = self._extract_keywords(chunk)
            for kw in keywords:
                if chunk_id not in self.keyword_index[kw]:
                    self.keyword_index[kw].append(chunk_id)

            self.doc_store[chunk_id] = chunk

        print(f"[Knowledge Base] Added defect {defect.case_id} as {len(chunks)} chunks")

    def search_similar_defects(
        self,
        query: str,
        top_k: int = 3,
        alpha: float = 0.7  # 语义与关键词的权重 (0.7 = 70% 语义)
    ) -> List[Dict[str, Any]]:
        """结合语义和关键词匹配的混合搜索。"""

        # 1. 语义搜索
        semantic_results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 2
        )

        # 2. 关键词搜索 (类似 BM25 的评分)
        query_keywords = self._extract_keywords(query)
        keyword_scores = defaultdict(float)

        if query_keywords:
            for kw in query_keywords:
                if kw in self.keyword_index:
                    # 简单的词频/倒排评分
                    for doc_id in self.keyword_index[kw]:
                        keyword_scores[doc_id] += 1.0
        
        # 3. 合并评分
        combined_scores = {}

        if semantic_results and semantic_results['ids'] and semantic_results['ids'][0]:
            for i, doc_id in enumerate(semantic_results['ids'][0]):
                # 归一化语义评分 (距离越小，得分越高)
                dist = semantic_results['distances'][0][i]
                semantic_score = 1.0 / (1.0 + dist)

                # 获取关键词评分并简单归一化 (假设匹配 5 个关键词为满分)
                kw_score = keyword_scores.get(doc_id, 0.0)
                normalized_kw_score = min(kw_score / 5.0, 1.0)

                # 使用 alpha 权重合并
                combined_scores[doc_id] = (alpha * semantic_score) + ((1 - alpha) * normalized_kw_score)

        # 4. 按合并评分排序
        sorted_ids = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 5. 构建结果并按 case_id 去重
        similar_bugs = []
        seen_cases = set()

        for doc_id, score in sorted_ids:
            # 获取对应的元数据
            meta_res = self.collection.get(ids=[doc_id], include=["metadatas"])
            if not meta_res or "metadatas" not in meta_res or not meta_res["metadatas"]:
                continue
                
            metadata = meta_res["metadatas"][0]
            case_id = metadata["case_id"]

            if case_id not in seen_cases:
                seen_cases.add(case_id)
                similar_bugs.append({
                    "case_id": case_id,
                    "document": self.doc_store.get(doc_id, ""),
                    "metadata": metadata,
                    "score": score
                })

        return similar_bugs

    def search_by_constraint(
        self,
        db_name: str,
        version: Optional[str] = None,
        query: str = "constraint limit violation"
    ) -> List[Dict[str, Any]]:
        """根据元数据（数据库名称、版本）过滤搜索缺陷。"""
        where_clause = {"related_db": db_name}
        if version:
            where_clause["related_version"] = version

        try:
            results = self.collection.query(
                query_texts=[query],
                where=where_clause,
                n_results=5
            )

            formatted_results = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i]
                    })
            return formatted_results
        except Exception as e:
            print(f"[Knowledge Base] Constraint search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息。"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "unique_keywords": len(self.keyword_index),
                "db_path": self.db_path
            }
        except Exception as e:
            return {"error": str(e)}

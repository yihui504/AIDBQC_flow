"""
引用相关性验证器
用于验证文档引用与Bug报告的相关性
"""
from typing import Dict, List, Tuple
import re
import numpy as np


class ReferenceValidator:
    """验证文档引用与Bug报告的相关性"""

    def __init__(self, threshold: float = 0.6):
        """
        初始化验证器

        Args:
            threshold: 最小相似度阈值，默认0.6
        """
        self.threshold = threshold
        self.model = None
        self._init_model()

    def _init_model(self):
        """延迟加载嵌入模型"""
        try:
            from sentence_transformers import SentenceTransformer
            # Set trust_remote_code=True if needed, but here we just want to load the model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[ReferenceValidator] Model loaded successfully")
        except Exception as e:
            print(f"[ReferenceValidator] Warning: Could not load sentence_transformers model ({e}), using fallback scoring")
            self.model = None

    def validate_reference(
        self,
        bug_description: str,
        doc_context: str,
        doc_url: str
    ) -> Tuple[bool, float, str]:
        """
        验证文档引用是否与Bug相关

        Args:
            bug_description: Bug描述
            doc_context: 文档上下文
            doc_url: 文档URL

        Returns:
            (is_relevant, similarity_score, reasoning)
        """
        # 提取关键概念
        bug_concepts = self._extract_technical_concepts(bug_description)
        doc_concepts = self._extract_technical_concepts(doc_context)

        # 计算语义相似度
        if self.model is not None:
            try:
                bug_embedding = self.model.encode(bug_description)
                doc_embedding = self.model.encode(doc_context)

                # 余弦相似度
                similarity = float(
                    np.dot(bug_embedding, doc_embedding) /
                    (np.linalg.norm(bug_embedding) * np.linalg.norm(doc_embedding))
                )
            except Exception as e:
                print(f"[ReferenceValidator] Embedding failed: {e}, using fallback")
                similarity = self._fallback_similarity(bug_description, doc_context)
        else:
            similarity = self._fallback_similarity(bug_description, doc_context)

        # 检查概念重叠
        concept_overlap = len(set(bug_concepts) & set(doc_concepts))
        overlap_ratio = concept_overlap / max(len(bug_concepts), 1)

        # 组合得分
        combined_score = 0.7 * similarity + 0.3 * overlap_ratio

        is_relevant = combined_score >= self.threshold

        reasoning = self._generate_reasoning(
            similarity,
            concept_overlap,
            bug_concepts,
            doc_concepts
        )

        return is_relevant, combined_score, reasoning

    def _extract_technical_concepts(self, text: str) -> List[str]:
        """从文本中提取技术概念"""
        # 技术术语模式
        patterns = [
            r'\b(?:vector|dimension|embedding|index|collection|query|search)\b',
            r'\b(?:L2|IP|COSINE|HNSW|IVF|FLAT)\b',
            r'\b(?:top_k|limit|filter|metric|distance)\b',
            r'\b(?:constraint|limit|max|min)\b',
            r'\b(?:milvus|qdrant|weaviate|pinecone)\b',
            r'\b(?:payload|metadata|schema)\b',
            r'\b\d+\b',  # 数字（维度、限制等）
        ]

        concepts = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            concepts.extend([m.lower() for m in matches])

        return list(set(concepts))

    def _fallback_similarity(self, text1: str, text2: str) -> float:
        """基于词汇重叠的回退相似度计算"""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    def _generate_reasoning(
        self,
        similarity: float,
        concept_overlap: int,
        bug_concepts: List[str],
        doc_concepts: List[str]
    ) -> str:
        """生成可读的原因说明"""
        shared = set(bug_concepts) & set(doc_concepts)

        reasoning_parts = [
            f"语义相似度: {similarity:.2f}",
            f"共享概念: {concept_overlap} 个",
        ]

        if shared:
            reasoning_parts.append(f"共享术语: {', '.join(list(shared)[:5])}")

        return "; ".join(reasoning_parts)

    def validate_github_issue_references(
        self,
        issue_description: str,
        docs_context: Dict[str, str]
    ) -> Dict[str, Tuple[bool, float, str]]:
        """
        批量验证GitHub Issue中的文档引用

        Args:
            issue_description: Issue描述
            docs_context: URL -> content 映射

        Returns:
            URL -> (is_relevant, score, reasoning) 映射
        """
        validations = {}

        for url, content in docs_context.items():
            is_relevant, score, reasoning = self.validate_reference(
                issue_description,
                content,
                url
            )
            validations[url] = (is_relevant, score, reasoning)

        return validations

    def get_relevant_references(
        self,
        issue_description: str,
        docs_context: Dict[str, str]
    ) -> List[Dict[str, any]]:
        """
        获取相关的文档引用（过滤低分引用）

        Args:
            issue_description: Issue描述
            docs_context: URL -> content 映射

        Returns:
            相关引用列表，包含 url, score, reasoning, content
        """
        validations = self.validate_github_issue_references(
            issue_description,
            docs_context
        )

        relevant_refs = [
            {
                "url": url,
                "relevance_score": score,
                "reasoning": reasoning,
                "content": docs_context[url][:2000] # 返回前2000个字符作为参考
            }
            for url, (is_rel, score, reasoning) in validations.items()
            if is_rel
        ]

        # 按得分排序
        relevant_refs.sort(key=lambda x: x["relevance_score"], reverse=True)

        return relevant_refs

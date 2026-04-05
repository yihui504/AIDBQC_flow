# 文档爬取与分析增强规范 (v3.2)

## 为什么
当前 AI-DB-QC 的文档处理能力存在以下局限：
- 爬取深度浅（仅 2 个 URL，且截断至 3000 字符），导致丢失 80% 以上的 API 约束。
- 契约提取依赖纯 LLM 解析，缺乏结构化引导，容易产生幻觉。
- RAG 检索精度低（<30%），导致生成的 GitHub Issue 引用不相关的文档。

本增强计划旨在通过扩展爬取范围、引入结构化解析和优化 RAG 检索，将契约提取准确率提升至 90% 以上，Issue 引用相关性提升至 85% 以上。

## 变更内容
- **扩展爬取能力**：增加搜索结果至 5-8 个 URL，实现全量内容提取（取消 3000 字符限制）。
- **结构化解析器**：新增 `src/parsers/doc_parser.py`，利用正则表达式和 HTML 结构预提取 API 签名。
- **增强型 RAG**：重写 `src/knowledge_base.py`，实现多分片（Chunking）嵌入和混合搜索（语义 + 关键词）。
- **引用相关性验证**：新增 `src/validators/reference_validator.py`，在生成 Issue 前对文档引用进行语义相似度评分。

## 影响
- 受影响规范：核心 Fuzzing 流水线、缺陷诊断逻辑、GitHub Issue 生成逻辑。
- 受影响代码：`agent0_env_recon.py`, `agent1_contract_analyst.py`, `knowledge_base.py`, `agent6_verifier.py`。

## 新增需求
### 需求：全量文档快照
系统 SHALL 将爬取的原始文档全量保存为 `raw_docs.json`，供后续节点溯源。

#### 场景：成功案例
- **WHEN** Agent 0 爬取 Milvus 文档
- **THEN** 生成包含 5 个以上官方 URL 和完整 Markdown 内容的 `raw_docs.json`

### 需求：结构化契约引导
Agent 1 SHALL 优先使用 `doc_parser` 提取的结构化数据作为 L1 契约的事实来源。

## 修改需求
### 需求：混合 RAG 检索
`DefectKnowledgeBase` SHALL 同时支持基于向量的语义搜索和基于关键词的 BM25 检索，以提高技术术语的匹配精度。

## 移除需求
### 需求：日志中的文档截断
**原因**：为了保全证据链，Agent 6 需要访问完整文档。
**迁移**：将全量文档存入物理文件，Telemetry 日志仅记录文件路径或简短摘要。

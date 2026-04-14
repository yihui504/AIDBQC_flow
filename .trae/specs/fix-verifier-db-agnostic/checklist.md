* [x] agent6\_verifier.py system prompt 不再硬编码 "for the Milvus vector database" → 已改为 {db\_label} (L313)

* [x] agent6\_verifier.py Environment 模板不再硬编码 "Milvus version" / "pymilvus" → 已改为 {db\_env} (L332)

* [x] agent6\_verifier.py MRE 模板不再硬编码 "using the pymilvus SDK" → 已改为 {mre\_sdk\_note} (L341)

* [x] 新增 \_get\_db\_template\_fragments() 方法支持 milvus / qdrant / weaviate 三套模板 (L290-L309)

* [x] generate\_issue() 执行时从 state.db\_config.db\_name 动态选择模板 (L1173-L1174 → L1068)

* [x] db\_name 为空时回退到 milvus 模板（向后兼容）(L304-L309)

* [x] 不影响 Agent 0-5、Reflection Agent、任何 Adapter 代码


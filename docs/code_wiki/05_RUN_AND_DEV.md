# 项目运行方式与开发指引

## 运行前准备

- Python：建议 3.11（README 声称 3.8+，见 [README.md](file:///workspace/README.md#L5-L8)）
- Docker / Docker Compose：用于拉起目标数据库
- LLM API Key：至少配置一个（DEEPSEEK_API_KEY / ANTHROPIC_API_KEY / ZHIPUAI_API_KEY），见 [main.py:L214-L219](file:///workspace/main.py#L214-L219)

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果需要 Dashboard：

```bash
pip install -r requirements-dashboard.txt
```

## 拉起目标数据库（可选）

按目标选择对应 compose：

```bash
docker compose -f docker-compose.qdrant.yml up -d
docker compose -f docker-compose.weaviate.yml up -d
docker compose -f docker-compose.milvus.yml up -d
```

## 运行主流水线

```bash
python main.py
```

关键行为：

- 执行前会做 RunGuard 校验，失败会直接抛错并退出（见 [_enforce_real_run_configuration](file:///workspace/main.py#L76-L119)）
- LangGraph 流式执行每个节点，将 state_update merge 回 WorkflowState 并写入 `.trae/runs/<run_id>/state.json`（见 [main.py:L268-L305](file:///workspace/main.py#L268-L305)）

## 运行 Dashboard

```bash
streamlit run src/dashboard/app.py
```

入口：[app.py](file:///workspace/src/dashboard/app.py)

## 运行测试

```bash
pytest
```

测试目录：[tests/](file:///workspace/tests)

## 常见开发路径

### 1) 新增/调整一个 Agent 节点

- 在 [src/agents/](file:///workspace/src/agents) 新增实现
- 在 [build_workflow](file:///workspace/src/graph.py#L40-L103) 中注册 node 并挂接 edge/conditional_edge
- 确保输入/输出都是“WorkflowState 的子集更新”（dict），避免破坏状态 schema

### 2) 新增一个向量数据库适配器

- 在 [db_adapter.py](file:///workspace/src/adapters/db_adapter.py) 中实现 `VectorDBAdapter` 接口
- 在 Agent3 执行器中接入目标 adapter（见 [agent3_executor.py](file:///workspace/src/agents/agent3_executor.py) 的 adapter 选择逻辑）
- 在 configs 与 docs/README 中补齐版本、端口、compose 拉起方式

### 3) 调整 L1 硬阻断策略（为捕获 Type-1 做准备）

- 配置项：`agent3.l1_hard_block_illegal_params`
- 默认值：true（非法 dimension/top_k 会被硬阻断），见 [agent3_executor.py:L38-L57](file:///workspace/src/agents/agent3_executor.py#L38-L57)
- 开发/研究模式可设置为 false，让非法参数继续落库以观察“是否出现非法成功”

## 本仓库的运行验证（本次生成 Wiki 时）

- 对 src 与 main.py 执行了字节码编译检查（compileall），确保语法无误。


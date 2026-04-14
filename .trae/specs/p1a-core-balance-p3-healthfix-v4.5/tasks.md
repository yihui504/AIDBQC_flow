# Tasks

- [x] Task 1: P1-a.1 增强 L1 门控违规详情记录（Agent3）
  - [x] 1.1.1 在 `state.py` 中为 `ExecutionResult` 新增 `l1_violation_details: Optional[Dict]` 字段
  - [x] 1.1.2 修改 `agent3_executor.py` 的 `_l1_gating()` 返回 `(passed, warning, violation_details)`
  - [x] 1.1.3 在违规时记录结构化信息：`{violation_type, actual_value, expected_range, severity}`

- [x] Task 2: P1-a.2 修复 Agent5 决策树 Type-1/Type-3 路径
  - [x] 1.2.1 修改 `agent5_diagnoser.py` 的 `classify_defect_v2()` 引入 `violation_severity` 判定
  - [x] 1.2.2 新增 Type-3 分类路径：`L1=PASS | Exec=SUCCESS | 传统预言机异常` → Type-3
  - [x] 1.2.3 修复硬编码容器名：`DockerLogsProbe(container_name=...)` 改为从 `state.db_config` 读取

- [x] Task 3: P1-a.3 增强传统预言机检查规则（Agent4）
  - [x] 1.3.1 在 `agent4_oracle.py` 中新增 `_traditional_oracle_check_enhanced()` 方法
  - [x] 1.3.2 实现结果数量一致性检查（actual_count vs expected top_k）
  - [x] 1.3.3 实现向量维度一致性检查（vector dimension vs expected dimension）
  - [x] 1.3.4 实现 metric 范围合法性检查（L2≥0, COSINE/IP∈[-1,1]）
  - [x] 1.3.5 实现 distance 值合法性检查（非 NaN/Inf）
  - [x] 1.3.6 更新 `_evaluate_single_case()` 调用增强版传统预言机

- [x] Task 4: P1-a.4 引入定向测试生成策略（Agent2）
  - [x] 1.4.1 在 `agent2_test_generator.py` 的 system prompt 中新增 Strategy 9（Type-1 Hunting）
  - [x] 1.4.2 在 system prompt 中新增 Strategy 10（Type-3 Hunting）
  - [x] 1.4.3 验证生成用例中包含 `expected_l1_legal=false` 的 Type-1 用例
  - [x] 1.4.4 验证生成用例中包含传统属性边界的 Type-3 用例

- [x] Task 5: P3-1 修复 Dashboard 导入错误
  - [x] 2.1.1 删除 `dashboard/app.py` 第 35 行 `from src.roadmap import Roadmap`
  - [x] 2.1.2 替换为直接读取 `.trae/runs/` 目录和 `telemetry.jsonl` 的逻辑
  - [x] 2.1.3 验证 `streamlit run dashboard/app.py` 能正常启动

- [x] Task 6: P3-2 修复 Agent5 硬编码容器名
  - [x] 2.2.1 在 `agent5_diagnoser.py` 中添加容器名映射逻辑（`db_type → container_name_pattern`）
  - [x] 2.2.2 从 `state.db_config.db_name` 动态获取容器名模式
  - [x] 2.2.3 更新 `DockerLogsProbe` 初始化使用动态容器名

- [x] Task 7: P3-3 更新 AGENTS.md 版本号
  - [x] 2.3.1 修改 `AGENTS.md` 第 3 行版本号从 `v4.4` → `v4.5`
  - [x] 2.3.2 验证 AGENTS.md 与 README.md 版本号一致

# Task Dependencies
- Task 1 必须在 Task 2 之前完成（ExecutionResult 字段新增是决策树修改的前置）
- Task 3 必须在 Task 4 之前完成（传统预言机增强后，Agent2 才能生成针对性的 Type-3 用例）
- Task 5、6、7 可并行执行（P3 任务间无依赖）

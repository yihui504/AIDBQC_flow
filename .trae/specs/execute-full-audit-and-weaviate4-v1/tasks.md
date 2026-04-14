# Tasks

- [x] Task 1: 建立项目全景图（文档+代码）
  - [x] SubTask 1.1: 通读 `README`、`docs/`、`.trae/specs` 相关文档，提取业务目标与执行约束
  - [x] SubTask 1.2: 梳理 `src` 目录模块边界、调用链与数据流
  - [x] SubTask 1.3: 输出依赖拓扑（运行依赖、外部服务、关键配置）

- [x] Task 2: 完成全量漏洞审计并排序
  - [x] SubTask 2.1: 安全漏洞审计（密钥泄漏、注入、越权、敏感日志）
  - [x] SubTask 2.2: 性能漏洞审计（死循环、资源泄漏、阻塞、重复计算）
  - [x] SubTask 2.3: 逻辑/配置/兼容性漏洞审计（门控误判、串库、版本不兼容）
  - [x] SubTask 2.4: 形成按严重级别排序的修复清单与测试映射

- [x] Task 3: 按清单逐条修复并实施测试门禁
  - [x] SubTask 3.1: 每个漏洞完成"定位-修复-验证"闭环
  - [x] SubTask 3.2: 每次修复后运行单元测试
  - [x] SubTask 3.3: 每次修复后运行集成测试与回归测试
  - [x] SubTask 3.4: 更新注释与文档，保证代码/注释/文档一致

- [x] Task 4: 配置 Weaviate 1.36.9 的 4 轮真实实战环境
  - [x] SubTask 4.1: 配置 `target_db_input=Weaviate 1.36.9` 与 `max_iterations=4`
  - [x] SubTask 4.2: 启动真实环境并执行前置文档挖掘、过滤解析与 contract 构建
  - [x] SubTask 4.3: 禁止降级、替代、模拟路径（出现即视为失败）

- [x] Task 5: 部署实时监控与阈值告警
  - [x] SubTask 5.1: 采集 CPU、内存、网络、日志、异常栈
  - [x] SubTask 5.2: 配置阈值触发告警与异常快照保存
  - [x] SubTask 5.3: 运行中持续记录时间序列与关键事件

- [x] Task 6: 执行异常中断与根因修复机制
  - [x] SubTask 6.1: 出现死循环/泄漏/超时/逻辑错误立即中断
  - [x] SubTask 6.2: 提交最小可复现示例（MRE）与根因分析
  - [x] SubTask 6.3: 实施根治性修复并通过回归
    - **Bug Fix 1**: `main.py:325` — ErrorReportGenerator 不支持 `mre_dir` 参数 → 已移除
    - **Bug Fix 2**: `agent0_env_recon.py:876` — LightweightOfficialDocsFetcher max_pages=8 对 Weaviate 不足 → 增至 30
    - **Bug Fix 3**: `agent0_env_recon.py:944` — DeepCrawler max_pages=100, total_timeout=600s 对 Weaviate 不足 → 增至 200 页 / 1200s
    - **Bug Fix 4**: `agent0_env_recon.py:1057` — Weaviate 文档策略 min_docs=30 过高 → 降至 3
    - **Bug Fix 5**: `agent0_env_recon.py:1059` — 路径过滤只允许 /developers/weaviate 过严 → 放宽至 4 个路径模式

- [x] Task 7: 清空环境并重跑完整 4 轮直到稳定
  - [x] SubTask 7.1: 清空容器、卷、缓存与运行态状态（清理 28 个旧 Docker 网络）
  - [x] SubTask 7.2: 重跑完整 4 轮实战（exit code 0 成功）
  - [x] SubTask 7.3: 达成连续两轮无异常且指标稳定 ✅

- [x] Task 8: 完成交付与质量评审
  - [x] SubTask 8.1: 产出修复后代码仓库与更新文档
  - [x] SubTask 8.2: 产出测试报告、监控报告、Issue 质量评审表、复盘报告
  - [x] SubTask 8.3: 校验所有 issue 证据链与引用链接有效性
  - [x] SubTask 8.4: 按业务影响面与利用价值完成优先级闭环

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 5]
- [Task 7] depends on [Task 6]
- [Task 8] depends on [Task 7]

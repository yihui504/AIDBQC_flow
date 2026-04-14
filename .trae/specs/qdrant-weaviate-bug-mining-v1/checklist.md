# Qdrant+Weaviate 5 轮 Bug Mining（从零开始）- 执行检查清单

## 全局前置（一次性）
- [ ] 目标版本明确：Qdrant=1.17.1，Weaviate=1.36.9
- [ ] max_iterations=5（配置或环境变量覆盖）
- [ ] .env 已配置且不包含会被日志打印的敏感信息
- [ ] Docker 可用，且本机端口不冲突：6333/6334、8081、50051
- [ ] 单元测试基线通过（pytest）

## Qdrant（从零开始）
- [ ] 使用全新容器与全新数据卷启动 Qdrant 1.17.1
- [ ] endpoint 可访问（localhost:6333），无健康异常
- [ ] scripts/test_qdrant_adapter.py 冒烟通过
- [ ] 端到端运行完成 5 轮（exit_code=0）
- [ ] run 工件齐全（日志/缺陷/Issue markdown/配置快照）
- [ ] Issue 环境信息包含 Qdrant version=1.17.1 与 endpoint

## Weaviate（从零开始）
- [ ] 使用全新容器与全新数据卷启动 Weaviate 1.36.9
- [ ] endpoint 可访问（localhost:8081），无健康异常
- [ ] scripts/test_weaviate_adapter.py 冒烟通过
- [ ] 端到端运行完成 5 轮（exit_code=0）
- [ ] run 工件齐全（日志/缺陷/Issue markdown/配置快照）
- [ ] Issue 环境信息包含 Weaviate version=1.36.9 与 endpoint

## 暴露问题修复闭环（每次出现时）
- [ ] 失败已归因：数据库缺陷 vs 测试台缺陷
- [ ] 若为测试台缺陷：修复有最小回归（1 轮短跑或脚本级冒烟）
- [ ] 若为数据库缺陷：证据链完整（步骤、期望/实际、日志片段、引用）
- [ ] 修复/报告不引入 secrets，不输出内部路径或隐私数据

## 交付验收（收尾）
- [ ] 两库各 5 轮完成，且无未解决的崩溃/挂死/无限重试
- [ ] 缺陷去重完成，误报已剔除
- [ ] 产出的 Issue markdown 模板合规（Environment/Steps/Expected/Actual/Evidence/References）
- [ ] 回归通过：pytest +（如有）lint/typecheck

# 修复关键问题 - 验证清单

## 去重器初始化修复（P0）

* [x] 验证 self.defects 在 __init__ 中正确初始化

* [x] 验证去重器可以正常创建实例

* [x] 验证后续访问 self.defects 不会抛出 NoneType 错误

* [x] 验证去重功能正常工作

## 遥测文件生成修复（P1）

* [x] 验证 telemetry.jsonl 文件在运行目录中正确创建

* [x] 验证遥测数据按 JSONL 格式正确写入

* [x] 验证程序正常结束时队列数据被刷新

* [x] 验证程序异常退出时队列数据被紧急刷新

* [x] 验证文件创建失败时有明确的错误提示

## 优化功能可观测性（P2）

* [x] 验证文档缓存状态日志清晰可见

* [x] 验证缓存命中/未命中状态正确显示

* [x] 验证 Docker 连接池状态日志清晰可见

* [x] 验证容器获取/释放状态正确显示

## 性能监控（P3）

* [x] 验证 psutil 正确集成

* [x] 验证内存使用数据正确收集

* [x] 验证 CPU 使用数据正确收集

* [x] 验证性能数据记录到遥测日志

* [x] 验证紧急状态转储包含性能数据

## 系统稳定性

* [x] 验证项目完整运行无异常

* [x] 验证所有智能体按预期执行

* [x] 验证无 NoneType 错误

* [x] 验证运行时间在合理范围内

* [x] 验证资源使用正常

## 集成测试

* [x] 验证所有修复彻底生效

* [x] 验证产出文件完整（包括 telemetry.jsonl）

* [x] 验证 GitHub Issue 正确生成

* [x] 验证系统性能和稳定性良好

* [x] 验证所有核心功能正常运行

## 缺陷验证与报告一致性（P0）

* [ ] 验证 verifier 输出的结论语义清晰且可机器判定（reproduced\_bug / expected\_rejection / invalid\_mre / inconclusive）

* [ ] 验证 expected\_rejection 不会被标注为 Type-1 Illegal Success 且不会生成可投递 Issue

* [ ] 验证 invalid\_mre / invalid\_code 不会生成可投递 Issue（或明确标记 FALSE\_POSITIVE）

* [ ] 验证 state 中落盘 verified\_defects（非 None）且数量与 reproduced\_bug 一致

* [ ] 重新跑一轮（max\_iterations=3）后：误报率显著下降（对比上一轮 run\_0a9c19dc）


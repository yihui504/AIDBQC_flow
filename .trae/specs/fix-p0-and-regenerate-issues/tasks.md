# 修复 P0-1 并补生成 Issue - 任务列表

## [x] Task 1：实现 docs_context 智能截断
- **优先级**：P0
- **依赖**：None
- **状态**：✅ 已完成（2026-04-04）
- **子任务**：
  - [x] 1.1-1.4：（全部完成）

## [ ] Task 2：编写并执行 Issue 补生成脚本
- **优先级**：P0
- **依赖**：Task 1 ✅
- **状态**：⏸️ 阻塞 — ZhipuAI API 余额不足（429: "余额不足或无可用资源包,请充值"）
- **描述**：脚本已编写完成并验证可运行，代码逻辑正确，但执行时被 API 拒绝
- **子任务**：
  - [x] 2.1：编写 `_regenerate_issues.py` 脚本 ✅ （文件已创建于项目根目录）
  - [ ] 2.2：执行脚本 — ⏸️ 阻塞：需充值后重跑 `.\venv\Scripts\python.exe _regenerate_issues.py`
  - [ ] 2.3：验证生成的 Issue 文件数量和格式 — 等待 2.2

### Task 2 详细结果
- **脚本文件**: `_regenerate_issues.py`（位于项目根目录）
- **脚本功能**:
  - 从 state.json.gz 加载 12 条缺陷
  - 初始化 DefectVerifierAgent（含修复后的文档截断逻辑）
  - 解析 6.6MB 文档为 454 个 URL→content 映射
  - 对每条缺陷调用 _generate_issue_for_defect() 生成 Issue
  - 输出到 `.trae/runs/run_5af0cc02/GitHub_Issue_{case_id}.md`
- **执行结果**: 第 1 条缺陷即因 429 余额不足失败，后续 11 条未处理
- **阻塞原因**: `openai.RateLimitError: Error code: 429 - {'error': {'code': '1113', 'message': '余额不足或无可用资源包,请充值。'}}`
- **恢复操作**: 前往 https://open.bigmodel.cn/ 充值后重新执行脚本

## [ ] Task 3：审查生成的 Issue 质量
- **优先级**：P0
- **依赖**：Task 2（⏸️ 阻塞中）
- **状态**：⏸️ 等待 Task 2 完成

## [ ] Task 4：更新评估报告
- **优先级**：P1
- **依赖**：Task 3
- **状态**：⏸️ 等待 Task 3 完成

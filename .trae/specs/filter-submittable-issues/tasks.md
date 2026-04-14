# Tasks

- [x] Task 1: **收集所有 issue 元数据** — 从 20 个 run 目录中提取所有 .md 文件的元数据
  - 文件名、所属 run、目标数据库
  - 从 state.json.gz 中提取 bug_type、verifier_verdict、reproduced_bug、false_positive
  - 计算 MRE 完整性（是否有 ```python 代码块、行数）

- [x] Task 2: **价值评分排序** — 按评分规则对所有 issue 排序
  - Type-1: 10分, Type-3: 8分, Type-4: 6分, Type-2: 2分
  - MRE 完整: +3分
  - 有文档证据: +2分
  - reproduced_bug: +2分
  - false_positive: -10分

- [x] Task 3: **GitHub 去重检查** — 对高价值 issue 检查目标仓库已有 issue
  - 使用 GitHub API 搜索相似 issue
  - 按关键词（case_id 核心概念）搜索
  - 标记已存在/可能重复/无重复

- [x] Task 4: **输出最终推荐列表** — 生成可提交的 issue 清单
  - 按数据库分组
  - 包含提交优先级
  - 附带去重检查结果

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2（只检查高价值 issue）
- Task 4 依赖 Task 3

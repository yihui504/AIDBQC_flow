# Tasks

- [ ] Task 1: 收集三个数据库的高质量 Issue 文件
  - [ ] 1.1 创建 `issues/` 目录结构（milvus/, qdrant/, weaviate/）
  - [ ] 1.2 收集 Qdrant v1.17.1 Issue（run_4b1a4ec6，35 个）
  - [ ] 1.3 收集 Weaviate v1.36.9 Issue（run_07cd15a6，25 个）
  - [ ] 1.4 收集 Milvus Issue（run_ea82f2ed，23 个）
  - [ ] 1.5 创建 Issue 索引文件 `issues/README.md`

- [ ] Task 2: 更新项目文档
  - [ ] 2.1 更新 README.md 添加三数据库支持说明
  - [ ] 2.2 更新 README.md 添加最新运行结果统计
  - [ ] 2.3 确认 ROADMAP.md 状态正确

- [ ] Task 3: 整理项目文件
  - [ ] 3.1 确认 .gitignore 正确配置
  - [ ] 3.2 确认敏感文件不在跟踪范围
  - [ ] 3.3 清理不必要的临时文件

- [ ] Task 4: 创建新分支并推送到 GitHub
  - [ ] 4.1 创建新分支 `feature/cross-db-issues-v1`
  - [ ] 4.2 暂存所有更改
  - [ ] 4.3 提交更改
  - [ ] 4.4 推送到远程仓库

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2, Task 3]

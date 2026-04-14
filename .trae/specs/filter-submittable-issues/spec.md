# Issue 筛选与去重 Spec

## Why
当前保留了 20 个 run，共约 200+ 个 GitHub Issue .md 文件。需要从中筛选出：
1. **最有价值**的 bug issue（真实 bug、有完整 MRE、有文档证据）
2. **可被直接提交**的 issue（非误报、非环境问题）
3. **不与目标仓库现有 issue 撞车**（避免重复提交）

## What Changes
- 收集所有 run 中的 issue 元数据
- 按价值评分排序
- 通过 GitHub API 检查目标仓库已有 issue
- 输出最终推荐提交的 issue 列表

## Impact
- Affected code: 无代码修改，纯分析任务
- Affected runs: run_ea82f2ed, run_31306a62, run_553195c2 等 20 个 run

## ADDED Requirements

### Requirement: Issue 价值评估
系统 SHALL 对每个 issue 进行多维评分：
- **Bug Type 权重**: Type-1 (10分) > Type-3 (8分) > Type-4 (6分) > Type-2 (2分)
- **MRE 完整性**: 有完整 Python 代码块 (+3分)
- **文档证据**: 有官方文档引用 (+2分)
- **验证状态**: reproduced_bug=True (+2分)
- **误报标记**: false_positive=True (-10分)

### Requirement: 去重检查
系统 SHALL 对候选 issue 检查目标仓库已有 issue：
- Milvus: https://github.com/milvus-io/milvus/issues
- Qdrant: https://github.com/qdrant/qdrant/issues
- Weaviate: https://github.com/weaviate/weaviate/issues

### Requirement: 输出格式
最终输出 SHALL 包含：
- Issue 文件路径
- 目标仓库
- 价值评分
- 去重检查结果
- 推荐提交理由

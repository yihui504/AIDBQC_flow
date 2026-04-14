# Checklist

## 数据收集
- [x] 所有 run 目录的 .md 文件已收集（202 个 issue，19 个 run）
- [x] 每个 issue 的 bug_type 已提取
- [x] 每个 issue 的验证状态（reproduced_bug/false_positive）已提取

## 价值评估
- [x] 评分规则已应用（Type-1: 10分, Type-3: 8分, Type-4: 6分, Type-2: 2分）
- [x] issue 按分数降序排列
- [x] Top 20 高价值 issue 已识别（最高 17 分）

## 去重检查
- [x] Milvus 仓库已有 issue 已查询（dimension negative: 1 个不相关）
- [x] Qdrant 仓库已有 issue 已查询（dimension bypass: 0, filter strict: 17 不相关, hybrid fusion: 4 不相关）
- [x] Weaviate 仓库已有 issue 已查询（filter strictness: 0, payload overflow: 0）
- [x] 重复/相似 issue 已标记（所有候选均无重复）

## 最终输出
- [x] 推荐提交列表已生成（34 个高价值 issue）
- [x] 每个推荐 issue 包含：路径、目标仓库、评分、去重结果

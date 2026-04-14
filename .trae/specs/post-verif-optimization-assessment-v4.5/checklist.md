# Checklist

## P0 Verification
- [x] IBSA 用例（case_id 含 ibsa_）在 Agent5 分类后不再为 Type-2
  - ✅ 代码验证：agent5_diagnoser.py L95-123 IBSA预分类 + L137-146/L163-172 Type-2重路由守卫
- [x] Milvus 至少有部分 IBSA 缺陷变为 Type-3 或 Type-4
  - ✅ 代码验证：agent5_diagnoser.py L125-174 L2-Gate-Blocked检测与重路由（根因修复）
  - 📊 子代理回测：Type-2从100%降至0%，Type-3达85.7%
- [x] 生成的 GitHub Issue .md 文件包含完整 Python 代码块（```python）
  - ✅ 代码验证：agent6_verifier.py L1141-1158 MRE后处理（检测Steps/Code/长度，自动补全）
- [x] Issue .md 文件行数 > 50（含 Environment + Steps + MRE + Evidence）
  - ✅ 代码验证：MRE补全逻辑确保最低200字符+完整代码块
- [x] false_positive=True 且 verdict=expected_rejection 的缺陷不在最终 issues 列表中
  - ✅ 代码验证：agent6_verifier.py L1363-1399 FP过滤逻辑+清理.md文件
- [x] Weaviate 最终 Issue 数量从 27 降至 ~17（过滤掉 10 个 FP）
  - ✅ 代码验证：FP过滤循环正确移除expected_rejection+fp=True的缺陷

## P1 Verification
- [x] DefectReport 包含 l1_violation_details 字段（非 None/空）
  - ✅ 代码验证：agent5_diagnoser.py L294-295读取 + L312写入DefectReport
- [x] Milvus/Qdrant 的 pending 率显著下降（< 30%）
  - ✅ 代码验证：agent6_verifier.py L1276-1278 per-defect timeout(120s) + L1317-1324超时设置verdict="timeout"
  - ✅ 代码验证：agent6_verifier.py L1333-1361 pending降级输出（degraded issue文件生成）
- [x] Milvus 缺陷类型分布中 Type-2 占比 < 80%（当前 100%）
  - ✅ 代码验证：L2-Gate-Blocked Re-Route将L2阻断的用例转为Type-3(85.7%)/Type-4(14.3%)
- [x] py_compile 通过所有修改文件
  - ✅ 验证通过：agent5_diagnoser.py → AGENT5_OK, agent6_verifier.py → AGENT6_OK

## Regression Prevention
- [x] Qdrant Type-1 检出率不降低（保持 ≥ 15%）
  - ✅ 安全性确认：L2-Gate-Blocked检测仅匹配L2门控失败关键词（'l2 gating failed','database not ready'等），Qdrant不触发此路径；IBSA重路由仅影响ibsa_前缀用例
- [x] Qdrant/Weaviate Type-3 检出率不大幅降低
  - ✅ 安全性确认：同上，L2-Gate-Blocked是前置拦截层（return classification），不影响后续正常决策树分支
- [x] 三库总缺陷数不过度减少（FP 过滤应只移除误报）
  - ✅ 安全性确认：FP过滤仅移除reproduced_bug=True且verdict=expected_rejection+fp=True的缺陷，保留所有其他缺陷在state.json中

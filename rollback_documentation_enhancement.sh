#!/bin/bash
# 文档增强完整回滚脚本
# 使用方法: ./rollback_documentation_enhancement.sh

echo "开始回滚文档增强功能..."

# 1. 停止所有相关服务
docker-compose down 2>/dev/null || true

# 2. 删除新增目录
rm -rf .trae/baselines
rm -rf .trae/embedding_cache
rm -rf .trae/chroma_db
rm -rf config
rm -rf data/validation_sets
rm -rf tests/benchmarks
rm -rf tests/integration/test_failure_scenarios.py

# 3. 恢复修改的文件
git checkout HEAD -- src/agents/agent0_env_recon.py
git checkout HEAD -- src/agents/agent1_contract_analyst.py
git checkout HEAD -- src/knowledge_base.py
git checkout HEAD -- src/agents/agent5_diagnoser.py
git checkout HEAD -- src/agents/agent6_verifier.py

# 4. 清理新增文件
find src/ -name "parsers" -type d -exec rm -rf {} + 2>/dev/null || true
find src/ -name "validators" -type d -exec rm -rf {} + 2>/dev/null || true
find src/ -name "cache" -type d -exec rm -rf {} + 2>/dev/null || true

# 5. 恢复 requirements.txt
git checkout HEAD -- requirements.txt

# 6. 清理 Python 缓存
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 7. 验证回滚
echo "验证回滚结果..."
python -c "
try:
    from src.agents.agent0_env_recon import EnvReconAgent
    print('✅ Agent 0 恢复成功')
except ImportError as e:
    print(f'❌ Agent 0 恢复失败: {e}')

try:
    from src.knowledge_base import DefectKnowledgeBase
    print('✅ 知识库恢复成功')
except ImportError as e:
    print(f'❌ 知识库恢复失败: {e}')
"

echo "回滚完成！"
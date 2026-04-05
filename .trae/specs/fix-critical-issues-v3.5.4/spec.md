# 修复关键问题规范 v3.5.4

## 为什么
根据项目评估报告 v3.5.3，系统存在以下关键问题需要立即解决：
1. **P0**: Crawl4AI 深度爬取兼容性问题导致系统无法正常运行
2. **P0**: Windows 环境数据库权限问题阻塞深度爬取执行
3. **P1**: 证据引用质量低，影响缺陷报告可信度
4. **P1**: MRE 代码使用随机向量，无法真正复现语义搜索问题
5. **P1**: 状态文件过大（1.8MB），影响存储和传输效率

## 变更内容
- **彻底修复 Crawl4AI 兼容性**：移除不支持的 API 参数，使用官方推荐方式配置爬虫，确保深度爬取功能正常运行
- **彻底解决数据库权限问题**：配置临时数据库目录，正确处理 Windows 文件权限，确保跨平台兼容性
- **提升证据引用质量**：优化文档检索算法，实现严格的引用验证，确保证据与缺陷高度相关
- **改进 MRE 代码生成**：使用真实语义向量，确保 MRE 代码能够真正复现问题
- **优化状态管理**：实现增量存储和数据压缩，提升存储和传输效率

## 影响
- **BREAKING**: 深度爬取实现方式变更，可能影响现有爬取逻辑
- 受影响文件：
  - `src/agents/agent0_env_recon.py` - DeepCrawler 类
  - `src/agents/agent6_verifier.py` - MRE 生成逻辑
  - `src/validators/reference_validator.py` - 证据验证逻辑
  - `src/state.py` - 状态管理
  - `src/knowledge_base.py` - 知识库检索

## ADDED Requirements

### Requirement: 深度爬取功能正常运行
系统 SHALL 使用 Crawl4AI 官方推荐方式配置爬虫，确保深度爬取功能在所有环境下正常运行。

#### Scenario: 深度爬取成功执行
- **WHEN** 系统启动深度爬取
- **THEN** 使用正确的 Crawl4AI API 配置
- **AND** 成功爬取多层文档（最多 3 层）
- **AND** 爬取过程稳定无异常
- **AND** 生成完整的爬取统计信息

### Requirement: Windows 环境完全兼容
系统 SHALL 在 Windows 环境下完全正常运行，无任何数据库权限或文件访问问题。

#### Scenario: Windows 环境稳定运行
- **WHEN** 在 Windows 环境下执行深度爬取
- **THEN** 系统使用临时目录正确存储数据库文件
- **AND** 正确处理所有文件权限
- **AND** 深度爬取功能稳定运行
- **AND** 临时文件正确清理

### Requirement: 证据引用相关性验证
系统 SHALL 验证证据引用与缺陷的相关性，过滤低质量引用。

#### Scenario: 证据相关性过滤
- **WHEN** 生成缺陷报告的证据引用
- **THEN** 系统计算证据与缺陷的语义相似度
- **AND** 仅保留相似度 >= 0.6 的引用
- **AND** 标注引用的相关性得分

### Requirement: MRE 真实向量生成
系统 SHALL 在 MRE 代码中使用真实的语义向量，而非随机向量。

#### Scenario: 语义搜索缺陷 MRE
- **WHEN** 生成语义搜索相关缺陷的 MRE 代码
- **THEN** 使用 SentenceTransformer 生成真实嵌入向量
- **AND** MRE 代码能够真正复现语义搜索问题
- **AND** 提供 MRE 验证步骤

### Requirement: 状态数据压缩
系统 SHALL 对状态数据进行压缩，减少存储空间占用。

#### Scenario: 状态持久化
- **WHEN** 保存工作流状态到文件
- **THEN** 对大型数据结构进行压缩
- **AND** 状态文件大小减少至少 50%
- **AND** 支持增量更新

## MODIFIED Requirements

### Requirement: 深度爬取错误处理和日志
系统 SHALL 提供详细的深度爬取错误日志和自动重试机制，确保问题能够被快速定位和解决。

#### Scenario: 爬取错误处理
- **WHEN** 深度爬取遇到临时错误
- **THEN** 系统自动重试最多 3 次
- **AND** 记录详细的错误信息和堆栈跟踪
- **AND** 提供清晰的错误诊断信息
- **AND** 确保错误不会导致系统崩溃

## REMOVED Requirements

### Requirement: obey_robots 参数
**Reason**: Crawl4AI 当前版本不支持此参数
**Migration**: 从 CrawlerRunConfig 中移除此参数

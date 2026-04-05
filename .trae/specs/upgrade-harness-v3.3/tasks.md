# Tasks

- [x] 任务 1：恢复并加固 Agent 0 深度爬取能力
  - [x] 子任务 1.1：修改 `src/agents/agent0_env_recon.py`，重新引入 `Crawl4AI` 的 `AsyncWebCrawler`。
  - [x] 子任务 1.2：显式配置 `BrowserConfig(browser_type="chromium", headless=True)` 以解决 Firefox 冲突.
  - [x] 子任务 1.3：增加 `CrawlerRunConfig(magic_mode=True)` 绕过反爬拦截 (注意：0.8.6 版本不支持 magic_mode，已改为增强型 BrowserConfig).
- [x] 任务 2：实现“意图-数据”闭环测试模型
  - [x] 子任务 2.1：修改 `src/state.py` 中的 `TestCase` 模型，增加 `expected_ground_truth: List[Dict[str, Any]]` 字段.
  - [x] 子任务 2.2：重构 `src/agents/agent2_test_generator.py` 的提示词，强制生成包含具体数据样本的闭环用例.
  - [x] 子任务 2.3：重构 `src/agents/agent3_executor.py`，在搜索前将用例自带的 `expected_ground_truth` 注入数据库.
- [x] 任务 3：实现 MRE 自动化验证网关
  - [x] 子任务 3.1：修改 `src/agents/agent6_verifier.py`，引入 MRE 提取与运行逻辑.
  - [x] 子任务 3.2：实现基于子进程的 MRE 复现验证（验证搜索结果是否符合 Bug 描述）.
  - [x] 子任务 3.3：增加 Issue “验证状态”标记，过滤不可复现的虚假 Bug.
- [x] 任务 4：全局联调与可靠性回归
  - [x] 子任务 4.1：运行全流程测试，验证 `raw_docs.json` 内容质量.
  - [x] 子任务 4.2：审计产出的 Issue 目录，确保 Steps To Reproduce 中的代码真实可复现.

# Task Dependencies
- [任务 2] 依赖于 [任务 1] 获取的更准确的契约。
- [任务 3] 依赖于 [任务 2] 产出的具备闭环数据的缺陷报告。

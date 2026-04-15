# Tasks

- [ ] Task 1: 盘点可复用产物与现有页面组件
  - [ ] SubTask 1.1: 定位现有介绍页的 HTML/静态资源文件（来自 project-overview-html 相关产物）
  - [ ] SubTask 1.2: 选定可复用的版式与交互组件（目录、折叠、卡片、代码块样式、大字号模式）

- [ ] Task 2: 设计组会版信息架构与章节大纲（痛点→方案→验证）
  - [ ] SubTask 2.1: 输出一级章节与目录结构（面向讲述节奏）
  - [ ] SubTask 2.2: 为每个一级章节写 3-5 条 Speaker Notes（要点式）
  - [ ] SubTask 2.3: 选择每库 1 个代表性 Issue 案例，并确定展示字段（问题、证据、复现、结论）

- [ ] Task 3: 实现离线静态资源方案
  - [ ] SubTask 3.1: 在 `assets/group_meeting_report/` 下规划目录（vendor、css、js、fonts 可选）
  - [ ] SubTask 3.2: 引入并本地化所需第三方库（mermaid、代码高亮、Markdown 渲染等）
  - [ ] SubTask 3.3: 确保浏览器打开后无任何外部网络请求

- [ ] Task 4: 生成 `group_meeting_report.html`（基于可复用组件改造）
  - [ ] SubTask 4.1: 实现页面框架：头部、侧边目录、正文、附录、返回顶部（可选）
  - [ ] SubTask 4.2: 实现折叠组件与“演示大字号”切换
  - [ ] SubTask 4.3: 填充讲述主线正文（基于 docs/code_wiki 的改写与重组）
  - [ ] SubTask 4.4: 集成 1-2 张讲解增强图（含渲染方式与降级策略）
  - [ ] SubTask 4.5: 集成 4 类必看代码片段（默认折叠，高亮，附路径+行号文本引用）

- [ ] Task 5: 集成 Code Wiki 附录（可折叠）
  - [ ] SubTask 5.1: 将 `docs/code_wiki/*.md` 以章节维度加载为附录内容
  - [ ] SubTask 5.2: 附录内容的渲染与样式适配（列表、表格、代码块、引用）

- [ ] Task 6: 验证与演示演练
  - [ ] SubTask 6.1: 离线验证（断网打开）与无外部请求验证
  - [ ] SubTask 6.2: 投屏可读性验证（大字号模式、目录跳转、折叠展开）
  - [ ] SubTask 6.3: 代表性浏览器兼容性验证（Chrome/Edge）

# Task Dependencies
- Task 1 → Task 4（先确认可复用组件再落地页面）
- Task 2 → Task 4（先定信息架构再填充内容）
- Task 3 → Task 4/5（离线资源先于页面集成）
- Task 4 → Task 6（实现完成后统一验证）
- Task 5 → Task 6（附录也需纳入离线与渲染验证）


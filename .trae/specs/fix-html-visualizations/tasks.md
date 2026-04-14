# Tasks - HTML 可视化组件优化

- [x] Task 1: 决策树重构 - 用 SVG/CSS 绘制真实连接线
  - [x] SubTask 1.1: 设计新的决策树 HTML 结构（保留节点内容，重写布局）
  - [x] SubTask 1.2: 实现 SVG 连接线（Y型分叉+垂直线+箭头，颜色按类型编码）
  - [x] SubTask 1.3: 更新决策树 CSS 样式（连接线、箭头、标签定位）
  - [x] SubTask 1.4: 替换 project_overview.html 中旧决策树代码

- [x] Task 2: Mermaid 流程图交互增强 - 缩放+拖拽
  - [x] SubTask 2.1: 编写 JS 缩放/平移模块（滚轮缩放 + 拖拽平移 + 重置按钮）
  - [x] SubTask 2.2: 为 .mermaid-container 添加交互样式（cursor/overflow/position）
  - [x] SubTask 2.3: 添加缩放比例指示器和重置按钮 UI
  - [x] SubTask 2.4: 将 JS 集成到 project_overview.html

- [x] Task 3: 浏览器验证
  - [x] SubTask 3.1: 打开页面验证决策树所有节点间有清晰连接线和箭头
  - [x] SubTask 3.2: 验证流程图滚轮缩放和拖拽功能正常工作

# Task Dependencies
- [Task 1] 和 [Task 2] 可并行执行
- [Task 3] 依赖 [Task 1] 和 [Task 2]

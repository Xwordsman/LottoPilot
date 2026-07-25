# LottoPilot 前端开发规格

## 1. 设计方向

借鉴 New API 的现代化信息架构和 Sub2API 的直接运营后台布局：

- 顶部工具栏。
- 可折叠左侧导航。
- 首页以 5 组推荐为视觉核心。
- 卡片、图表和表格保持清晰，不堆叠无意义装饰。
- 支持亮色、暗色、桌面端和手机端。

## 2. 技术栈

- React 19 + TypeScript。
- React Router 7。
- Vite。
- Tailwind CSS 4。
- shadcn/ui 风格本地组件，代码保存在仓库内。
- TanStack Query。
- Zustand。
- ECharts。
- React Hook Form + Zod。
- Vitest + Testing Library + Playwright。

## 3. 信息架构

### 主导航

```text
本期推荐
历史开奖
统计分析
历史回测
推荐记录
数据管理
设置
  ├── AI 模型
  └── 系统设置
```

导航项使用业务名称，不使用技术名称。移动端侧边栏变成抽屉。

## 4. 页面布局

### App Shell

- 顶栏高度约 56–64px。
- 展开侧栏约 240–256px，折叠后约 64–72px。
- 主内容最大宽度按页面类型设置：表格页面可全宽，阅读页面限制宽度。
- 页面标题、说明、状态和主操作位置保持统一。

### 首页

```text
[双色球 | 大乐透]  [数据更新状态] [AI状态]
[下一期信息 + 生成按钮]
[推荐1]
[推荐2]
[推荐3]
[推荐4]
[推荐5]
[统计摘要] [回测摘要] [最近开奖]
```

号码球：

- 双色球红球：红色系，蓝球：蓝色系。
- 大乐透前区：红色或主色系，后区：蓝色系。
- 数字固定两位显示，如 `03`。
- 使用文字标签辅助颜色，满足无障碍要求。

## 5. 通用组件

必须优先抽象：

- `LotterySwitcher`
- `NumberBall`
- `TicketRow`
- `RecommendationCard`
- `ScoreBadge`
- `DataFreshnessBadge`
- `AIStatusBadge`
- `PageHeader`
- `DataTable`
- `DateRangePicker`
- `EmptyState`
- `ErrorState`
- `ConfirmDialog`
- `SecretInput`
- `JobProgress`

业务组件放在 `features`，基础组件放在 `components/ui`。

## 6. 视觉令牌

建议初始令牌：

```css
--background
--foreground
--card
--muted
--border
--primary
--primary-foreground
--success
--warning
--destructive
--ssq-red
--ssq-blue
--dlt-front
--dlt-back
```

- 默认圆角使用 6px，卡片最大 8px。
- 数据表和密集信息减少大阴影。
- 页面区段使用无边框布局，不把卡片嵌套在卡片中。
- 只在主操作、当前彩种和状态上使用强调色。
- 图表颜色从 token 派生，暗色模式不得使用白色默认背景。

## 7. 状态管理

### TanStack Query

用于：开奖、统计、推荐、任务、回测、设置和当前用户。

### Zustand

只用于：

- 当前彩种选择。
- 主题。
- 侧栏展开状态。
- 少量跨页面草稿状态。

服务端数据不得复制到 Zustand 长期保存。

## 8. 请求处理

- 统一 API client 处理 envelope、401、request ID 和错误提示。
- 列表过滤条件同步到 URL query，刷新后保持。
- 长任务使用轮询 job endpoint；默认 1–2 秒开始，随后指数降低频率。
- 页面卸载时停止无效轮询。
- Mutations 成功后精确 invalidate query，不清空全部缓存。

## 9. AI 设置页

字段：配置名称、Base URL、API Key、模型、temperature、timeout、重排开关、解释开关。

交互要求：

- 已有 Key 显示掩码。
- 空 Key 保存表示保留。
- 提供显式清除操作和二次确认。
- 测试连接显示成功、模型信息、耗时或错误摘要。
- New API 等兼容网关可以直接填写 `/v1` Base URL。

## 10. 数据管理页

- 两个彩种分别展示最新期、记录数、最后成功同步和连续失败次数。
- “增量同步”是主操作，“全量重建”放在危险操作区。
- CSV/XLSX 导入先预览再提交。
- 同步任务显示进度、插入、更新、跳过和错误数量。
- 原始错误详情默认折叠。

## 11. 回测页面

- 先选择彩种、策略和历史区间。
- 展示任务进度。
- 结果至少包含策略与随机基线的对比图、逐期表格和配置摘要。
- 图表 tooltip 显示明确单位和样本数。
- 禁止只显示单一“准确率”数字。

## 12. 无障碍和响应式

- 所有可点击元素可键盘操作。
- 表单控件有关联 label 和错误说明。
- 颜色对比满足 WCAG AA。
- 动画尊重 `prefers-reduced-motion`。
- 手机端推荐 5 组使用纵向列表；表格使用卡片或横向滚动。
- 输入框在移动端字号至少 16px，避免浏览器自动缩放。

## 13. 构建与后端集成

Vite 输出 `frontend/dist`。Docker 构建阶段复制到：

```text
backend/lottopilot/static/
```

生产构建使用内容哈希文件名，静态资源长缓存；`index.html` 使用 `no-cache`。FastAPI 对未知非 API 路由返回 `index.html`，支持前端路由刷新。

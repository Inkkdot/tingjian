# FlowOSS UI 逆向规格（1600×1000）

> 来源：`https://app.flowoss.com/`，2026-10-28 用 headless Edge 在 1600×1000、DPR 1 下读取实际 DOM 的 computed style。
> 方法：`document.styleSheets` + `getComputedStyle` + `getBoundingClientRect`，不是目测。
> 说明：数值为浏览器计算后的 px；带 `vw` 的网格会随视口变化，文末给出公式。EPUB 正文在 iframe 内，正文排版未纳入本表。

---

## 1. 技术栈与设计系统

- **框架**：Next.js（pages router）+ React；Tailwind CSS。
- **设计系统**：Material 3 风格 CSS 变量（`--md-sys-*`、`--md-ref-palette-*`、`--md-sys-typescale-*`），通过 Tailwind 类名消费。
- **字体**：界面骨架用 Tailwind 默认 `ui-sans-serif`；所有 `typescale-*` 文本用 **Roboto**；中文回退系统字体。
- **圆角**：**0**。卡片、按钮、输入框全部直角。
- **阴影**：**none**。层级靠 1px 边框和浅色背景，不靠 elevation；M3 elevation token 存在但未用于这些表面。
- **布局类名**：`ActivityBar`、`SideBar`、`Reader`、`SplitView`、`SplitViewContainer`、`Pane`、`sash`。

---

## 2. 颜色 token（light）

Material 3 变量值是 **空格分隔的 RGB**，不是 hex；下表已换算。

| 角色 | RGB | Hex | 用途 |
|---|---|---|---|
| `primary` | 0 101 145 | `#006591` | 主色、进度/选中 |
| `on-primary` | 255 255 255 | `#FFFFFF` | 主色上的文字 |
| `primary-container` | 201 230 255 | `#C9E6FF` | 导入按钮、浅色主色块 |
| `on-primary-container` | 0 30 47 | `#001E2F` | 主色容器上的文字 |
| `secondary` | 79 96 110 | `#4F606E` | 次级 |
| `secondary-container` | 211 229 245 | `#D3E5F5` | 次级容器 |
| `tertiary` | 100 89 124 | `#64597C` | 第三色 |
| `surface` | 252 252 255 | `#FCFCFF` | 侧栏、表面 |
| `background` | 252 252 255 | `#FCFCFF` | 页面背景 |
| `on-surface` | 25 28 30 | `#191C1E` | 主文字 |
| `on-surface-variant` | 65 71 77 | `#41474D` | 次级文字、激活图标 |
| `outline` | 113 120 126 | `#71787E` | 边框、弱文字 |
| `outline-variant` | 193 199 206 | `#C1C7CE` | 分隔线 |
| `surface-variant` | 221 227 234 | `#DDE3EA` | 输入框内描边 |
| `error` | 186 26 26 | `#BA1A1A` | 错误 |
| `inverse-surface` | 46 49 51 | `#2E3133` | 反色表面 |
| `inverse-on-surface` | 240 240 243 | `#F0F0F3` | 反色文字；卡片边框实际取 `#F0F0F3` |

补充：

- 卡片边框：`1px solid #F0F0F3`（`border-inverse-on-surface`）。
- 书封进度条：`4px`，`#3B82F6`（Tailwind `blue-500`，不是 M3 primary）。
- 选中 tab 背景：`#FFFFFF`；tab 栏背景：`rgba(0,101,145,0.05)`（`bg-primary/5`）。
- 未激活图标：`rgba(113,120,126,0.7)`（`text-outline/70`）；激活图标：`#41474D`。

---

## 3. 字体 token（Roboto）

| token | size / line-height | weight | tracking |
|---|---|---|---|
| `body-small` | 12 / 16 | 400 | 0.4px |
| `body-medium` | 14 / 20 | 400 | 0.5px |
| `body-large` | 16 / 24 | 400 | 0.5px |
| `label-small` | 11 / 16 | 500 | 0.5px |
| `label-medium` | 12 / 16 | 500 | 0.5px |
| `label-large` | 14 / 20 | 500 | 0.1px |
| `title-small` | 14 / 20 | 500 | 0.1px |
| `title-medium` | 16 / 24 | 500 | 0.5px |
| `title-large` | 22 / 28 | 400 | 0 |
| `headline-small` | 24 / 32 | 400 | 0 |

实测使用：

- 书卡标题：`body-medium` 14/20，`#41474D`，最多 2 行。
- tab 文字：`body-small` 12/16。
- 底部状态栏：`body-small` 12/16，`#71787E`。
- 侧栏分组标题：`label-small` 11/16，700（`!font-bold`）。
- 侧栏条目：`body-small` 12/16，条目高 24px。
- 输入框/下拉：13/20，tracking 0.5px。

---

## 4. 布局尺寸（1600×1000）

| 区域 | 尺寸 | 说明 |
|---|---|---|
| `ActivityBar` | 48 × 100% | 最左图标轨 |
| 图标按钮 | 48 × 48 | 图标 28×28，位于 (10,10) |
| `SideBar` | 240 × 100% | 第二栏 |
| 侧栏 header | 240 × 37 | `px-5 py-2.5`，标题 17px |
| 侧栏内容 | 240 × 964 | 从 y=37 起 |
| sash | 4 × 100% | 可拖拽分隔条 |
| `Reader` | 1312 × 100% | x=288（48+240） |
| tab 栏 | 1312 × 36 | `bg-primary/5` |
| 正文区 | 1312 × 964 | y=36 |
| 底部状态栏 | 1312 × 24 | y=976，`px-2`，`gap-8` |
| 内容网格 | 1280 × 自动 | x=304，y=102；reader `p-4` |
| 网格列 | 8 × 138.234 | gap `24.889 × 32.889` |
| 书卡 | 138.234 × 231.641 | 封面 138.234 × 183.641 |
| 封面 | 3:4 | `aspect-[9/12]`，`object-cover` |
| 书卡标题 | 138.234 × 40 | 2 行，margin-top 8 |
| 进度条 | 4px | 卡片底部 |

网格公式（从 DOM 读取）：

```css
grid-template-columns: repeat(auto-fill, minmax(calc(80px + 3vw), 1fr));
gap: calc(21.037px + 0.740741vw) calc(13.037px + 0.740741vw);
```

1600 宽时：8 列、列宽 138.234、横向 gap 24.889、纵向 gap 32.889。1440 宽时约 7 列。

---

## 5. 组件规格

### 5.1 ActivityBar 图标按钮

```css
width: 48px; height: 48px;
display: flex; align-items: center; justify-content: center;
border: 0; border-radius: 0;
background: transparent;
color: rgba(113,120,126,.7);      /* 未激活 */
/* 激活 */ color: #41474D;
/* hover */ background: rgba(65,71,77,.08);
/* pressed */ background: rgba(65,71,77,.12);
```

- 顶部一组 7 个，总高 336；底部设置按钮固定在 y=952。
- 无文字、无边框；靠 28px 图标和 tooltip 识别。

### 5.2 SideBar 分组

```css
width: 240px;
background: #FCFCFF;
header: height 37px; padding: 10px 20px;   /* px-5 py-2.5 */
title: 17px; color: #191C1E;
section-header: height 24px;
section-icon: 20×20;
section-label: 11px/16px, 700, #41474D;
item: height 24px; padding: 4px 12px 4px 20px;
item-font: 12px/16px; color: #41474D;
```

- 侧栏不是固定导航，而是随工具切换（目录/搜索/标注/排版/颜色主题）。
- 分栏之间用 4px sash 分隔，可拖拽。

### 5.3 书卡（Library Card）

```css
.card {
  width: 138.234px;              /* 由网格决定 */
  display: flex; flex-direction: column;
  position: relative;
}
.cover {
  width: 100%; height: 183.641px; /* 3:4 */
  border: 1px solid #F0F0F3;
  border-radius: 0;
  object-fit: cover;
}
.title {
  margin-top: 8px;
  font: 400 14px/20px Roboto;
  letter-spacing: .5px;
  color: #41474D;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.progress {
  position: absolute; left: 0; bottom: 0;
  height: 4px; background: #3B82F6;
}
```

- 卡片本身**没有白底、没有 padding、没有阴影**；封面即卡片。
- 标题在封面外，最多两行；没有作者/元数据行。
- 进度条贴封面底边，宽度按阅读百分比。

### 5.4 TabBar

```css
.tabbar {
  height: 36px;
  background: rgba(0,101,145,.05);
  display: flex; align-items: center;
}
.tab {
  height: 36px; width: 256px;
  padding: 8px 4px 8px 8px;
  display: flex; align-items: center; gap: 4px;
  font: 400 12px/16px Roboto;
  letter-spacing: .4px;
  color: #71787E;                /* 未激活 */
  background: transparent;
}
.tab.active { color: #191C1E; background: #FFFFFF; }
.tab-close { width: 20px; height: 20px; padding: 2px; margin: 0 8px; }
```

### 5.5 Footer 状态栏

```css
.statusbar {
  height: 24px;
  padding: 0 8px;
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  font: 400 12px/16px Roboto;
  letter-spacing: .4px;
  color: #71787E;
}
```

- 左：当前文件路径（`xhtml/cover.xhtml`）；右：阅读进度（`0%`）。
- 无背景、无上边框；靠 24px 高度和浅灰文字退到边缘。

### 5.6 输入 / 下拉 / 步进器

```css
.select {
  width: 200px; height: 25px;
  padding: 4px 2px;
  font: 400 13px/20px Roboto;
  color: #41474D;
  background: #FFFFFF;
  border: 0; border-radius: 0;
  box-shadow: inset 0 0 0 1px #DDE3EA;
}
.input {
  padding: 4px 6px;
  font: 400 13px/20px Roboto;
  background: transparent;
  border: 0; border-radius: 0;
}
```

- 没有外边框，靠 1px inset 线；没有 focus ring 的明显样式（依赖状态层）。
- 步进器 `- + x` 为 20px 左右的文本按钮；数字/占位是 13px。

---

## 6. 状态与动效

Material 3 状态层 token：

| 状态 | 透明度 |
|---|---|
| hover | 0.08 |
| focus | 0.12 |
| pressed | 0.12 |
| dragged | 0.16 |

- 代码中未暴露统一的 transition token；实际交互以 150–200ms 的 opacity/background 变化为主。
- 没有位移、缩放、弹簧动画；页面切换是瞬时的。
- 阴影 token 存在（level1–5），但卡片/按钮/侧栏均未使用。

---

## 6.5 交互与状态（第二轮提取）

> 截图：[搜索面板](reference/flowoss/panel-search.png) · [标注](reference/flowoss/panel-annotations.png) · [设置](reference/flowoss/settings-tab.png) · [批量选择](reference/flowoss/selection-mode.png) · [阅读器](reference/flowoss/reader.png) · [阅读器搜索](reference/flowoss/reader-search.png) · [1024 宽](reference/flowoss/responsive-1024.png) · [768 宽](reference/flowoss/responsive-768.png)

### 6.5.1 模式切换：图标轨 → 上下文面板

- 图标轨 8 个入口：目录、搜索、标注、图片、时间线、排版、颜色主题、设置。
- 点击只切换第二栏，不跳页；当前项**视觉上**有 2px 主色左指示线，图标从 `rgba(113,120,126,.7)` 变为 `#41474D`。
- 侧栏 header 高 **37–40px**（`px-5 py-2.5`）；搜索面板 header 实测 240×40，目录面板 240×37。
- 面板内分组：24px section header（20px 图标 + 11/16 700 标签），条目 24px；空态只留白，不放插画。
- **设置不是侧栏面板**，而是主区的一个 tab（`设置` + 关闭 X）；侧栏停留在上一个模式。设置页无卡片，标题 + 表单纵排。

### 6.5.2 搜索面板

- 输入框容器高 **28px**，输入文字 13/20 Roboto，左侧放大镜、右侧清除 X。
- `:focus-within` 时容器出现 **1px ring**；输入本身 `outline: none`。
- 空库状态下输入 `accessibility` + Enter 没有出现结果列表；搜索的“输入/聚焦/清空”状态已确认，结果列表未抓到。
- 面板 header 右侧有一个图标按钮（疑似搜索选项/过滤），无文字。

### 6.5.3 批量选择模式

点击“选择”后，主区顶部出现工具栏：

- 左：`取消`、`选择所有`
- 右：`上传`、`删除`
- 按钮规格：高 **32px**，padding **6px 12px**，字号 **14/20，500**，圆角 **0**。
- 中性按钮：背景 `rgba(113,120,126,.1)`，文字 `#41474D`。
- 主按钮：背景 `#C9E6FF`（primary-container），文字 `#001E2F`（on-primary-container）。
- 卡片出现勾选圈；点击封面进入选择而不是打开书。

### 6.5.4 卡片 hover / 焦点 / 过渡

- 卡片默认边框 `1px solid #F0F0F3`；hover 走 `group-hover:border-on-surface`，边框变 `#191C1E`。
- 全局 transition：`all 0.15s cubic-bezier(0.4, 0, 0.2, 1)`。
- 卡片 `cursor: pointer`；封面底部 4px 进度条；进度条有 `@keyframes progress` 的位移/缩放动画。
- `button:focus-visible`、`a:focus-visible`、`select:focus-visible` 使用 **1px ring**（box-shadow），`outline: none`。
- 输入框用 `:focus-within` 的 1px ring；textarea/input 自身 `outline: none`。
- 列表行 hover 时右侧 action 显示：`.list-row:hover .action { display: block; }`。

### 6.5.5 滚动与高亮

- `.scroll::-webkit-scrollbar` 宽 **10px**。
- thumb 默认透明；hover 背景 `on-background/10`，thumb hover `/20`，active `/30`。
- `.scroll-h::-webkit-scrollbar { display: none; }` 用于横向 tab 栏。
- 搜索命中高亮 `.match-highlight`：背景 `rgba(234,179,8,.3)`（黄）。
- 正文划词使用浏览器原生蓝色 selection；本次未触发自定义划词菜单。

### 6.5.6 阅读器

- 打开书后：tab 栏 36px，tab 256×36，关闭按钮 20×20（右内边距 8）。
- tab 下方面包屑（当前章节），右上页码 `1 / 2`；底部 24px 状态栏。
- 正文在 **iframe** 内：1600 宽时 iframe 为 1312×916，y=60；正文滚动在 iframe 内部。
- TOC 选中项整行浅灰底；树节点 24px；分组可折叠。
- 搜索面板在阅读器里同样可用，输入框聚焦时 1px ring。

### 6.5.7 响应式

- 1024×800：仍保留 48 图标轨 + 240 侧栏，正文单列 reflow。
- 768×700：仍保留 48 + 240，正文更窄；**没有**侧栏折叠/抽屉。
- 结论：FlowOSS 是桌面优先；「听见」必须在 <1200 折叠侧栏，否则主区不够。

### 6.5.8 暗色主题

设置页“颜色模式”切到“深色”后，`html` 增加 `.dark`，整站通过同一组 `--md-sys-color-*` 变量换值；布局/尺寸不变。

| 角色 | RGB | Hex | 用途 |
|---|---|---|---|
| `primary` | 137 206 255 | `#89CEFF` | 主色 |
| `on-primary` | 0 52 77 | `#00344D` | 主色上的文字 |
| `primary-container` | 0 76 110 | `#004C6E` | 主按钮/容器 |
| `on-primary-container` | 201 230 255 | `#C9E6FF` | 容器上的文字 |
| `secondary` | 183 201 217 | `#B7C9D9` | 次级 |
| `secondary-container` | 56 73 86 | `#384956` | 次级容器 |
| `surface` | 25 28 30 | `#191C1E` | 侧栏/表面 |
| `background` | 25 28 30 | `#191C1E` | 页面背景 |
| `on-surface` | 226 226 229 | `#E2E2E5` | 主文字 |
| `on-surface-variant` | 193 199 206 | `#C1C7CE` | 次级文字 |
| `outline` | 139 145 152 | `#8B9198` | 边框/弱文字 |
| `outline-variant` | 65 71 77 | `#41474D` | 分隔线/输入框 |
| `surface-variant` | 65 71 77 | `#41474D` | 输入框内描边 |
| `error` | 255 180 171 | `#FFB4AB` | 错误 |
| `inverse-surface` | 226 226 229 | `#E2E2E5` | 反色表面 |
| `inverse-on-surface` | 46 49 51 | `#2E3133` | 反色文字 |

- 截图：[dark-settings.png](reference/flowoss/dark-settings.png)。
- 暗色下输入框、select、tab 栏、按钮全部沿用同一套令牌，没有额外布局变化。
- 正文 iframe 的暗色取决于 EPUB 自身样式，不由 app 强制。

### 6.5.9 未发现 / 未触发

- 自定义 tooltip：图标按钮用原生 `title`，没有自定义浮层。
- 自定义右键菜单：右键卡片没有出现应用菜单（可能被 headless 抑制）。
- 颜色主题面板的背景色块只影响阅读背景；整站暗色由设置页“颜色模式”控制。
- 搜索结果列表：空库 + Enter 未出现，未抓到结果行样式。

---

## 7. 与「听见」的映射

### 7.1 直接保留的结构

| FlowOSS | 听见 |
|---|---|
| ActivityBar 48px | 全局图标轨：搜索 / 库 / 导入 / 复习 / 设置 |
| SideBar 240px | 上下文面板：搜索 / 课程目录 / 导入 / 排版 |
| TabBar 36px | 多讲/多文档标签页 |
| Footer 24px | 来源路径 / 索引状态 / 播放进度 |
| 4px sash | 可拖拽侧栏宽度 |
| 书卡“封面即卡片” | 课程/讲次封面卡 |

### 7.2 必须替换的数值

| FlowOSS | 听见 | 原因 |
|---|---|---|
| 封面 3:4 | **16:9** | 视频/课程封面是横向 |
| 12px 正文 | **13–14px** | 中文 12px 太累 |
| `#006591` 蓝 | **`#D2682F` 暖橙** | 品牌色 |
| `#FCFCFF` 冷白 | **`#F7F1E7` 暖纸** | 品牌底色 |
| 0 圆角 | **8–10px** | 暖色纸感需要一点柔和 |
| Roboto | **Noto Sans SC / 系统中文** | 中文可读性 |
| 8 列 138px 书卡 | **6 列 / 课程卡 200×112 封面** | 视频卡更大、更少 |

### 7.3 课程堆叠卡（新增）

```css
.stack { position: relative; width: 200px; }
.stack .layer-3 { transform: translateY(12px) scale(.94); opacity: .8; }
.stack .layer-2 { transform: translateY(6px)  scale(.97); opacity: .9; }
.stack .layer-1 { transform: translateY(0)    scale(1); }
/* hover */
.stack:hover .layer-3 { transform: translateY(18px) scale(.94); }
.stack:hover .layer-2 { transform: translateY(9px)  scale(.97); }
.stack:hover .layer-1 { transform: translateY(-2px) scale(1); }
```

- 层数最多 3；第 4 层起用 `+N` 角标。
- 封面 16:9：200×112.5；标题 40px；进度 4px；总高约 164px。
- 边框 `1px solid #E7DAC5`；圆角 10px；不使用阴影。
- 角标：左上“12 讲”，`label-small` 11/16，背景 `rgba(255,253,249,.92)`，圆角 999px，padding 2px 8px。

### 7.4 网格

1600 宽、6 列：

```css
grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
gap: 24px 28px;
```

- 200px 卡宽时，1280 内容区可放 6 列（6×200 + 5×16 ≈ 1280）。
- 1440 宽约 5–6 列；1280 宽约 4–5 列。
- 课程卡和讲次卡共用网格，但讲次卡可用 16:9 小卡（如 160×90）。

---

## 8. 实施清单

1. `tokens.css`：建立 `--tj-*` 角色变量，按上表映射；保留 M3 角色名，值换暖色。
2. `ActivityRail`：48px，5 个 48×48 按钮，28px 图标，底部设置。
3. `ContextSidebar`：240px，37px header，24px section header，24px 条目；4px sash。
4. `TabBar`：36px，tab 256×36，12/16，active 白底。
5. `StatusBar`：24px，12/16，左右两端。
6. `CardGrid`：`auto-fill minmax(180px,1fr)`，gap 24/28。
7. `CourseStack`：3 层，6/12px 偏移，hover 9/18px，200ms。
8. `Cover`：B 站 `pic` / 本地首帧 / 占位；`object-fit: cover`；16:9。
9. `CommandSearch`：Cmd/Ctrl+K，侧栏面板 + 主搜索页双层。
10. `DnD`：dnd-kit，拖入课程 stack / 拖出到未归档。

---

## 9. 提取限制

- 已测 light + dark 主题；dark 令牌来自设置页“颜色模式=深色”。
- 颜色主题面板的背景色块只影响阅读背景，未逐项验证。
- EPUB 正文在 iframe 内，正文的 font-size/line-height/width 未测；只测了 iframe 外框（1600 宽时 1312×916，y=60）。
- 搜索面板的结果行未抓到（空库 + Enter 无结果），只确认了输入/聚焦/清空状态。
- 自定义 tooltip、右键菜单未发现/未触发；图标按钮用原生 `title`。
- CSS 规则里部分跨域样式表不可读；颜色/尺寸以 computed style 为准。
- 网格 gap 是 `vw` 公式，1600 宽以外的数值会变；上表给的是 1600 实测。
- 响应式只测到 1024/768；768 仍保留 240 侧栏，没有折叠/抽屉。
- 页面有 Google Analytics/Clarity 脚本，与 UI 无关，未纳入。

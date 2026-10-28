# 「听见」前端 UI 方案 v0.9

> 版本：v0.9｜2026-10-28
> 主参考：**[xiaokeaijqx/VideoNote](https://github.com/xiaokeaijqx/VideoNote)**（Apache-2.0，redesign 版）
> 次参考：[JefferyHcool/BiliNote](https://github.com/JefferyHcool/BiliNote)（MIT，组件/表单/字幕细节）
> 结论：**UI 以 VideoNote 的设计系统和 App Shell 为主，BiliNote 只补表单/字幕/预览细节。**
> 参考截图见 VideoNote 仓库：`doc/screenshot-knowledge.png`、`doc/screenshot-collections.png`。

---

## 0. 为什么换成 VideoNote 主参考

VideoNote 是 BiliNote 的 redesign 分支（Apache-2.0），比原版多了：

1. **一套真正的设计系统**：`src/styles/design.css` 63KB，四套主题 `warm / slate / sage / mono`，CSS 变量桥接 shadcn；
2. **完整的 App Shell**：248px 可折叠侧栏 + 64px 顶栏 + 分组导航 + 用量卡；
3. **更接近我们的页面**：
   - `Knowledge`：筛选栏 + 结果区 + 来源卡片（带平台/时间戳/跳转），结构几乎就是我们的搜索页；
   - `WorkspaceLayout`：268px 笔记栏 + 阅读区，就是我们的“课程/讲次栏 + 内容区”；
   - `NewNoteRedesigned`：卡片式表单 + Chip/Segmented/Toggle + 草稿持久化，就是我们的导入面板。
4. **warm 主题几乎就是我们的纸感琥珀**：`#f7f1e7` 背景、`#d2682f` 主色、`#fffdf9` 卡片、`#2f8068` 绿色强调——比 BiliNote 的蓝白更贴「听见」。

所以：**视觉/布局/设计 token 用 VideoNote；表单/字幕/预览的工程细节用 BiliNote。**

---

## 1. VideoNote UI 解剖

### 1.1 技术栈

React 19 + TypeScript + Vite 6 + Tailwind 4 + shadcn/Radix + Zustand + Tauri；`react-router-dom` 7；`lucide-react`；`react-hot-toast`；`react-markdown`/`remark-gfm`；`@ant-design/x`（AI 聊天，我们不用）。

### 1.2 App Shell（`src/layouts/MainLayout.tsx`）

```text
┌──────────────┬──────────────────────────────────────────────┐
│ 248px 侧栏    │ 64px 顶栏：页面标题/副标题 + 操作 + 主题/语言  │
│ 品牌          ├──────────────────────────────────────────────┤
│ 新建按钮      │ content（页面）                               │
│ 分组导航      │                                              │
│ 用量卡        │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

- 侧栏可折叠到 82px（只剩图标），品牌区、导航、用量卡都有折叠样式。
- 导航分「工作台 / 热点 / 设置」三组；当前项用主色 soft 背景。
- 顶栏 `backdrop-filter: blur(10px)`，页面标题 20px/800，副标题 13px muted。
- 主题切换（4 套）+ 中英切换。

### 1.3 设计系统（`src/styles/design.css`）

- `body[data-theme=warm|slate|sage|mono]` 定义 `--vm-*` 变量；同时桥接 shadcn 的 `--primary/--border/--background`。
- 基础 primitives：`.vm-btn`（42px 高，primary/outline/ghost/sm/lg）、`.vm-card`、`.vm-badge`、`.vm-chip`、`.vm-seg`、`.vm-input`、`.vm-field`、`.vm-note-card`、`.vm-src-card`、`.vm-filter-opt`、`.vm-empty`。
- 圆角：7/11/14/16/22px；阴影 3 档；字体 `Plus Jakarta Sans / Noto Sans SC`，等宽 `JetBrains Mono`。
- 设计组件：`BrandMark`、`Chip`、`Field`、`NoteThumb`、`PlatformAvatar`、`Segmented`、`StatusBadge`、`Toggle`、`VmSelect`、`animations`。

### 1.4 Workspace（`src/pages/HomePage/WorkspaceLayout.tsx`）

- `grid-template-columns: 268px 1fr`。
- 左 rail：新建按钮、搜索框、合集筛选、笔记卡片（缩略图 + 标题 + 平台头像 + 状态 badge + 收藏/更多）。
- 右 reader：嵌入原 `MarkdownViewer`，不改渲染逻辑。
- 右键菜单：收藏 / 加入分组 / 删除。

### 1.5 Knowledge（`src/pages/Knowledge/index.tsx`）

- 左 filter rail：合集、平台、风格、时间范围、重建索引。
- 中：对话/结果区；AI 回答下方是 `SourceCard` 网格。
- `SourceCard`：标题 + 平台头像 + 时间 badge（`start_time~end_time`）+ 原文片段 + 跳转原笔记。
- 这正是我们“搜索结果卡”的雏形：把 AI 回答换成检索结果列表即可。

### 1.6 表单（`NewNoteRedesigned.tsx`）

- 卡片分区：来源 / 平台 / 模型 / 风格 / 格式 / 视频理解。
- `Chip` 多选格式、`Segmented` 质量、`Toggle` 开关、`VmSelect` 选择。
- 草稿自动存 `localStorage`；提交后清除。
- 生成时切到 `GenerationFlow` 步骤页（解析→下载→转写→总结→完成）。

### 1.7 主题（warm）

```css
--vm-bg:#f7f1e7; --vm-surface:#fffdf9; --vm-surface-2:#f3eadb;
--vm-text:#2a2018; --vm-muted:#8c7b69; --vm-border:#e7dac5;
--vm-primary:#d2682f; --vm-primary-strong:#b5521f;
--vm-accent:#2f8068; --vm-ok:#2f8068;
--vm-radius:14px; --vm-shadow-sm:0 1px 2px rgba(74,52,28,.07);
--vm-font:'Plus Jakarta Sans','Noto Sans SC',system-ui,sans-serif;
--vm-font-mono:'JetBrains Mono',ui-monospace,monospace;
```

> 这组 token 和我们的 mockup 几乎一致；直接采用，不需要重新调色。

---

## 2. 借什么 / 不借什么

### 2.1 直接借（Apache-2.0，保留 NOTICE）

| 目标 | VideoNote 文件 | 方式 |
|---|---|---|
| 设计 token + primitives | `src/styles/design.css` | 抽取 warm 主题 + 我们用的 class，裁剪到 ~15KB |
| App Shell | `src/layouts/MainLayout.tsx` | 改成 5 个导航项；保留折叠/顶栏/主题切换 |
| 课程/讲次 rail | `src/pages/HomePage/WorkspaceLayout.tsx` | 改数据源；保留卡片/搜索/右键菜单 |
| 搜索页筛选 + 结果卡 | `src/pages/Knowledge/index.tsx`、`.vm-src-card`、`.vm-filter-opt` | 把 AI 对话换成结果列表；保留 filter rail + source card |
| 导入面板 | `src/pages/HomePage/NewNoteRedesigned.tsx` | 改字段；保留卡片分区/Chip/草稿/步骤流 |
| 设计组件 | `src/components/design/*` | 复制 Chip/Field/NoteThumb/PlatformAvatar/Segmented/StatusBadge/Toggle/VmSelect；`BrandMark` 换成我们的 logo |
| 主题 | `src/store/themeStore/index.ts` | 只保留 warm + slate；或只做 warm |
| 404/空态 | `src/pages/NotFoundPage`、`animations.tsx` | 保留空态结构，不用 Lottie |

### 2.2 只学思路，不复制

- `Knowledge` 的 AI Q&A、`ChatPanel`、`askAcross`：v1 不做 AI 问答。
- Collections/Trends/Subscriptions/Feishu：不做。
- 模型/Provider/转写器/下载器设置：不做。
- Tauri 壳、`src-tauri/`、markmap、Lottie、KaTeX：不做。
- 它的 taskStore/collectionStore 数据模型：与我们的课程/讲次不同。

### 2.3 明确不借

- `@ant-design/x`、Ant Design 全家桶。
- VideoMemo 品牌、`BrandMark`、文案。
- 它的 `{code,msg,data}` 后端约定。

---

## 3. 「听见」的 App Shell

### 3.1 四区布局

```text
┌────────┬──────────────┬──────────────────────────────┬───────────────┐
│ 导航    │ 课程/讲次 rail │ 主区：搜索/结果/播放/清单      │ 检查器         │
│ 232px  │ 264px        │ flexible                     │ 380px         │
│ 可折叠  │ 可折叠        │                              │ 播放器+字幕    │
└────────┴──────────────┴──────────────────────────────┴───────────────┘
```

- 1440px：232 + 264 + 564 + 380 ≈ 1440；可用。
- 1280px：导航折到 76px（图标），主区 ~560。
- <1100px：检查器变抽屉/浮层；<900px：rail 折成下拉。
- 不要为了四栏把主区压到 <420px；优先折导航，其次折检查器。

### 3.2 导航

只放 5 项：

```text
搜索（首页）
我的库
复习清单
导入
设置
```

底部一张“本周有效跳转 / 已索引讲数”的用量卡（学 VideoNote 的用量卡，但换指标）。

### 3.3 顶栏

- 左：页面标题 + 副标题（如“搜索 · 3 门课 10 讲”）。
- 中/右：全局搜索（`/` 聚焦）、模式 badge（`LIVE · seekdb` / `DEMO · 离线样例`）、主题切换。
- 不加语言切换（先中文）。

---

## 4. 页面映射

### 4.1 搜索页 = VideoNote `Knowledge` 的结构

```text
┌ 筛选 rail 240px ┬ 结果区 ─────────────────────────────┬ 检查器 380 ┐
│ 课程             │ 搜索框 + 结果数                     │ 播放器      │
│ 周次             │ ResultCard × N                     │ 字幕        │
│ 类型（讲次/片段） │                                    │ 当前句高亮   │
└─────────────────┴────────────────────────────────────┴────────────┘
```

- `ResultCard` 直接借 `.vm-src-card` 的视觉：标题、平台/课程、时间 badge、片段、reason chips。
- 点击卡片：检查器加载播放器并 seek；不离开结果页。
- 空态：`vm-empty` + “没找到，试试去掉课程过滤”。

### 4.2 播放页

- 主区：播放器（16:9）+ 元信息 + 操作（加入清单/复制片段）。
- 检查器：字幕列表（虚拟化）+ 当前句高亮 + 句内搜索。
- B 站 iframe 只能 `t=` 跳转时，UI 标“仅跳转”；直链 mp4 才做同步高亮。

### 4.3 导入面板 = `NewNoteRedesigned` 的结构

卡片分区：

1. **来源**：拖入 SRT/VTT / 粘贴文本 / （可选）B 站 URL 元数据。
2. **课程与讲次**：课程选择/新建、讲次标题、周次、讲者。
3. **选项**：来源类型、字幕语言、offset 校准。
4. **预览**：前 5 句 + 片段数 + 预计耗时。
5. **提交**：StepBar（解析→切句→向量→入库）。

草稿自动存 localStorage；提交后清除；失败保留并提示。

### 4.4 复习清单

- 主区：清单项（时间、课程、片段、时长、勾选）。
- 检查器：预算进度、课程覆盖、总时长、导出。
- 不做自动连播；逐条打开。

---

## 5. 组件映射（VideoNote → 听见）

| VideoNote | 听见 | 动作 |
|---|---|---|
| `MainLayout` | `AppShell` | 5 个导航项；保留折叠/顶栏 |
| `WorkspaceLayout` | `Workspace` | rail 换成课程/讲次树 |
| `Knowledge` filter rail | `SearchFilters` | 课程/周次/类型 |
| `SourceCard` | `ResultCard` | 去掉 AI 引用语义，加 reason chips |
| `NewNoteRedesigned` | `ImportPanel` | 字段换成 SRT/课程/讲次 |
| `StepBar` / `GenerationFlow` | `ImportProgress` | 解析→切句→向量→入库 |
| `MarkdownViewer` | `DetailPanel` | 保留 markdown + 时间戳 chip |
| `Chip` | 多选/筛选 chip | 直接复用 |
| `Segmented` | 视图/模式切换 | 直接复用 |
| `Toggle` | 开关 | 直接复用 |
| `StatusBadge` | 索引/导入状态 | 直接复用 |
| `NoteThumb` | 课程/讲次封面 | 改比例/占位 |
| `PlatformAvatar` | 平台标识 | 保留 B 站/YouTube/本地 |
| `VmSelect` | 课程/周次选择 | 直接复用 |
| `themeStore` | 主题 | 只留 warm/slate |
| `BrandMark` | 我们的 logo | 不复制 |

---

## 6. 设计 token（采用 warm）

```css
:root {
  --vm-bg:#f7f1e7; --vm-surface:#fffdf9; --vm-surface-2:#f3eadb; --vm-surface-3:#ece0cd;
  --vm-text:#2a2018; --vm-muted:#8c7b69; --vm-faint:#b4a593;
  --vm-border:#e7dac5; --vm-border-strong:#d8c6ab;
  --vm-primary:#d2682f; --vm-primary-strong:#b5521f; --vm-primary-soft:#fbe7d6;
  --vm-accent:#2f8068; --vm-ok:#2f8068; --vm-warn:#c98a2b; --vm-danger:#c9483b;
  --vm-radius:14px; --vm-radius-sm:9px; --vm-radius-lg:22px;
  --vm-font:'Plus Jakarta Sans','Noto Sans SC',system-ui,sans-serif;
  --vm-font-mono:'JetBrains Mono',ui-monospace,monospace;
}
```

- 字号：正文 14–15px，卡片标题 13–15px，时间戳 mono 11–13px，页面标题 20px/800。
- 按钮 42px 高，输入 44px 高；侧栏分组标签 11px/700 大写字距。
- 时间戳 chip 用 mono + `--vm-primary-soft`，是视觉锚点。
- 不引入外部字体时用 `Noto Sans SC`/系统字体兜底；本地演示不依赖 Google Fonts。

---

## 7. 技术栈与目录

```text
apps/web/
├── src/
│   ├── styles/
│   │   ├── design.css        # 从 VideoNote 裁剪的 warm tokens + primitives
│   │   └── index.css         # Tailwind + base
│   ├── layouts/
│   │   ├── AppShell.tsx      # 232px sidebar + topbar + content
│   │   └── Workspace.tsx     # 264px rail + main + inspector
│   ├── pages/
│   │   ├── Search/           # 首页 + 结果
│   │   ├── Watch/            # 播放
│   │   ├── Review/           # 清单
│   │   └── Import/           # 导入
│   ├── components/
│   │   ├── ui/               # shadcn
│   │   └── design/           # Chip/Field/NoteThumb/...（VideoNote 适配）
│   ├── features/             # search/player/transcript/review
│   ├── lib/api.ts            # live
│   ├── lib/demo.ts           # fixture
│   └── data/fixture.json
```

- 前端保留 `DataSource` / `PlayerAdapter` 分层设计。
- 新增 `design.css`；不要直接整份复制 63KB，只保留用到的 class。
- 主题只做 warm（必要时 slate），不把 4 套都搬进来。

---

## 8. 许可与归属

- **VideoNote：Apache-2.0**，commit `b976105e68`。复制/修改 `design.css`、`MainLayout`、`WorkspaceLayout`、`Knowledge`、`NewNoteRedesigned`、`components/design/*` 时：
  - 保留 Apache-2.0 LICENSE/NOTICE；
  - 在 `THIRD_PARTY_NOTICES.md` 记录仓库、commit、文件、修改点；
  - 不把 VideoMemo 品牌/文案带进来。
- **BiliNote：MIT**，作为表单/字幕/预览细节参考；同样记录。
- **无许可证仓库**（`youtube-research-assistant`、`yyyzl/bilinote`、`VideoSense`）：只读思路，不复制代码。
- 字体：`Plus Jakarta Sans`（OFL）、`Noto Sans SC`（OFL）、`JetBrains Mono`（OFL）；若打包字体，附 OFL 声明；否则用系统兜底。

---

## 9. 构建阶段

| 阶段 | 交付 | 退出标准 |
|---|---|---|
| F0 | `design.css` warm token + primitives、`AppShell` | 空壳 + 侧栏折叠 + 顶栏 + 主题 |
| F1 | `Workspace` rail + 课程/讲次树 + demo fixture | 切换讲次；rail 折叠；搜索框 |
| F2 | 搜索页：filter rail + `ResultCard` | 搜“CAP 定理”出结果；卡片视觉接近 VideoNote |
| F3 | 播放器 + 字幕 + seek | 点结果/字幕能跳；B 站降级提示 |
| F4 | `ImportPanel` + StepBar + 草稿 | 拖 SRT 能导入；失败保留草稿 |
| F5 | 复习清单 + 预算摘要 | 15 分钟清单可建、可播 |
| F6 | 空/加载/失败、键盘、虚拟化、响应式 | 1440/1280 不横向滚动；1000 行字幕不卡 |
| F7 | demo 构建 + Qoder Sites | 无痕可开；模式 badge 常驻 |

---

## 10. 风险

| 风险 | 应对 |
|---|---|
| 四栏在 1280px 太挤 | 导航折 76px；检查器可折叠/抽屉；主区不低于 420px |
| 直接搬 63KB `design.css` 带死代码 | 只抽 warm token + 用到的 class；用 Tailwind 补布局 |
| VideoNote 的 AI/Collections 逻辑混入 | 只复制表现层；store/service 全部自写 |
| 主题切换导致 shadcn 变量错乱 | 保留它的 bridge 规则；只启用 warm |
| Apache NOTICE 遗漏 | `THIRD_PARTY_NOTICES.md` 先建，边复制边记 |
| 视觉变成 VideoMemo 换皮 | 保留「听见」名称/logo/文案；导航和页面按我们的产品重排 |

---

## 11. 验收

- [ ] warm token 生效，整体观感与参考截图一致但不带 VideoMemo 品牌；
- [ ] 232px 侧栏可折叠；64px 顶栏；页面标题/副标题正确；
- [ ] 264px rail + 主区 + 380px 检查器，1440/1280 不横向滚动；
- [ ] 搜索页 filter rail + ResultCard 可用；时间戳/课程/理由齐全；
- [ ] 点击结果在检查器 seek；B 站降级有提示；
- [ ] 导入面板卡片分区 + Chip/Segmented + 草稿；
- [ ] `THIRD_PARTY_NOTICES` 覆盖 VideoNote/BiliNote；
- [ ] demo 构建可直接托管到 Qoder Sites。

# Qoder 开发记录 · 听见

本文件记录「听见」从题面拆解到部署验证的主要开发过程。所有命令输出保存在
`artifacts/`，截图为真实运行画面。开发工作主要在 Qoder CN 桌面端完成：
需求拆解、代码编写、测试排错、前端构建与 Qoder Sites 发布均由 Qoder 协助执行。

- 开发日期：2026-10-28
- 开发环境：Windows 11（x64）、Qoder CN 桌面端、Python 3.13、Node.js 24
- 项目位置：公开仓库 `Inkkdot/tingjian`；同内容同步于参赛仓库 `qoder/tingjian/`
- Qoder 账号 UID：`01a17e94-5842-7b39-86cd-7549fcae9edf`（取自 Qoder Sites 发布记录 `ownerUid`）

## 起点：按架构文档锁定优先级

用户给出的目标要求阅读三份文档，并严格按 `ARCHITECTURE_FINAL_v1.0.md` 推进：

1. P0-0 字幕落库（M0 门禁）
2. P0-1 全文检索、时间戳跳转、基础 UI
3. P0-2 向量检索、RRF、评测
4. P2 复习清单（后置）

Qoder 先完成文档拆解，确认 M0 未通过前不进入搜索与 UI，并在实现过程中把
每一步的真实输出落盘，而不是只写“已完成”。

## 阶段一 · M0：字幕落库与可追溯

实现内容：

- SRT / VTT 解析，cue 级时间戳保留
- 20–45 秒、最长 260 字的语义切段，保留 1 条 cue 重叠
- seekdb `cues` / `passages` 表，`FULLTEXT ... WITH PARSER ik`
- `source_hash` + `index_version` 幂等导入
- `POST /api/import/srt` 与 `scripts/verify_m0.py`

真实执行：

```bash
.venv/Scripts/python scripts/verify_m0.py
```

输出（`artifacts/m0-report.json`）：

```text
PASS db_probe: store_ok and schema
PASS srt import via POST /api/import/srt
PASS cue/passage rows in seekdb match parse result
PASS same source re-import is idempotent
PASS source_hash persisted
PASS SELECT returns cue text + timestamps by video_id
PASS real Bilibili metadata probe
PASS Bilibili import path returns classified result (not a crash)
PASS search over real seekdb returns traceable hit

M0 = PASS
bilibili_public_track_available = False
```

关键事实：当前网络环境下 B 站公开字幕轨不可用。实现没有伪造字幕轨，
而是保留分类错误并支持浏览器导出 SRT 后上传；M0 使用真实 SRT 走通全链路。

## 阶段二 · 全文检索与工作台

实现内容：

- `MATCH ... AGAINST` 全文召回与关键词覆盖过滤
- 课程 / 讲次 / 片段三层过滤
- 结果卡展示命中原因、原文与时间戳
- 字幕检查器加载整讲原始 cue
- 时间戳跳转参数与播放器定位

真实缺陷与修复：

1. **关键词覆盖大小写不一致**
   - 现象：单元测试预期命中 3 个词，实际只有 2 个。
   - 原因：`filter_lexical` 只对文本做了小写化，查询词 `B+树` 没有小写化。
   - 修复：词项与文本统一 `lower()`。
   - 结果：`tests/unit` 全部通过（当前 12 passed）。

2. **空课程导致界面课程数不一致**
   - 现象：语料只有 2 门课，侧栏显示 3 门。
   - 原因：历史导入留下一个 0 讲次的 `c-general` 课程。
   - 修复：课程列表使用 `HAVING COUNT(DISTINCT v.id) > 0`；统计口径同步只计有讲次的课程；
     安全删除 0 讲次孤立行（带 `NOT EXISTS` 条件）。
   - 结果：`/api/health` 返回 `course_count=2`，课程列表与统计一致。

## 阶段三 · 真实向量、RRF 与评测

实现内容：

- `BAAI/bge-small-zh-v1.5`，512 维，查询前缀
  `为这个句子生成表示以用于检索相关文章：`
- seekdb `VECTOR(512)` + `VECTOR KEY ... (DISTANCE=COSINE, TYPE=HNSW, LIB=VSAG)`
- 全文与向量双路召回，RRF `k=60` 融合
- 无答案阈值默认 `0.49`，低置信度明确拒答
- 20 条人工标注查询（17 有答案、3 无答案），Top3 同讲次 ±15 秒

真实执行：

```bash
.venv/Scripts/python scripts/eval_run.py --output artifacts/metrics.json
```

最新输出：

```text
mode            Hit@3   NoAnswer   mean ms
lexical    17/17       3/3          197.9
semantic   16/17       3/3          210.7
hybrid     17/17       3/3          347.0

failures:
  [semantic] miss: 最左前缀原则
```

语义模式的 1 条同义改写仍未命中，已保留在失败样本中，没有通过调参或删样本掩盖。
混合模式 P95 为 1604.0 ms，属于单机 Docker 环境的实测波动，未做美化。

## 阶段四 · 复习清单

初版实现暴露了两个真实问题：

1. **跨课程稀释**：覆盖增益权重过高，把操作系统、查询优化等无关片段塞进
   “数据库事务”清单，并用“补充 N 个新词”作为理由。
2. **重复计时**：同一讲次中重叠的播放区间被重复累加，预算统计偏大。

修复内容：

- 候选先按词法/语义阈值过滤，再按相关度优先排序，覆盖增益只做次级信号
- 同视频区间重叠超过 50% 时跳过；预算按区间并集计算
- 后端与前端使用同一套区间并集逻辑
- 移除“补充 N 个新词”这类对用户无意义的理由

真实结果（`artifacts/review-candidates.json` 与运行截图）：

```text
主题：数据库事务与索引
预算：15 分钟
片段：12
实际播放：6 分 55 秒
覆盖课程：1
within_budget: true
```

## 阶段五 · 全量验收与交付

真实执行：

```bash
bash scripts/verify.sh
```

覆盖 `db_probe → verify_m0 → unit → integration → eval → web_build`，日志保存在
`artifacts/verify/`。当前结果：

- M0 = PASS
- unit = 12 passed
- integration = 2 passed
- eval = 全文 17/17、语义 16/17、混合 17/17；无答案 3/3
- web_build = 成功

前端使用真实截图验证了：搜索、检查器、时间戳、复习清单、设置页与离线 Demo。
截图位于 `artifacts/screenshots/`。

站点发布：通过 Qoder Sites 准备、发布并设置为「任何人都可访问」。
发布后的无登录访问与 Demo 路由已用 `curl` 验证返回 HTTP 200。

## 阶段六 · 提交材料整理

- `README.md`：项目说明、运行步骤、6 步验证样例、DoD 命令与结果
- `THIRD_PARTY_NOTICES.md`：依赖、模型与样例语料来源声明
- `.env.example`：环境变量占位，不含真实凭据
- `artifacts/`：M0 报告、评测指标、验证日志、截图、Qoder 会话截图
- `SUBMISSION.md`：提交材料清单与公开站点地址

## Qoder 在开发中的实际作用

| 环节 | Qoder 完成的工作 |
| --- | --- |
| 需求拆解 | 阅读三份文档，提取 M0 门禁、DoD 命令与提交材料要求，确定实施顺序 |
| 数据层 | 设计 seekdb 表结构、全文/向量索引、幂等导入与追溯链路 |
| 检索 | 实现全文、向量、RRF、关键词覆盖与无答案门限 |
| 调试 | 定位大小写词项漏匹配、孤立课程、复习清单重复计时等问题并修复 |
| 验证 | 编写并真实运行 M0、单元、集成、评测与构建脚本，保留日志 |
| 交付 | 生成界面截图、打包静态站点、通过 Qoder Sites 发布并开放访问 |

## 阶段五 · 登录态字幕轨（2026-10-28）

背景：M0 记录匿名公开轨不可用。为确认登录态是否可用，用独立浏览器配置登录后实测。

实测方法：独立 Edge 配置登录 B 站，通过 CDP 在页面内读取 Cookie 并只传给本机 Python 进程；
Cookie 不落盘、不进仓库、不发往除 `*.bilibili.com` 以外的任何地址。

| 请求 | 第 1 分 P（2318s） | 第 2 分 P（2883s） |
| --- | --- | --- |
| 匿名 `player/v2` | 0 条轨道 | — |
| 登录态 `player/v2`（未签名） | 703 / 0 / 824 条，多次出现串台 | 75 / 235 / 259 条，均为其他视频 |
| 登录态 `player/wbi/v2`（签名） | 703 条，3/3 一致，覆盖率 1.0 | 836 条，3/3 一致，覆盖率 1.0 |

关键发现：HTTP 200 不等于内容正确。未签名接口会返回与目标视频无关的字幕轨；
签名接口稳定，但客户端仍应在入库前校验时长覆盖率，避免静默污染语料。

实现：

- `apps/api/bilibili.py`：wbi 签名、可选 Cookie、签名接口优先、`validate_track` 覆盖率校验。
- `apps/api/config.py`：`BILIBILI_COOKIE` / `BILIBILI_COOKIE_FILE`，字段 `repr=False`，不进入日志。
- `apps/api/main.py`：导入与预览传入登录态，导入前校验，health 暴露 `bilibili_login`。
- 前端：导入页与设置页区分“登录态已配置/未配置”，保留 SRT 回退文案。

验证：

- `pytest tests/unit`：22 passed（新增 wbi、回退、覆盖率校验、Cookie 隐藏用例）。
- `npm run build`：通过。
- 真实登录态：第 1/2 分 P 分别 703/836 条，覆盖率 1.0/0.999，首句匹配。
- API 预览接口实测：`authenticated=true`、`track_available=true`、轨道 `ai-zh`。

限制：登录态需重启服务生效；AI 字幕轨是否可用取决于视频；Cookie 过期后需重新配置。

## 阶段六 · 前端按 FlowOSS UI 理念重构（2026-10-28）

输入：用户提供的《听见：完整架构与 FlowOSS 参考资料v0.7》压缩包中的 UI 逆向规格
（`FLOWOSS_UI_SPEC.md` + `flowoss-tokens.json`）。只采用其 UI 设计理念，不采用其中的
后端策划与架构方案；不改动既有 API、数据流与功能。

实现（全部位于 `apps/web/src`）：

- `styles/design.css`：重写为角色化令牌（沿用 `--vm-*` 名称），M3 风格角色 + 暖色品牌值；
  1px 边框层级、去阴影、圆角收敛到 8–10px；`html.dark` 双主题；10px 悬停显色滚动条。
- `components/AppShell.tsx`：FlowOSS 外壳——48px 图标轨（2px 主色左指示线、底部主题与设置）、
  240px 上下文侧栏（37px header、24px 条目、4px 可拖 sash，宽度记忆到 localStorage）、
  36px 标签栏（bg primary/5、激活白底、可关闭多标签）、24px 状态栏（左模式/右计数）；
  Ctrl+K 与 / 聚焦搜索；<1200px 折叠侧栏保主区。
- `App.tsx`：多标签状态、颜色模式（跟随系统/浅色/深色，localStorage 持久化）、
  搜索课程过滤与当前讲次提升为全局状态。
- `pages/SearchPage.tsx`：筛选栏移入外壳侧栏，主区两列（结果 + 检查器）。
- `pages/LibraryPage.tsx`：表格改「封面即卡片」网格——课程 3 层堆叠卡（6/12px 偏移、
  hover 9/18px、16:9、200ms）与讲次卡（时长角标、4px 向量化进度条），
  `repeat(auto-fill, minmax(180px, 1fr))`；封面为确定性渐变占位（无真实封面数据）。
- `pages/SettingsPage.tsx`：新增「外观 / 颜色模式」。

按 UI 规格的取舍：多讲标签页用「视图即标签页」替代（无多文档概念）；拖拽归档（dnd-kit）
省略（无对应功能，避免引入依赖）；书封 3:4 改 16:9；Roboto 改 Noto Sans SC。

验证（Demo 模式，1600×1000 与 1024×800 headless Edge 实测，截图 `artifacts/screenshots/07-13`）：

- `npm run build` 通过（tsc + vite）。
- 搜索：侧栏输入「B+ 树」→ 4 条结果 → 点击首条 → 检查器加载 40 句字幕联动。
- 库：课程堆叠卡 + 5 张讲次卡渲染；点卡片展开字幕详情。
- 暗色：图标轨切换后全站令牌换值，状态栏显示「深色」。
- 响应式：1024 宽侧栏折叠、主区单列；控制台无报错。

## 阶段七 · 外链 + 封面 + 字幕 + B 站嵌入播放一体化（2026-10-28）

外链（source_url）、封面（pic/cover_url）、字幕与嵌入播放作为一条完整链路实现：

- `apps/api/store.py`：videos 表新增 `cover_url` 列（CREATE TABLE + 旧库幂等 ALTER），入库、`list_videos`、`export_fixture` 全链路携带。
- `apps/api/bilibili.py`：`BiliVideo.pic` 取自 view 接口 `pic` 字段，导入时随字幕一并入库；preview 返回 `pic`。
- `apps/api/playback.py`：新增 `bilibili_embed_url`（player.bilibili.com/player.html，bvid/page/t 参数秒级定位）；B 站命中能力标签从 `external_seek` 升级为 `embed_seek`。
- 前端：`Video.cover_url` 类型；检查器对 platform=bilibili 讲次渲染官方嵌入 iframe，点击结果/字幕行时按字幕时间戳重定位（key 触发重载）；本地文件毫秒级对齐保留为次要路径；库页封面卡片优先使用真实封面图（失败回退渐变）；导入页预览显示封面。
- `scripts/build_demo_fixture.mjs`：从本地 B 站演示素材（manifest + 字幕 JSON + 封面，素材不入库不分发）生成 demo fixture，复刻 live 端 chunk_passages（20-45s/260 字）切块。演示素材版权归原视频作者及 Bilibili，仅用于站点演示。

验证（Demo 模式，headless Edge 实测，截图 `artifacts/screenshots/14-16`）：

- `python -m pytest tests/unit`：23 通过（含 `bilibili_embed_url` 新用例）；`npm run build` 通过。
- 搜索「SQL」→ 10 条命中 → 点击首条 → 检查器渲染 player.bilibili.com 嵌入播放器，`t=1832` 与命中片段 30:32 对齐，字幕 960 句联动高亮。
- 库页 6 张封面（2 课程堆叠 + 4 讲次）全部真实图片加载（naturalWidth > 0）。


## 证据索引

| 证据 | 路径 |
| --- | --- |
| Qoder 会话截图 | `artifacts/qoder-development/01-qoder-session.png` |
| M0 报告 | `artifacts/m0-report.json` |
| 评测指标 | `artifacts/metrics.json` |
| 验证日志 | `artifacts/verify/*.log` |
| 界面截图 | `artifacts/screenshots/*.png` |
| 复习候选证据 | `artifacts/review-candidates.json` |
| 样例查询证据 | `artifacts/sample-check.json` |

> 说明：Qoder 账号 UID 取自本机 Qoder Sites 发布记录中的 `ownerUid`，与账号头像 URL
> 中的用户 ID 一致，未做猜测。其余开发记录、命令输出与截图均为本次真实开发产生。

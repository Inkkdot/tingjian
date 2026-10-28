# 「听见」— 课程视频字幕检索与复习系统

把课程视频的字幕变成可检索、可跳转、可复习的学习资料。输入一句自然语言问题，
系统在 seekdb 中同时执行 **ik 全文检索** 与 **bge-small-zh 向量检索**，用 RRF 融合，
返回带时间戳的字幕片段；点击结果即可从对应时间点播放，并可生成限时复习清单。

> Qoder × OceanBase 参赛作品。核心检索与存储完全运行在 **seekdb v1.4.0.0** 上；
> 前端另有一份从真实 seekdb 导出的离线样例（Demo 模式），用于公开站点体验。
>
> 公开代码仓库：https://github.com/Inkkdot/tingjian

## 解决的问题

复习一门课时，常见的问题是「记得老师讲过，但不知道在第几讲第几分钟」。
视频进度条无法按语义定位，讲义和字幕又彼此分离。本项目把每讲字幕切成语义段落，
建立全文 + 向量双索引，并提供：

- 一句自然语言查询 → 命中片段 + 可播放时间戳 + 命中原因；
- 结果面板内嵌字幕上下文，点击时间戳定位本地视频；
- 按主题与时间预算生成复习清单，选入项附理由；
- 导入 SRT/VTT 或 B 站字幕轨，导入即建索引，重复导入幂等。

## 技术架构

```text
┌───────────────────────────── React 19 + Vite 6 + Tailwind 4 ─────────────────────────────┐
│ 搜索 / 我的库 / 复习清单 / 导入 / 设置        Live 模式 ⇄ Demo 模式（同一套 DTO）          │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │ /api (JSON)
┌───────────────────────────────────────▼──────────────────────────────────────────────────┐
│ FastAPI                                                                                  │
│  · 字幕解析（SRT/VTT）→ 20–45s / ≤260 字切块（1 条 cue 重叠）→ cues + passages           │
│  · 检索：MATCH…AGAINST（ik） + cosine_distance（HNSW/VSAG） → 关键词覆盖过滤 → RRF(k=60)  │
│  · 无答案门禁：语义最高分 < 0.49 时明确返回空结果与原因                                    │
│  · 复习清单：按预算做覆盖贪心选段，理由来自主题词覆盖                                    │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │ MySQL 协议 127.0.0.1:2881
┌───────────────────────────────────────▼──────────────────────────────────────────────────┐
│ seekdb v1.4.0.0                                                                          │
│  courses / videos / cues / passages(embedding VECTOR(512), FULLTEXT ik, VECTOR KEY HNSW) │
│  source_hash + index_version 支撑幂等导入与重建                                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘

Embedding: fastembed (ONNX) + BAAI/bge-small-zh-v1.5，512 维，查询前缀
「为这个句子生成表示以用于检索相关文章：」。模型不可用时健康检查如实降级为纯全文。
```

### seekdb 实际承担的能力

| 能力 | 实现 |
| --- | --- |
| 结构化存储 | 课程、视频、cue、passage 四表；`source_hash`、`index_version` |
| 全文检索 | `FULLTEXT KEY ... WITH PARSER ik` + `MATCH ... AGAINST` |
| 向量检索 | `VECTOR(512)` + `VECTOR KEY ... (DISTANCE=COSINE, TYPE=HNSW, LIB=VSAG)` + `cosine_distance` |
| 溯源 | 每个 passage 保存起止 cue 序号，结果可回查原文时间戳 |
| 幂等 | 同一 `platform + platform_video_id + part_index` 二次导入不增长行数 |

## 目录

```text
apps/api/            FastAPI 服务、seekdb 访问、字幕解析、检索、复习
apps/web/            React 前端（Live / Demo 共用组件）
fixtures/authored/   自撰 CC BY 4.0 字幕（5 讲，2 门课）
scripts/             db_probe / verify_m0 / import_fixture / reindex / eval_run / export_demo
tests/unit/          字幕解析、切块、检索逻辑、跳转 URL 单测
tests/integration/   真实 seekdb 建表、幂等导入、真实向量与混合检索
artifacts/           真实执行输出（探针、M0 报告、评测指标、验证日志）
DEVELOPMENT_LOG.md   Qoder 开发记录（提交材料见 SUBMISSION.md）
```

## 快速开始

### 0. 环境

- Python 3.11+（验证环境为 3.13）
- Node.js 20+（验证环境为 24）
- Docker，能拉取 `quay.io/oceanbase/seekdb:latest`（容器内版本 5.7.25-OceanBase seekdb-v1.4.0.0）
- 首次运行 embedding 需联网下载约 90 MB 的 ONNX 模型；之后走本地缓存

### 1. 启动 seekdb

```bash
docker run -d --name seekdb-sdd -p 2881:2881 quay.io/oceanbase/seekdb:latest
```

等待容器就绪后，服务会自动建库建表（默认库名 `tingjian`，root 空密码）。

### 2. 安装依赖

```bash
# Windows Git Bash / PowerShell 均可
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r apps/api/requirements.txt

cd apps/web && npm install && cd ../..
```

Linux/macOS 将 `.venv/Scripts/python.exe` 换成 `.venv/bin/python`。

### 3. 导入样例字幕

```bash
.venv/Scripts/python.exe scripts/import_fixture.py
```

预期输出 5 行导入结果（`status=created`，cue/passage 行数），并写入
`artifacts/fixture-import.json`。

### 4. 启动后端（本仓库验证端口 8001）

```bash
.venv/Scripts/python.exe -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8001
```

打开 <http://127.0.0.1:8001/api/health> 应看到：

```json
{"status":"ok","database":"tingjian","embedding_model":"bge-small-zh-v1.5","vector_search":true,"hybrid_search":true}
```

> 8000 端口可根据环境自行更换，同时修改 `apps/web/vite.config.ts` 的 proxy。

### 5. 启动前端

```bash
cd apps/web && npm run dev
```

打开 <http://127.0.0.1:5173>，右上角应显示 `LIVE · seekdb`。

## 验证样例（可按步骤执行）

1. 进入「搜索」，输入 `B+ 树的叶子节点怎么连接`。
   - 预期：返回 5–10 条结果，Top1 属于「第 2 讲 索引与 B+ 树」，附带命中原因与时间戳。
2. 点击 Top1。
   - 预期：右侧出现该段字幕上下文；时间戳 chip 显示片段起止时间（实测 `00:43 – 01:24`）。
3. 点击时间戳，选择本地同一视频文件。
   - 预期：本地视频跳转到对应秒数；未选择文件时明确提示需要本地视频。
4. 进入「复习清单」，主题填 `事务隔离`，预算选 15 分钟，生成。
   - 预期：返回不超过 15:00 的条目列表，每项含选入理由与跳转时间。
5. 输入无答案问题（如 `量子纠缠的贝尔不等式`）。
   - 预期：返回空结果并说明「语料中未找到足够相关的内容」，不编造片段。
6. 进入「设置」。
   - 预期：显示运行时能力、Live/Demo 差异、真实评测指标与已知限制。

命令行的等价检索验证：

```bash
curl "http://127.0.0.1:8001/api/search?q=B%2B%20%E6%A0%91&mode=hybrid&limit=3"
```

返回中应包含 `jump_url`、`cue_start_ms`、`passage_id`、`capability: "local_select"`。

## 测试与 DoD

```bash
# 一条命令跑完整门禁与验证（Git Bash / WSL）
bash scripts/verify.sh
```

等价的手工命令：

```bash
.venv/Scripts/python.exe scripts/db_probe.py            # seekdb 建表/写入/FTS+向量 DDL
.venv/Scripts/python.exe scripts/verify_m0.py           # M0：导入、幂等、SELECT 溯源、检索
.venv/Scripts/python.exe -m pytest tests/unit -q        # 11 passed
.venv/Scripts/python.exe -m pytest tests/integration -q # 2 passed（真实 seekdb）
.venv/Scripts/python.exe scripts/eval_run.py --output artifacts/metrics.json
cd apps/web && npm run build
```

当前真实结果（2026-10-28，17 条有答案 + 3 条无答案查询，±15s 判定）：

| 模式 | Hit@3 | 无答案识别 | 平均延迟 |
| --- | --- | --- | --- |
| 全文（ik） | 17/17 | 3/3 | 197.9 ms |
| 向量（bge-small-zh） | 16/17 | 3/3 | 210.7 ms |
| 混合（RRF k=60） | 17/17 | 3/3 | 347.0 ms |

向量模式的失败样本是 `最左前缀原则`（语料中表述为「联合索引的最左列」），
已在 `artifacts/metrics.json` 原样保留，没有为了分数调整标注。
M0 报告见 `artifacts/m0-report.json`，完整验证日志见 `artifacts/verify/`。

### 索引重建

修改切块规则或更换 embedding 后：

```bash
.venv/Scripts/python.exe scripts/reindex.py                # 全部讲次
.venv/Scripts/python.exe scripts/reindex.py --video-id v-xxx --skip-embeddings
.venv/Scripts/python.exe scripts/reindex.py --bump-version # 先推进索引版本
```

重建只替换 passage 与向量，不动 cue 原文；结果写入 `artifacts/reindex.json`。

## Live 模式与 Demo 模式

| | Live | Demo |
| --- | --- | --- |
| 数据源 | 本机 seekdb | `apps/web/public/fixture.json`（从真实 seekdb 导出） |
| 检索 | seekdb 全文 + 向量 + RRF | 浏览器内关键词过滤，仅作展示 |
| 导入 | 可用 | 禁用并提示 |
| 适合 | 本地复现、评审验证 | 公开站点无后端时体验界面 |

Demo 模式的所有结果页均有「离线样例」标识，不宣称语义检索能力。
构建静态演示站：

```bash
cd apps/web && npm run build:demo   # 产物 dist-demo/
```

## B 站字幕的限制与兜底

- 仅处理**公开字幕轨**，不向服务端传递任何 Cookie；代码中没有 Cookie 参数入口。
- 当前环境 B 站公开轨接口返回需要登录，因此 `verify_m0.py` 记录
  `bilibili_public_track_available = False`，M0 使用**用户导出的 SRT + source_url** 路径通过。
- 导入页保留 B 站预览/导入入口，失败时返回可读错误，不伪造成功。
- 推荐兜底：用浏览器用户脚本导出 SRT（登录态留在浏览器侧），再上传 SRT。

## 已知限制

- 语义检索对语料中未出现的同义表述仍可能失败（见上表 1 条 miss）。
- 本地视频跳转依赖用户选择同一文件；不代理、不下载视频流。
- 复习清单为 P2 功能，当前按时间预算与主题覆盖选段，未实现 MMR。
- Demo 模式不具备真实检索能力，只用于界面演示。
- 尚无真实用户使用规模数据；公开站点访问统计可在上线后补充。

## 提交材料索引

| 材料 | 位置 |
| --- | --- |
| 代码仓库 | [https://github.com/Inkkdot/tingjian](https://github.com/Inkkdot/tingjian)（公开） |
| 运行说明 | 本 README |
| 验证样例 | 上文「验证样例」+ `artifacts/sample-check.json` |
| Qoder 开发记录 / UID | `DEVELOPMENT_LOG.md`；UID `01a17e94-5842-7b39-86cd-7549fcae9edf` |
| 真实执行证据 | `artifacts/`、`artifacts/verify/` |
| 第三方来源 | `THIRD_PARTY_NOTICES.md` |

## 设计文档

- `ARCHITECTURE_FINAL_v1.0.md`：模块边界、优先级、M0 门禁、DoD
- `FRONTEND_v0.9.md`：界面结构与交互

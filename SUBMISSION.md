# 提交材料 · 听见（Tingjian）

> 最后更新：2026-10-28。站点在评审结束前保持在线，不暂停、不删除。
> 本材料所有数据均来自本机真实运行；失败样本原样保留，未调参掩盖。

## 0. 关键信息

| 项目 | 内容 |
| --- | --- |
| 项目名称 | 听见 · 课程视频字幕检索与复习系统 |
| 项目网站 | https://tingjian-qm1uiydhbox.qoder.zone |
| 在线体验入口 | https://tingjian-qm1uiydhbox.qoder.zone/demo/index.html?demo=1 |
| 代码仓库（公开） | https://github.com/Inkkdot/tingjian |
| 主分支 | `main` |
| 代码与证据提交 | 公开仓库 `main@7c5a9c1`（修复、回归测试与验证证据；本文件回填 SHA 的后续提交仅改文档） |
| 参赛仓库 | `SakuyaInazaki/powercontext-2026`，分支 `2026-competition-ecosystem`，项目目录 `qoder/tingjian/`，同步提交 `691e5693` |
| 指定技术 | seekdb v1.4.0.0（本项目选用 seekdb，未使用 PowerContext，也不宣称使用） |
| Qoder 账号 UID | `01a17e94-5842-7b39-86cd-7549fcae9edf` |
| 验证环境 | Windows 11 x64；Python 3.13.1；Node.js 24.14.0；Docker |
| 全量验证 | `bash scripts/verify.sh`：M0、单测 24、集成 2、评测、前端构建全部通过 |

## 1. 项目网站（题面第 1 项）

- 地址：<https://tingjian-qm1uiydhbox.qoder.zone>，托管于 Qoder Sites，**公开访问，无需登录**。
- 站点包含题面要求的全部内容：
  - 项目简介与问题场景（首页 Hero、「它解决什么」）；
  - 核心功能：字幕落库与溯源、全文 + 向量混合检索与拒答、预算内复习清单；
  - 真实界面截图：检索结果、B 站内嵌播放器 + 字幕检查器、复习清单、设置页、SRT 导入；
  - 在线 Demo 入口（右上角「在线演示」与正文按钮）；
  - 公开代码仓库链接；
  - 运行步骤、seekdb 能力、真实检索评测、Qoder 开发阶段与已知限制。
- 在线 Demo：<https://tingjian-qm1uiydhbox.qoder.zone/demo/index.html?demo=1>
  - 数据为 B 站公开课程字幕快照（4 讲 / 2,106 条字幕 / 229 个片段），封面与字幕不进入公开仓库；
  - Demo 在浏览器内完成关键词过滤与时间戳定位，页面明确标注「离线样例」，不冒充 seekdb 混合检索。
- 站点为 Qoder Sites 不可变快照；本次更新后重新发布，评审期内保持在线。

## 2. 代码仓库（题面第 2 项）

- 公开仓库：<https://github.com/Inkkdot/tingjian>，分支 `main`，未登录可直接访问。
- 仓库根目录即完整工程：后端 `apps/api/`、前端 `apps/web/`、样例字幕 `fixtures/authored/`、
  脚本 `scripts/`、测试 `tests/`、真实执行产物 `artifacts/`。
- 参赛仓库同步：`SakuyaInazaki/powercontext-2026` 的 `2026-competition-ecosystem` 分支，
  完整项目位于 `qoder/tingjian/`，含站点快照 `site/` 与验证证据，供评审在赛事仓库内直接查看。
  本次同步提交：`691e569337810dc4fcdb4f6be676383b89627154`。
- 本次提交对应 `main` 上的提交：`7c5a9c157a7ea05d1bb34df9572a5d623bd5912d`
  （含修复、契约测试与证据；之后仅回填 SHA 的文档提交不改变代码）。
- 公开仓库内 `site/` 是早期自建语料（5 讲）的站点快照，`site/demo` 亦为自建语料，均不含 B 站素材；
  线上站点与参赛仓库 `qoder/tingjian/site/` 同步，使用 B 站字幕快照。
- 仓库不包含任何真实 API Key、密码、Cookie、Token 或验证行；配置示例均为本地默认值或占位符。

## 3. 运行说明（题面第 3 项）

### 3.1 环境

| 组件 | 验证版本 | 说明 |
| --- | --- | --- |
| 操作系统 | Windows 11 10.0.26200 x64 | Linux/macOS 路径替换为 `.venv/bin/python` |
| Python | 3.13.1 | 要求 3.11+ |
| Node.js / npm | 24.14.0 / 11.9.0 | 要求 Node 20+ |
| Docker | 可用 | 运行 seekdb 官方镜像 |
| seekdb | `5.7.25-OceanBase seekdb-v1.4.0.0` | 镜像 `quay.io/oceanbase/seekdb:latest` |
| Embedding | `BAAI/bge-small-zh-v1.5`，512 维 | fastembed ONNX；首次运行下载约 90 MB，之后走本地缓存 |

### 3.2 依赖（均已固定版本）

后端 `apps/api/requirements.txt`：

```text
fastapi==0.162.0
uvicorn==0.54.0
PyMySQL==1.2.3
python-multipart==0.0.32
httpx==0.28.1
fastembed==0.9.1
jieba==0.42.1
numpy==2.5.4
pytest==9.2.0
```

前端 `apps/web/package.json`：React 19、React DOM 19、TypeScript 5.7、Vite 6、Tailwind CSS 4、
`@tailwindcss/vite` 4、`@vitejs/plugin-react` 4、lucide-react 0.468。

### 3.3 seekdb 部署与接入

```bash
docker run -d --name seekdb-sdd -p 2881:2881 quay.io/oceanbase/seekdb:latest
```

- 连接方式：MySQL 协议 `127.0.0.1:2881`，默认用户 `root`、空密码、库名 `tingjian`。
- 服务启动时自动建库建表（`ensure_schema`），无需手工执行 DDL；`/api/health` 会报告
  `store_ok`、数据库版本与表计数。
- 可通过环境变量覆盖连接信息（示例为占位符）：

  | 变量 | 默认值 | 示例 |
  | --- | --- | --- |
  | `SEEKDB_HOST` | `127.0.0.1` | `<your-seekdb-host>` |
  | `SEEKDB_PORT` | `2881` | `2881` |
  | `SEEKDB_USER` | `root` | `<your-user>` |
  | `SEEKDB_PASSWORD` | 空 | `<your-password>` |
  | `SEEKDB_DATABASE` | `tingjian` | `tingjian` |

- 数据模型：`courses` / `videos` / `cues` / `passages` 四表。
  `passages` 上同时建立 `FULLTEXT KEY ... WITH PARSER ik` 与
  `VECTOR KEY ... (DISTANCE=COSINE, TYPE=HNSW, LIB=VSAG)`，并保存 `source_hash`、`index_version`。
- 检索链路：`MATCH ... AGAINST`（ik）与 `cosine_distance`（HNSW/VSAG）分别召回，
  关键词覆盖过滤后按 RRF（k=60）融合；无答案门禁在语义最高分低于阈值时返回空结果与原因。
- 建表、全文、向量与双索引共存的实测 DDL 与结果见 `artifacts/db-probe.json`
  （探针脚本 `scripts/db_probe.py`）。

### 3.4 完整启动步骤

```bash
# 1. seekdb
docker run -d --name seekdb-sdd -p 2881:2881 quay.io/oceanbase/seekdb:latest

# 2. Python 依赖
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r apps/api/requirements.txt

# 3. 前端依赖
cd apps/web && npm install && cd ../..

# 4. 导入 5 讲样例语料（等待 seekdb 就绪后执行）
.venv/Scripts/python.exe scripts/import_fixture.py

# 5. 启动后端（验证使用 8001）
.venv/Scripts/python.exe -m uvicorn main:app --app-dir apps/api --host 127.0.0.1 --port 8001

# 6. 另开终端启动前端
cd apps/web && npm run dev        # http://127.0.0.1:5173
```

健康检查预期：

```json
{"mode":"live","store_ok":true,"database_version":"5.7.25-OceanBase seekdb-v1.4.0.0",
 "embedding_model":"bge-small-zh-v1.5","course_count":2,"video_count":5,
 "cue_count":187,"passage_count":23,"embedded_passage_count":23}
```

前端右上角应显示 `LIVE · seekdb`。命令行验证：

```bash
curl --get --data-urlencode "q=B+ 树的叶子节点怎么连接" \
     --data "mode=hybrid" --data "limit=3" \
     http://127.0.0.1:8001/api/search
```

### 3.5 一条命令完成验收

```bash
bash scripts/verify.sh
```

依次执行 `db_probe` → `verify_m0` → 单元测试 → 集成测试 → 评测 → 前端构建，
日志写入 `artifacts/verify/`。本次结果：M0 全部通过、单元 24 通过、集成 2 通过、
评测完成、`npm run build` 成功。

### 3.6 配置与凭据

- 仓库内没有真实凭据；seekdb 使用镜像默认的本地 root 空密码，仅用于本机验证。
- B 站可选登录态只从本机环境变量 `BILIBILI_COOKIE` 或仓库外文件 `BILIBILI_COOKIE_FILE` 读取，
  Cookie 不写库、不返回前端、不进日志；未配置时使用匿名公开轨或 SRT 上传回退。
- 所有示例配置均使用 `<your-...>` 占位符。

## 4. 可执行验证样例（题面第 4 项，指定技术：seekdb）

### 4.1 初始数据

`fixtures/authored/` 为自撰 CC BY 4.0 字幕，共 2 门课、5 讲。执行：

```bash
.venv/Scripts/python.exe scripts/import_fixture.py
```

导入后 seekdb 中的真实计数（`/api/health`、`artifacts/m0-report.json`）：

| 课程 | 讲次 | cue（字幕句） | passage（检索片段） | 向量 |
| --- | ---: | ---: | ---: | ---: |
| 数据库系统原理 | 3 | 117 | 15 | 15 |
| 操作系统 | 2 | 70 | 8 | 8 |
| 合计 | 5 | 187 | 23 | 23 |

### 4.2 输入与执行步骤

1. 按 3.4 启动 seekdb、后端与前端；
2. 调用：

   ```bash
   curl --get --data-urlencode "q=B+ 树的叶子节点怎么连接" \
        --data "mode=hybrid" --data "limit=3" \
        http://127.0.0.1:8001/api/search \
        -o artifacts/verification-search.json
   ```

3. 或在前端搜索框输入同一问题，观察结果卡与右侧检查器。

### 4.3 预期结果与实际结果

实际返回（`artifacts/verification-search.json`，2026-10-28 本机实测；同输入重复执行 Top3 一致）：

| 排名 | 讲次 | 时间戳 | 命中原因 | 融合分 | 全文分 | 语义分 |
| ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | 第 2 讲 索引与 B+ 树 | 00:04 – 00:47.300 | 关键词 + 语义共同命中 | 0.032787 | 1.004184 | 0.470424 |
| 2 | 第 2 讲 索引与 B+ 树 | 00:43 – 01:24.090 | 关键词 + 语义共同命中 | 0.032258 | 0.862551 | 0.431129 |
| 3 | 第 1 讲 事务与 ACID | 03:11.700 – 03:31.720 | 关键词 + 语义共同命中 | 0.031746 | 0.583353 | 0.398170 |

- 候选集同时包含全文召回 4 条与语义召回 23 条，证明两路检索都在 seekdb 内真实执行；
- Top2 即直接回答「叶子节点之间用链表连接，方便范围扫描」的片段；
- 每条结果带 `passage_id`、`cue_start_seq`、`cue_end_seq`、`playback_capability: "local_select"`，
  可回查原始字幕与时间戳。

预期判定：Top3 首位命中「第 2 讲 索引与 B+ 树」，且结果同时带全文分与语义分。

### 4.4 seekdb 能力证据

| 验证项 | 实际结果 | 证据 |
| --- | --- | --- |
| 数据库版本 | `5.7.25-OceanBase seekdb-v1.4.0.0` | `artifacts/db-probe.json` |
| 建表 / 写入 / 查询 | 3 行写入并可查回 | `artifacts/db-probe.json` |
| 中文全文检索 | `FULLTEXT ... WITH PARSER ik` 命中 1 条，score 1.0652 | `artifacts/db-probe.json` |
| 向量检索 | `cosine_distance` 排序正确（自身 0.0） | `artifacts/db-probe.json` |
| 双索引共存 | FULLTEXT + VECTOR KEY 同表建立成功 | `artifacts/db-probe.json` |
| SRT 导入写库 | 43 条字幕 / 6 个片段 / 6 个向量，覆盖率 43/43 | `artifacts/m0-report.json` |
| 幂等导入 | 同源二次导入 `unchanged`，计数保持 5 / 187 / 23 / 23 | `artifacts/m0-report.json` |
| 时间戳溯源 | 按 `video_id` SELECT 返回 cue 原文与起止毫秒 | `artifacts/m0-report.json` |
| 真实 B 站元数据 | BV1pW411W7Do，120,826 秒，分 P 列表可读 | `artifacts/m0-report.json` |
| 检索评测 | 全文 17/17、语义 16/17、混合 17/17；无答案 3/3 | `artifacts/metrics.json` |

评测条件：20 条人工标注查询（17 条有答案、3 条无答案），Top3 命中同一讲次且起点在 ±15 秒内；
延迟为单机 Docker 实测。失败样本「最左前缀原则」（语义模式）原样保留。

另存 7 条查询的 Top3 轨迹：`artifacts/sample-check.json`。

### 4.5 辅助样例：在线 Demo 与导入

在线 Demo（不依赖后端，仅演示界面与定位）：

- 打开 <https://tingjian-qm1uiydhbox.qoder.zone/demo/index.html?demo=1>；
- 搜索「操作系统」：返回 10 条片段，首条「操作系统简介」为 `00:01 – 00:45`；
- 右侧检查器内嵌 B 站官方播放器，展开可见该讲 578 句字幕；拖拽分隔条可将检查器从 380px 放大到 680px，双击复位；
- Demo 的检索是浏览器内关键词过滤，页面标注「离线样例」，不作为 seekdb 能力证据。

Live 导入：`scripts/verify_m0.py` 通过 `POST /api/import/srt` 上传真实 SRT，
得到 43 条字幕 / 6 个片段 / 6 个向量并写回 seekdb（见上表）。

## 5. Qoder 开发记录（题面第 5 项）

| 材料 | 位置 |
| --- | --- |
| Qoder 开发会话截图 | `artifacts/qoder-development/01-qoder-session.png`（Qoder 桌面端任务、工具调用与执行状态） |
| 开发记录 | `DEVELOPMENT_LOG.md`：需求拆解、阶段实现、真实命令输出、缺陷与修复 |
| 全量验收日志 | `artifacts/verify/`：db_probe、verify_m0、unit、integration、eval、web_build |
| 评测明细 | `artifacts/metrics.json`（含失败样本） |
| 账号 UID | `01a17e94-5842-7b39-86cd-7549fcae9edf` |

UID 取自本机 Qoder Sites 发布记录的 `ownerUid`，并与账号头像 URL 中的用户 ID 一致；
仅用于赛事身份核验，不含任何凭据。

## 6. 使用效果材料（题面可选项）

- 检索效果（可复核）：`artifacts/metrics.json` 的 Hit@3 与拒答率，见 4.4；混合模式 17/17，拒答 3/3。
- 站点访问（Qoder Sites 后台，2026-10-28 查询）：近 24 小时 PV 47、估算 UV 8。
  该统计覆盖不完整且包含开发自测访问，**不作为用户规模或提效比例的证据**。
- 未虚构用户数、提效比例或第三方评价；无真实用户调研数据时如实标注「暂无」。

## 7. 合规与第三方材料

- 仓库与站点不含真实 API Key、密码、Cookie、Token 或平台验证行；配置示例使用占位符。
- B 站封面与字幕仅用于功能演示，不进入公开仓库；公开 Demo 由浏览器加载 B 站官方播放器。
- 第三方依赖与数据来源、许可证见 `THIRD_PARTY_NOTICES.md`：
  fastembed、bge-small-zh-v1.5、jieba、FastAPI、React、Vite、Tailwind 等；
  自撰字幕以 CC BY 4.0 提供；FlowOSS 仅作设计参考。
- 本项目使用 seekdb 作为指定技术，未使用 PowerContext；不把 Postgres、SQLite 或浏览器过滤
  标成 seekdb 能力。
- 站点在评审结束前保持在线。

## 8. 验收对照（题面 3.1 / 3.2 与提交材料）

| 题面要求 | 对应材料 | 状态 |
| --- | --- | --- |
| 网站可公开访问、无需登录 | 站点首页与 Demo 链接；Qoder Sites access policy = public | 通过 |
| 网站含简介、问题、功能、Demo 截图、仓库链接、体验入口 | 首页各分区与在线 Demo | 通过 |
| 代码仓库公开或评审可访问 | `Inkkdot/tingjian`（public）；参赛仓库 `qoder/tingjian/` | 通过 |
| 完整运行说明：环境、依赖、seekdb 部署与接入 | 第 3 节 + `README.md` | 通过 |
| 可执行验证样例：初始数据、输入、步骤、预期、证据 | 第 4 节 + `artifacts/verification-search.json`、`db-probe.json`、`m0-report.json` | 通过 |
| 证明指定技术真实生效 | seekdb 版本、ik 全文、HNSW 向量、双索引、真实查询分数与候选数 | 通过 |
| Qoder 为主要开发工具且可核对 | Qoder 会话截图、`DEVELOPMENT_LOG.md`、UID | 通过 |
| 使用效果材料（可选） | 检索评测 + 站点访问统计（含覆盖说明） | 提交 |
| 配置占位符、无敏感凭据、第三方署名 | 第 7 节 + `THIRD_PARTY_NOTICES.md` | 通过 |
| 评审结束前不暂停/删除站点 | 站点持续在线 | 遵守 |

## 9. 真实性与已知限制

- 所有指标来自本机真实运行；失败样本与波动延迟原样保留。
- 语义检索对语料中未出现的同义表述仍会失败（如「最左前缀原则」），未通过改标注掩盖。
- B 站匿名公开字幕轨在本机网络时可用时不稳；可选本机登录态读取 AI 字幕轨，并在入库前按分 P
  时长校验覆盖率，不符时返回 `TRACK_MISMATCH`，不会静默写入错误语料。
- 本地视频跳转依赖用户选择同一文件；不代理、不下载视频流。
- Demo 模式不具备真实检索能力，只用于界面演示。
- 尚无真实用户规模数据；站点访问统计覆盖不完整且含自测访问。

# 提交材料 · 听见

## 项目网站

- 地址：https://tingjian-qm1uiydhbox.qoder.zone
- 可见范围：公开（任何人都可访问，无需登录）
- 体验入口：https://tingjian-qm1uiydhbox.qoder.zone/demo/?demo=1
- 发布平台：Qoder Sites
- 站点源码快照：`site/`（与线上发布内容一致）

站点内容：项目简介、问题与场景、核心功能、真实界面截图、检索评测数据、运行步骤、
代码仓库链接、Qoder 开发记录与离线体验入口。

## 代码仓库

- 仓库：https://github.com/Inkkdot/tingjian（公开）
- 分支：`main`
- 目录：仓库根目录；同内容同步保留于参赛仓库的 `qoder/tingjian/`
- 基线：基于 `oceanbase/powercontext` 的 `2026-competition-ecosystem` 分支
- 可见性：公开仓库，未登录可直接访问

## 运行说明

见仓库内 `README.md`。主要步骤：

1. 启动 seekdb Docker 容器（端口 2881）
2. 创建虚拟环境并安装 `apps/api/requirements.txt`
3. 运行 `scripts/import_fixture.py` 导入样例语料
4. 启动 FastAPI（端口 8001）与前端开发服务器
5. 运行 `bash scripts/verify.sh` 完成 M0、单元、集成、评测与构建验收

## 验证样例

查询「B+ 树的叶子节点怎么连接」，预期：

- 首条结果为「第 2 讲 索引与 B+ 树」
- 片段区间 `00:43–01:24`
- 打开字幕检查器可见该讲 40 条原始字幕
- 结果理由标注全文与语义共同命中

对应截图：`artifacts/screenshots/02-results.png`、`03-inspector.png`。

## 验收对照（题面 3.1 与提交材料）

| 要求 | 证据 | 状态 |
| --- | --- | --- |
| 网站未登录可访问 | 匿名请求 `/` 与 `/demo/?demo=1` 均返回 200；站点访问策略为 public | 通过 |
| 按运行说明可启动并复现 | `README.md` + `scripts/verify.sh`；M0 PASS，单元 12、集成 2、评测与前端构建日志在 `artifacts/verify/` | 通过 |
| Qoder 参与可核对 | `artifacts/qoder-development/01-qoder-session.png`、`DEVELOPMENT_LOG.md`、账号 UID | 通过 |
| seekdb 实际发挥作用 | 真实 seekdb 1.4 容器；187 条字幕、23 个片段、23 个向量；M0、评测与查询轨迹可查 | 通过 |
| 完整源码可审阅 | 公开仓库 [https://github.com/Inkkdot/tingjian](https://github.com/Inkkdot/tingjian)，匿名可访问 | 通过 |
| 验证样例可按步骤执行 | 见「验证样例」，另有 `artifacts/sample-check.json` | 通过 |
| 使用效果材料（可选） | 尚无真实用户数据，未虚构访问量或提效比例 | 未提交 |

## Qoder 开发记录

- `DEVELOPMENT_LOG.md`：需求拆解、分阶段实现、真实命令输出、缺陷与修复
- `artifacts/qoder-development/01-qoder-session.png`：Qoder 桌面端开发会话截图
- `artifacts/verify/`：全量验收日志
- `artifacts/metrics.json`：评测指标（含失败样本）
- Qoder 账号 UID：`01a17e94-5842-7b39-86cd-7549fcae9edf`

> UID 取自本机 Qoder Sites 发布记录中的 `ownerUid`，并与账号头像 URL 中的用户 ID
> 一致；未做猜测或伪造。该值仅用于赛事身份核验，不含任何凭据。

## 真实性与限制

- 所有指标来自本机真实运行，失败样本保留，未调参掩盖。
- B 站匿名公开字幕轨在本机网络不可用；新增可选登录态（本机环境变量或仓库外文件）读取 AI 字幕轨，
  导入前按时长校验覆盖率，未配置时保留 SRT 回退。M0 仍使用真实 SRT 完成，不使用伪造字幕后端。
- 样例语料为自建、可复现的教学内容，仅用于功能验证。
- 尚无真实用户使用统计，站点不展示使用人数或提效比例。
- 离线 Demo 仅做浏览器内关键词过滤，页面已明确标注，不冒充 seekdb 混合检索。

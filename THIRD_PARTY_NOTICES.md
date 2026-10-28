# 第三方来源与许可

本项目没有直接复制第三方项目的源代码。以下列出运行时依赖、模型、数据和设计参考。

## 运行时依赖

| 组件 | 版本 | 用途 | 许可（以上游声明为准） |
| --- | --- | --- | --- |
| seekdb | v1.4.0.0（`quay.io/oceanbase/seekdb:latest`） | 全文/向量/结构化存储 | Apache-2.0 |
| FastAPI | 0.162.0 | HTTP API | MIT |
| Uvicorn | 0.54.0 | ASGI 服务器 | BSD-3-Clause |
| PyMySQL | 1.2.3 | MySQL 协议客户端 | MIT |
| python-multipart | 0.0.32 | 文件上传 | Apache-2.0 |
| HTTPX | 0.28.1 | B 站公开接口请求 | BSD-3-Clause |
| fastembed | 0.9.1 | ONNX embedding 推理 | Apache-2.0 |
| NumPy | 2.5.4 | 向量归一化 | BSD-3-Clause |
| jieba | 0.42.1 | 查询关键词抽取 | MIT |
| pytest | 9.2.0 | 测试 | MIT |
| React / React DOM | 19.x | 前端运行时 | MIT |
| Vite | 6.x | 前端构建 | MIT |
| Tailwind CSS | 4.x | 样式 | MIT |
| lucide-react | 0.468.x | 图标 | ISC |
| TypeScript | 5.7.x | 类型检查 | Apache-2.0 |

完整依赖树以 `apps/api/requirements.txt`、`apps/web/package.json` 与
`apps/web/package-lock.json` 为准。

## 模型

- **BAAI/bge-small-zh-v1.5**，512 维中文 embedding，经 fastembed 下载 ONNX 版本。
  模型许可以 [BAAI/bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5) 仓库声明为准（MIT）。
  本项目只调用推理，不重新分发模型权重；`fastembed_cache/` 已排除在仓库之外。

## 数据

- `fixtures/authored/*.srt`：为本项目自撰的课程字幕样例，采用 **CC BY 4.0**，
  不含任何真实用户、教师或课程平台的音视频内容。
- `fixtures/authored/make_fixtures.py`：生成上述样例的脚本，可复现。
- B 站仅通过公开接口读取公开字幕轨；不采集、不存储 Cookie，不下载视频流。

## 设计参考

以下项目仅作为交互/流程设计参考，未复制源码：

- BiliNote（浏览器侧字幕与时间戳交互）：<https://github.com/AliceDel66/BiliNote>
- BiliNote（AI 笔记工作流）：<https://github.com/JefferyHcool/BiliNote>
- seekdb 文档与示例：<https://github.com/oceanbase/seekdb>

## 字体

前端不打包字体文件，使用系统字体栈（`--vm-font` / `--vm-font-mono`）。

import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, Link2, Loader2, Search, UploadCloud } from "lucide-react";
import { api, errorText } from "../lib/api";
import { addDemoLesson, parseSubtitleText } from "../lib/demoImport";
import type { Course } from "../lib/types";

interface ImportPageProps {
  demo: boolean;
  courses: Course[];
  onImported: () => Promise<void> | void;
  onOpenSearch: () => void;
}

interface Preview {
  bvid?: string;
  title?: string;
  owner?: string;
  pic?: string;
  duration_ms?: number;
  parts?: Array<{ page: number; title: string; duration_ms: number; cid: number }>;
  part_index?: number;
  part_title?: string;
  subtitle_tracks?: Array<{ lan?: string; lan_doc?: string }>;
  track_available?: boolean;
  authenticated?: boolean;
  fallback_hint?: string;
}

interface ImportResult {
  video_id?: string;
  status?: string;
  cue_count?: number;
  passage_count?: number;
  embedded_count?: number;
  source_hash?: string;
  warnings?: string[];
  course_name?: string;
  bilibili?: { title?: string; part_title?: string };
}

function previewLines(text: string): string[] {
  const lines = text.replace(/\r/g, "").split("\n");
  const out: string[] = [];
  for (let index = 0; index < lines.length && out.length < 5; index += 1) {
    if (!lines[index].includes("-->")) continue;
    const start = lines[index].split("-->")[0].trim().replace(",", ".");
    const body: string[] = [];
    let cursor = index + 1;
    while (cursor < lines.length && lines[cursor].trim() !== "" && !lines[cursor].includes("-->")) {
      body.push(lines[cursor].trim());
      cursor += 1;
    }
    out.push(`${start}  ${body.join(" ")}`);
    index = cursor;
  }
  return out;
}

export default function ImportPage({ demo, courses, onImported, onOpenSearch }: ImportPageProps) {
  const [tab, setTab] = useState<"bilibili" | "srt">(demo ? "srt" : "bilibili");
  const [url, setUrl] = useState("");
  const [courseId, setCourseId] = useState("");
  const [courseName, setCourseName] = useState("");
  const [term, setTerm] = useState("2026 秋");
  const [title, setTitle] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [offset, setOffset] = useState("0");
  const [part, setPart] = useState("1");
  const [force, setForce] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState<"preview" | "import" | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const disabled = busy !== null;

  function resetFeedback() {
    setResult(null);
    setError(null);
  }

  async function loadFile(next: File | undefined) {
    if (!next) return;
    setFile(next);
    resetFeedback();
    try {
      const text = await next.text();
      setLines(previewLines(text));
    } catch {
      setLines([]);
    }
  }

  async function doPreview() {
    if (!url.trim() || demo) return;
    resetFeedback();
    setPreview(null);
    setBusy("preview");
    try {
      const data = await api.previewBilibili(url.trim());
      setPreview(data as Preview);
      if (data.part_index) setPart(String(data.part_index));
    } catch (exc) {
      setError(errorText(exc));
    } finally {
      setBusy(null);
    }
  }

  async function doImportBilibili() {
    if (!url.trim() || demo) return;
    resetFeedback();
    setBusy("import");
    try {
      const data = await api.importBilibili({
        url: url.trim(),
        course_id: courseId || null,
        course_name: courseId ? null : courseName || null,
        term,
        part_index: Number(part) || 1,
        offset_ms: Number(offset) || 0,
      });
      setResult(data as ImportResult);
      await onImported();
    } catch (exc) {
      setError(errorText(exc));
    } finally {
      setBusy(null);
    }
  }

  async function doImportSrt() {
    if (!file) {
      setError("请先选择 SRT/VTT 文件");
      return;
    }
    resetFeedback();
    setBusy("import");
    try {
      if (demo) {
        const cues = parseSubtitleText(await file.text());
        const wanted = courseName.trim() || "未分类课程";
        const existing = courseId
          ? courses.find((course) => course.id === courseId)
          : courses.find((course) => course.name === wanted);
        const summary = addDemoLesson({
          courseId: existing?.id ?? `c-local-${Date.now().toString(36)}`,
          courseName: existing?.name ?? wanted,
          term,
          title: title.trim() || file.name.replace(/\.[^.]+$/, ""),
          sourceUrl: sourceUrl.trim(),
          offsetMs: Number(offset) || 0,
          cues,
        });
        setResult({
          video_id: summary.video.id,
          status: "demo-local",
          cue_count: summary.cueCount,
          passage_count: summary.passageCount,
          embedded_count: 0,
          source_hash: summary.sourceHash,
          course_name: summary.course.name,
          warnings: [
            "Demo 模式：字幕只写入当前页面的浏览器内临时索引，不会写入 seekdb；刷新页面后清空。",
          ],
        });
      } else {
        const form = new FormData();
        form.set("file", file);
        if (courseId) form.set("course_id", courseId);
        else if (courseName.trim()) form.set("course_name", courseName.trim());
        form.set("term", term);
        form.set("title", title);
        form.set("source_url", sourceUrl);
        form.set("offset_ms", String(Number(offset) || 0));
        form.set("force", force ? "true" : "false");
        const data = await api.importSrt(form);
        setResult(data as ImportResult);
      }
      await onImported();
    } catch (exc) {
      setError(errorText(exc));
    } finally {
      setBusy(null);
    }
  }

  const steps = demo
    ? [
      { label: "解析字幕", done: Boolean(result?.cue_count) },
      { label: "按上下文切句", done: Boolean(result?.passage_count) },
      { label: "浏览器内索引", done: Boolean(result?.video_id) },
    ]
    : [
      { label: "解析字幕", done: Boolean(result?.cue_count) },
      { label: "按上下文切句", done: Boolean(result?.passage_count) },
      { label: "生成向量", done: Boolean(result?.embedded_count), warn: Boolean(result && !result.embedded_count) },
      { label: "写入 seekdb", done: Boolean(result?.video_id) },
    ];

  return (
    <div>
      {demo && (
        <div className="notice">
          <strong>Demo 模式为静态站点：</strong>SRT / VTT 导入在浏览器内完成解析与切句，
          只写入当前页面的临时索引，不会写入 seekdb；B 站字幕轨导入需在本机 Live 模式运行。
        </div>
      )}

      <div className="card">
        <div className="tabs">
          <button className={`tab${tab === "bilibili" ? " active" : ""}`} onClick={() => setTab("bilibili")}>
            <Link2 size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
            B 站链接
          </button>
          <button className={`tab${tab === "srt" ? " active" : ""}`} onClick={() => setTab("srt")}>
            <FileText size={14} style={{ marginRight: 5, verticalAlign: -2 }} />
            SRT / VTT 上传
          </button>
        </div>

        <div className="form-grid">
          <div className="field">
            <label htmlFor="course">课程</label>
            <select id="course" value={courseId} onChange={(event) => setCourseId(event.target.value)} disabled={disabled}>
              <option value="">+ 新建课程</option>
              {courses.map((course) => (
                <option key={course.id} value={course.id}>{course.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="term">学期</label>
            <input id="term" value={term} onChange={(event) => setTerm(event.target.value)} disabled={disabled} />
          </div>
          {!courseId && (
            <div className="field">
              <label htmlFor="courseName">新课程名称</label>
              <input
                id="courseName"
                value={courseName}
                onChange={(event) => setCourseName(event.target.value)}
                placeholder="留空则归入「未分类课程」"
                disabled={disabled}
              />
            </div>
          )}
          <div className="field">
            <label htmlFor="offset">时间偏移（毫秒）</label>
            <input
              id="offset"
              type="number"
              step={1}
              value={offset}
              onChange={(event) => setOffset(event.target.value)}
              disabled={disabled}
            />
          </div>
          {tab === "bilibili" && (
            <div className="field">
              <label htmlFor="part">分 P</label>
              <input
                id="part"
                type="number"
                min={1}
                step={1}
                value={part}
                onChange={(event) => setPart(event.target.value)}
                disabled={disabled}
              />
            </div>
          )}
        </div>

        {tab === "bilibili" ? (
          <div style={{ marginTop: 14 }}>
            <div className="field">
              <label htmlFor="biliUrl">视频 URL</label>
              <input
                id="biliUrl"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://www.bilibili.com/video/BV...?p=1"
                disabled={disabled}
              />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
              <button
                className="btn"
                onClick={() => void doPreview()}
                disabled={disabled || demo || !url.trim()}
                title={demo ? "静态演示站无法直连 B 站接口" : undefined}
              >
                {busy === "preview" ? <Loader2 className="spin" size={15} /> : <Link2 size={15} />}
                读取元数据
              </button>
              <button
                className="btn primary"
                onClick={() => void doImportBilibili()}
                disabled={disabled || demo || !url.trim()}
                title={demo ? "B 站字幕轨导入需在本地 Live 模式运行" : undefined}
              >
                {busy === "import" ? <Loader2 className="spin" size={15} /> : <UploadCloud size={15} />}
                导入字幕轨
              </button>
            </div>
            {demo ? (
              <div className="notice" style={{ marginTop: 12 }}>
                静态演示站没有服务端代理与登录 Cookie，无法请求 B 站字幕接口。
                可切换到「SRT / VTT 上传」体验从解析、切句到检索定位的完整流程；B 站链接导入在本机 Live 模式可用。
              </div>
            ) : (
              <div className="notice" style={{ marginTop: 12 }}>
                未配置登录态时只读取匿名公开轨；在本机设置 BILIBILI_COOKIE 后可读取登录态字幕轨。
                Cookie 仅由本机服务端读取并只发往 B 站，不写库、不返回前端。若仍失败，
                请用「视频字幕提取器 Pro」导出 SRT 后上传。
              </div>
            )}
            {preview && (
              <div className="card" style={{ marginTop: 12, background: "var(--vm-surface-2)" }}>
                {preview.pic && (
                  <img
                    src={preview.pic}
                    alt="视频封面"
                    referrerPolicy="no-referrer"
                    style={{
                      width: "100%", aspectRatio: "16 / 9", objectFit: "cover",
                      borderRadius: "var(--vm-radius)", marginBottom: 10, display: "block",
                    }}
                    onError={(event) => {
                      event.currentTarget.remove();
                    }}
                  />
                )}
                <dl className="kv">
                  <dt>标题</dt><dd>{preview.title}</dd>
                  <dt>UP 主</dt><dd>{preview.owner}</dd>
                  <dt>BV / P</dt><dd className="mono">{preview.bvid} · P{preview.part_index}</dd>
                  <dt>分 P</dt><dd>{preview.parts?.length ?? 0} 个</dd>
                  <dt>登录态</dt>
                  <dd>
                    {preview.authenticated
                      ? <span className="badge ok">已配置</span>
                      : <span className="badge warn">未配置</span>}
                  </dd>
                  <dt>字幕轨</dt>
                  <dd>
                    {preview.track_available
                      ? <span className="badge ok">可用：{preview.subtitle_tracks?.map((track) => track.lan_doc || track.lan).join(" / ")}</span>
                      : <span className="badge warn">未发现</span>}
                  </dd>
                </dl>
                {preview.fallback_hint && <div className="notice">{preview.fallback_hint}</div>}
              </div>
            )}
          </div>
        ) : (
          <div style={{ marginTop: 14 }}>
            <div
              className={`dropzone${drag ? " drag" : ""}`}
              onClick={() => !disabled && fileRef.current?.click()}
              onDragOver={(event) => {
                event.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDrag(false);
                void loadFile(event.dataTransfer.files?.[0]);
              }}
              role="button"
              tabIndex={0}
              onKeyDown={(event) => {
                if (event.key === "Enter") fileRef.current?.click();
              }}
            >
              <UploadCloud size={22} style={{ marginBottom: 4 }} />
              <strong>{file ? file.name : "拖入或点击选择 SRT / VTT"}</strong>
              <span className="small muted">
                {file ? `${(file.size / 1024).toFixed(1)} KB · 前 5 句预览如下` : "UTF-8；也支持 UTF-8 BOM 与常见换行"}
              </span>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept=".srt,.vtt,text/plain"
              hidden
              onChange={(event) => void loadFile(event.target.files?.[0])}
            />
            {lines.length > 0 && (
              <div className="card" style={{ marginTop: 10, background: "var(--vm-surface-2)" }}>
                <div className="section-title" style={{ margin: "0 0 6px", fontSize: 13 }}>预览</div>
                {lines.map((line, index) => (
                  <div className="small mono" key={index} style={{ padding: "2px 0" }}>{line}</div>
                ))}
              </div>
            )}
            <div className="form-grid" style={{ marginTop: 12 }}>
              <div className="field">
                <label htmlFor="title">讲次标题</label>
                <input id="title" value={title} onChange={(event) => setTitle(event.target.value)} disabled={disabled} placeholder="例如：第 4 讲 事务隔离级别" />
              </div>
              <div className="field">
                <label htmlFor="sourceUrl">来源 URL（可选）</label>
                <input id="sourceUrl" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} disabled={disabled} placeholder="https://www.bilibili.com/video/BV..." />
              </div>
            </div>
            <label className="small" style={{ display: "flex", gap: 7, alignItems: "center", marginTop: 10 }}>
              <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} disabled={disabled} />
              内容变化时强制替换同来源旧版本（默认幂等：相同字幕不重复写入）
            </label>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button className="btn primary" onClick={() => void doImportSrt()} disabled={disabled || !file}>
                {busy === "import" ? <Loader2 className="spin" size={15} /> : <UploadCloud size={15} />}
                {demo ? "导入到浏览器演示索引" : "导入并写入 seekdb"}
              </button>
            </div>
          </div>
        )}

        {(result || error) && (
          <div style={{ marginTop: 16 }}>
            <div className="steps">
              {steps.map((step) => (
                <span
                  key={step.label}
                  className={`step${step.done ? " done" : step.warn ? " active" : ""}`}
                >
                  {step.done ? "✓ " : step.warn ? "! " : ""}{step.label}
                </span>
              ))}
            </div>
            {error && (
              <div className="notice error">
                <AlertTriangle size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
                {error}
              </div>
            )}
            {result && (
              <div className="notice ok">
                <CheckCircle2 size={14} style={{ marginRight: 4, verticalAlign: -2 }} />
                {demo
                  ? `导入完成：${result.cue_count} 条字幕、${result.passage_count} 个片段，已加入当前页面的演示索引。`
                  : `导入完成：${result.cue_count} 条字幕、${result.passage_count} 个片段、${result.embedded_count} 个向量。`}
                <div className="small mono">video_id {result.video_id} · source_hash {result.source_hash?.slice(0, 16)}…</div>
                {demo && (
                  <div className="small" style={{ marginTop: 4 }}>
                    未写入 seekdb，刷新页面后清空。
                    <button className="btn ghost sm" style={{ marginLeft: 8 }} onClick={onOpenSearch}>
                      <Search size={13} /> 去搜索页验证
                    </button>
                  </div>
                )}
                {result.warnings?.map((warning) => <div className="small" key={warning}>{warning}</div>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ArrowUpRight, Loader2, Play, Search, Upload, X,
} from "lucide-react";
import { api, errorText, fmtTime } from "../lib/api";
import { demoCues, demoSearch } from "../lib/demo";
import type {
  Course, Cue, Fixture, Health, SearchHit, SearchResponse, Video,
} from "../lib/types";

type SearchMode = "hybrid" | "lexical" | "semantic";

const MODE_LABEL: Record<SearchMode, string> = {
  hybrid: "混合",
  lexical: "全文",
  semantic: "语义",
};

const EXAMPLES = ["操作系统", "计算机网络", "内存", "database"];

const INSPECTOR_MIN = 320;
const INSPECTOR_MAX = 760;

interface SearchPageProps {
  demo: boolean;
  health: Health | null;
  courses: Course[];
  videos: Video[];
  fixture: Fixture | null;
  query: string;
  onSearch: (query: string) => void;
  courseId: string;
  onCourseId: (courseId: string) => void;
  activeVideo: Video | null;
  onActiveVideo: (video: Video | null) => void;
}

function capLabel(capability: string): string {
  if (capability === "embed_seek") return "B 站内嵌播放（秒级定位）";
  if (capability === "external_seek") return "外链跳转（尽量定位）";
  if (capability === "local_select") return "本地视频精确跳转";
  if (capability === "url_hint") return "链接提示";
  return "无播放能力信息";
}

function bilibiliEmbedUrl(video: Video, startMs: number): string {
  const t = Math.max(0, startMs + (video.offset_ms || 0)) / 1000;
  const page = Math.max(1, video.part_index || 1);
  return (
    `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(video.platform_video_id)}` +
    `&page=${page}&autoplay=0&high_quality=1&danmaku=0&t=${Math.floor(t)}`
  );
}

function highlight(text: string, query: string): ReactNode {
  const terms = Array.from(new Set(query.trim().split(/\s+/).filter((t) => t.length >= 2))).slice(0, 8);
  if (!terms.length) return text;
  const lower = terms.map((term) => term.toLowerCase());
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(${escaped.join("|")})`, "gi");
  return text.split(re).map((part, index) =>
    lower.includes(part.toLowerCase())
      ? <mark className="hit-mark" key={index}>{part}</mark>
      : <span key={index}>{part}</span>,
  );
}

export default function SearchPage(props: SearchPageProps) {
  const {
    demo, health, courses, videos, fixture, query, onSearch,
    courseId, onCourseId, activeVideo, onActiveVideo,
  } = props;
  const [draft, setDraft] = useState(query);
  const [mode, setMode] = useState<SearchMode>("hybrid");
  const [resp, setResp] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<SearchHit | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [cuesLoading, setCuesLoading] = useState(false);
  const [cueFilter, setCueFilter] = useState("");
  const [cueFocus, setCueFocus] = useState<number | null>(null);
  const [localUrl, setLocalUrl] = useState<string | null>(null);
  const [embedSeek, setEmbedSeek] = useState<{ videoId: string; ms: number } | null>(null);
  const [inspectorW, setInspectorW] = useState(() => {
    const saved = Number(window.localStorage.getItem("tj-inspector-w"));
    return saved >= INSPECTOR_MIN && saved <= INSPECTOR_MAX ? saved : 380;
  });
  const [inspectorDrag, setInspectorDrag] = useState(false);
  const [playhead, setPlayhead] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  useEffect(() => setDraft(query), [query]);

  useEffect(() => {
    if (!query.trim()) {
      setResp(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const run = async () => {
      try {
        if (demo) {
          if (!fixture) throw new Error("Demo 数据尚未加载");
          const hits = demoSearch(fixture, query, 10, courseId || undefined);
          if (cancelled) return;
          setResp({
            query,
            mode: "demo-keyword",
            rrf_k: 60,
            candidate_counts: { lexical: hits.length, semantic: 0 },
            hits,
            warnings: [fixture.notice],
          });
        } else {
          const result = await api.search({
            q: query,
            mode,
            limit: 10,
            course_id: courseId || undefined,
          });
          if (!cancelled) setResp(result);
        }
        if (!cancelled) {
          setSelected(null);
          setCueFocus(null);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(errorText(exc));
          setResp(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [query, mode, courseId, demo, fixture, videos]);

  useEffect(() => {
    if (!activeVideo) {
      setCues([]);
      return;
    }
    let cancelled = false;
    setCuesLoading(true);
    setPlayhead(0);
    const run = async () => {
      try {
        if (demo) {
          if (fixture) setCues(demoCues(fixture, activeVideo.id));
        } else {
          const result = await api.cues(activeVideo.id);
          if (!cancelled) setCues(result.cues);
        }
      } catch {
        if (!cancelled) setCues([]);
      } finally {
        if (!cancelled) setCuesLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [activeVideo, demo, fixture]);

  useEffect(() => {
    if (!localUrl) return;
    return () => URL.revokeObjectURL(localUrl);
  }, [localUrl]);

  useEffect(() => {
    const element = videoRef.current;
    if (!localUrl || !selected || !element) return;
    const target = Math.max(0, selected.start_ms + (activeVideo?.offset_ms ?? 0)) / 1000;
    const apply = () => {
      try {
        element.currentTime = target;
        setPlayhead(target * 1000);
      } catch {
        /* metadata not ready yet */
      }
    };
    if (element.readyState >= 1) apply();
    else element.addEventListener("loadedmetadata", apply, { once: true });
    return () => element.removeEventListener("loadedmetadata", apply);
  }, [localUrl, selected, activeVideo]);

  const focusSeq = cueFocus;

  useEffect(() => {
    if (focusSeq == null || !transcriptRef.current) return;
    const node = transcriptRef.current.querySelector<HTMLElement>(`[data-seq="${focusSeq}"]`);
    node?.scrollIntoView({ block: "center" });
  }, [focusSeq, cues]);

  const playheadSeq = useMemo(() => {
    let seq: number | null = null;
    for (const cue of cues) {
      if (cue.start_ms <= playhead) seq = cue.seq;
      else break;
    }
    return seq;
  }, [cues, playhead]);

  const filteredCues = useMemo(() => {
    const needle = cueFilter.trim();
    return needle ? cues.filter((cue) => cue.text.includes(needle)) : cues;
  }, [cues, cueFilter]);

  const hits = resp?.hits ?? [];
  const selectedCueSeq = localUrl && playhead > 0 ? playheadSeq : focusSeq;
  const externalUrl = selected?.jump_url || activeVideo?.source_url || "";
  const embeddable =
    activeVideo != null &&
    activeVideo.platform === "bilibili" &&
    !!activeVideo.platform_video_id;
  const embedMs =
    embedSeek && activeVideo && embedSeek.videoId === activeVideo.id ? embedSeek.ms : 0;
  const embedSrc = activeVideo ? bilibiliEmbedUrl(activeVideo, embedMs) : "";

  function chooseHit(hit: SearchHit) {
    setSelected(hit);
    setCueFocus(hit.cue_start_seq);
    setEmbedSeek({ videoId: hit.video_id, ms: hit.start_ms });
    onActiveVideo(videos.find((video) => video.id === hit.video_id) ?? null);
  }

  function chooseCue(cue: Cue) {
    setCueFocus(cue.seq);
    if (embeddable && activeVideo) {
      setEmbedSeek({ videoId: activeVideo.id, ms: cue.start_ms });
    }
    const element = videoRef.current;
    if (localUrl && element) {
      element.currentTime = Math.max(0, cue.start_ms + (activeVideo?.offset_ms ?? 0)) / 1000;
      void element.play().catch(() => undefined);
    }
  }

  function pickLocalFile(file: File | undefined) {
    if (!file) return;
    setLocalUrl(URL.createObjectURL(file));
  }

  function startInspectorDrag(event: React.PointerEvent) {
    event.preventDefault();
    setInspectorDrag(true);
    const startX = event.clientX;
    const startW = inspectorW;
    let latest = inspectorW;
    const move = (ev: PointerEvent) => {
      latest = Math.min(INSPECTOR_MAX, Math.max(INSPECTOR_MIN, startW - (ev.clientX - startX)));
      setInspectorW(latest);
    };
    const up = () => {
      setInspectorDrag(false);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.localStorage.setItem("tj-inspector-w", String(latest));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  function resetInspectorWidth() {
    setInspectorW(380);
    window.localStorage.setItem("tj-inspector-w", "380");
  }

  const intro = !query.trim();

  return (
    <div
      className={`workspace${activeVideo ? " has-inspector" : " no-inspector"}`}
      style={activeVideo ? ({ "--tj-inspector-w": `${inspectorW}px` } as React.CSSProperties) : undefined}
    >
      <section className="panel main-panel">
        {intro ? (
          <div className="search-hero">
            <h1>把课程视频变成可检索的片段</h1>
            <p>
              输入自然语言问题，按 seekdb 全文 + 向量双路召回，结果带原文、时间戳与命中依据。
              {health && ` 当前库内 ${health.video_count} 讲 / ${health.passage_count} 个片段。`}
            </p>
            <form
              className="search-box"
              onSubmit={(event) => {
                event.preventDefault();
                onSearch(draft);
              }}
            >
              <Search size={18} color="var(--vm-muted)" />
              <input
                autoFocus
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="例如：操作系统为什么要管理硬件资源？"
                aria-label="搜索课程字幕"
              />
              <button className="btn solid" type="submit">检索</button>
            </form>
            <div className="chips" style={{ marginTop: 12 }}>
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  className="chip"
                  onClick={() => {
                    setDraft(example);
                    onSearch(example);
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
            {health && (
              <div className="stats-row" style={{ marginTop: 18, marginBottom: 0 }}>
                <div className="stat"><div className="n">{health.course_count}</div><div className="l">课程</div></div>
                <div className="stat"><div className="n">{health.video_count}</div><div className="l">讲次</div></div>
                <div className="stat"><div className="n">{health.cue_count}</div><div className="l">原始字幕行</div></div>
                <div className="stat"><div className="n">{health.passage_count}</div><div className="l">可检索片段</div></div>
              </div>
            )}
          </div>
        ) : (
          <>
            <div className="result-toolbar">
              <div>
                <div className="section-title" style={{ margin: 0 }}>检索结果</div>
                <div className="result-count">
                  “{query}” · {loading ? "检索中" : `${hits.length} 条`}
                  {resp && !demo && ` · 全文候选 ${resp.candidate_counts.lexical} / 语义候选 ${resp.candidate_counts.semantic} · RRF k=${resp.rrf_k}`}
                </div>
              </div>
              <div className="topbar-spacer" />
              {demo ? (
                <span className="badge warn">Demo 关键词过滤</span>
              ) : (
                <div className="seg" role="group" aria-label="检索模式">
                  {(Object.keys(MODE_LABEL) as SearchMode[]).map((key) => (
                    <button
                      key={key}
                      className={mode === key ? "active" : ""}
                      onClick={() => setMode(key)}
                      disabled={key !== "lexical" && health != null && !health.capabilities.vector_search}
                      title={key !== "lexical" && health != null && !health.capabilities.vector_search ? "向量能力不可用，退回全文检索" : MODE_LABEL[key]}
                    >
                      {MODE_LABEL[key]}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {!demo && resp?.warnings.map((warning) => (
              <div className="notice" key={warning}>{warning}</div>
            ))}
            {error && <div className="notice error">{error}</div>}
            {loading && (
              <div className="empty">
                <Loader2 className="spin" size={20} style={{ marginBottom: 6 }} />
                <strong>正在检索</strong>
                <span className="small">全文与向量两路召回后做 RRF 融合</span>
              </div>
            )}
            {!loading && !error && hits.length === 0 && (
              <div className="empty">
                <strong>没有找到相关片段</strong>
                <span className="small">
                  {demo
                    ? "Demo 只做浏览器关键词过滤，可换个更短的关键词。"
                    : "可以去掉课程过滤、换用更短的关键词，或切换检索模式。"}
                </span>
              </div>
            )}
            <div className="results">
              {!loading && hits.map((hit) => (
                <article
                  key={hit.passage_id}
                  className={`result-card${selected?.passage_id === hit.passage_id ? " selected" : ""}`}
                  onClick={() => chooseHit(hit)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      chooseHit(hit);
                    }
                  }}
                >
                  <div className="result-top">
                    <span className="result-title">{hit.video_title}</span>
                    <span className="time-chip">{fmtTime(hit.start_ms)}–{fmtTime(hit.end_ms)}</span>
                    <span className="course-chip">{hit.course_name}</span>
                  </div>
                  <p className="result-text">
                    {highlight(hit.text.length > 260 ? `${hit.text.slice(0, 260)}…` : hit.text, query)}
                  </p>
                  <div className="reason-row">
                    {hit.match_reason.split("+").map((reason) => (
                      <span
                        key={reason}
                        className={`reason-chip${reason.includes("semantic") || reason.includes("语义") ? " semantic" : ""}`}
                      >
                        {reason}
                      </span>
                    ))}
                    {hit.lexical_score != null && <span className="reason-chip">lex {Number(hit.lexical_score).toFixed(2)}</span>}
                    {hit.semantic_score != null && <span className="reason-chip semantic">vec {Number(hit.semantic_score).toFixed(3)}</span>}
                  </div>
                  <div className="result-meta">
                    <span>score {Number(hit.score).toFixed(4)}</span>
                    <span>cue {hit.cue_start_seq}–{hit.cue_end_seq}</span>
                    <span>{capLabel(hit.playback_capability)}</span>
                  </div>
                </article>
              ))}
            </div>
          </>
        )}
      </section>

      {activeVideo && (
        <div
          className={`ws-sash${inspectorDrag ? " dragging" : ""}`}
          role="separator"
          aria-orientation="vertical"
          aria-label="拖拽调整播放器与字幕宽度，双击恢复默认"
          title="拖拽调整宽度 · 双击恢复默认"
          onPointerDown={startInspectorDrag}
          onDoubleClick={resetInspectorWidth}
        />
      )}

      {activeVideo && (
        <aside className="inspector" aria-label="播放与字幕">
          <div className="inspector-head">
            <div>
              <div className="inspector-title">{activeVideo.title}</div>
              <div className="page-sub">
                {courses.find((course) => course.id === activeVideo.course_id)?.name ?? activeVideo.course_id}
                {activeVideo.offset_ms ? ` · offset ${activeVideo.offset_ms} ms` : ""}
              </div>
            </div>
            <button
              className="btn ghost sm"
              aria-label="关闭检查器"
              onClick={() => {
                onActiveVideo(null);
                setSelected(null);
                setCueFocus(null);
              }}
            >
              <X size={15} />
            </button>
          </div>

          {embeddable && !localUrl ? (
            <div>
              <div className="player-wrap">
                <iframe
                  key={`${activeVideo.id}:${Math.floor(embedMs / 1000)}`}
                  src={embedSrc}
                  title="Bilibili 嵌入播放器"
                  allowFullScreen
                  scrolling="no"
                />
              </div>
              <div className="result-meta" style={{ marginTop: 6 }}>
                <span>B 站内嵌播放{embedMs > 0 ? ` · 已定位 ${fmtTime(embedMs)}` : ""}</span>
                {externalUrl && (
                  <a href={externalUrl} target="_blank" rel="noreferrer">打开原视频</a>
                )}
                <button className="btn ghost sm" onClick={() => fileRef.current?.click()}>
                  <Upload size={14} /> 本地文件毫秒级对齐
                </button>
              </div>
            </div>
          ) : localUrl ? (
            <div>
              <div className="player-wrap">
                <video
                  ref={videoRef}
                  src={localUrl}
                  controls
                  onTimeUpdate={(event) => setPlayhead(event.currentTarget.currentTime * 1000)}
                />
              </div>
              <div className="result-meta" style={{ marginTop: 6 }}>
                <span>本地临时播放 · 不上传</span>
                <button className="btn ghost sm" onClick={() => fileRef.current?.click()}>换一个文件</button>
              </div>
            </div>
          ) : (
            <div className="player-fallback">
              <Play size={20} style={{ marginBottom: 6 }} />
              <p>
                {activeVideo.source_url
                  ? "当前讲次有外部来源，浏览器内可打开原视频；若需精确按时间戳定位，可选取本地视频文件。"
                  : "当前讲次没有源视频文件。选取本地视频后，点击结果或字幕即可按毫秒跳转。"}
              </p>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", flexWrap: "wrap" }}>
                <button className="btn sm primary" onClick={() => fileRef.current?.click()}>
                  <Upload size={14} /> 选择本地视频
                </button>
                {externalUrl && (
                  <a className="btn sm" href={externalUrl} target="_blank" rel="noreferrer">
                    <ArrowUpRight size={14} /> 打开原视频
                  </a>
                )}
              </div>
            </div>
          )}
          <input
            ref={fileRef}
            type="file"
            accept="video/*"
            hidden
            onChange={(event) => pickLocalFile(event.target.files?.[0])}
          />

          {selected && (
            <div className="notice" style={{ marginTop: 10 }}>
              <div>
                命中片段 {fmtTime(selected.start_ms)}–{fmtTime(selected.end_ms)} · {capLabel(selected.playback_capability)}
              </div>
              <div className="small">
                {selected.playback_capability === "embed_seek"
                  ? "点击结果或字幕行时，右侧内嵌播放器会按字幕时间戳重新定位（秒级）。"
                  : selected.playback_capability === "external_seek"
                    ? "外部平台只能通过链接打开并尽量定位，iframe 内不保证精确 seek。"
                    : "选择本地视频后，将按字幕时间戳精确跳转。"}
              </div>
              {selected.jump_url && (
                <a href={selected.jump_url} target="_blank" rel="noreferrer">
                  跳转原视频 {fmtTime(selected.start_ms)}
                </a>
              )}
            </div>
          )}

          <div className="inspector-head" style={{ marginTop: 12 }}>
            <span className="inspector-title">字幕 · {cues.length} 句</span>
            <input
              value={cueFilter}
              onChange={(event) => setCueFilter(event.target.value)}
              placeholder="句内筛选"
              aria-label="字幕内筛选"
              style={{
                width: 110, height: 28, border: "1px solid var(--vm-border)",
                borderRadius: 7, padding: "0 8px", fontSize: 11, outline: "none",
              }}
            />
          </div>
          {cuesLoading && <div className="small muted">加载字幕…</div>}
          <div className="transcript" ref={transcriptRef}>
            {filteredCues.map((cue) => (
              <div
                key={cue.seq}
                data-seq={cue.seq}
                className={`cue-row${selectedCueSeq === cue.seq ? " active" : ""}`}
                onClick={() => chooseCue(cue)}
                role="button"
                tabIndex={0}
                onKeyDown={(event) => {
                  if (event.key === "Enter") chooseCue(cue);
                }}
              >
                <span className="cue-time">{fmtTime(cue.start_ms)}</span>
                <span>{cue.text}</span>
              </div>
            ))}
            {!cuesLoading && filteredCues.length === 0 && (
              <div className="small muted" style={{ padding: 8 }}>
                {cues.length === 0 ? "没有字幕" : "没有匹配的字幕行"}
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

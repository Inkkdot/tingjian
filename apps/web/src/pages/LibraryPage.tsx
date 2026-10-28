import { useEffect, useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";
import { api, errorText, fmtTime } from "../lib/api";
import { demoCues } from "../lib/demo";
import type { Course, Cue, Fixture, Video } from "../lib/types";

interface LibraryPageProps {
  demo: boolean;
  courses: Course[];
  videos: Video[];
  fixture: Fixture | null;
  libCourseId: string;
  onLibCourseId: (courseId: string) => void;
}

const COVER_PALETTES: Array<[string, string]> = [
  ["#8a4b23", "#d2682f"],
  ["#5c4426", "#a5762f"],
  ["#2f5d52", "#6f9c84"],
  ["#4a3d6b", "#8a7ab0"],
  ["#7a3b2e", "#c47a52"],
  ["#3b556e", "#7f9cba"],
  ["#6b4a2a", "#b08a4f"],
  ["#41584a", "#7d9c72"],
];

function paletteFor(seed: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) | 0;
  return COVER_PALETTES[Math.abs(hash) % COVER_PALETTES.length];
}

function Cover(props: {
  seed: string;
  title: string;
  coverUrl?: string;
  durationMs?: number;
  badge?: string;
  progress?: number;
  children?: React.ReactNode;
}) {
  const [from, to] = paletteFor(props.seed);
  return (
    <div className="cover">
      <div className="cover-art" style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}>
        {props.coverUrl ? (
          <img
            src={props.coverUrl}
            alt=""
            loading="lazy"
            onError={(event) => {
              event.currentTarget.remove();
            }}
          />
        ) : null}
        <span className="cover-mark">听见</span>
      </div>
      <span className="cover-title">{props.title}</span>
      {props.badge ? <span className="cover-badge">{props.badge}</span> : null}
      {props.durationMs ? (
        <span className="cover-dur">{fmtTime(props.durationMs)}</span>
      ) : null}
      {props.progress != null && props.progress > 0 ? (
        <i className="card-progress" style={{ width: `${Math.min(100, props.progress)}%` }} />
      ) : null}
      {props.children}
    </div>
  );
}

export default function LibraryPage({
  demo, courses, videos, fixture, libCourseId, onLibCourseId,
}: LibraryPageProps) {
  const [selected, setSelected] = useState<Video | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selected) {
      setCues([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    const run = async () => {
      try {
        if (demo) {
          if (fixture) setCues(demoCues(fixture, selected.id));
        } else {
          const result = await api.cues(selected.id);
          if (!cancelled) setCues(result.cues);
        }
      } catch (exc) {
        if (!cancelled) setError(errorText(exc));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [selected, demo, fixture]);

  const shown = libCourseId
    ? videos.filter((video) => video.course_id === libCourseId)
    : videos;
  const totalCues = shown.reduce((sum, video) => sum + (video.cue_count ?? 0), 0);
  const totalPassages = shown.reduce((sum, video) => sum + (video.passage_count ?? 0), 0);
  const embedded = shown.reduce((sum, video) => sum + (video.embedded_count ?? 0), 0);

  return (
    <div>
      <div className="stats-row">
        <div className="stat"><div className="n">{courses.length}</div><div className="l">课程</div></div>
        <div className="stat"><div className="n">{shown.length}</div><div className="l">讲次</div></div>
        <div className="stat"><div className="n">{totalCues}</div><div className="l">原始字幕行</div></div>
        <div className="stat"><div className="n">{embedded}/{totalPassages}</div><div className="l">已生成向量片段</div></div>
      </div>

      <div className="section-title" style={{ marginTop: 0 }}>课程</div>
      {courses.length > 0 ? (
        <div className="card-grid">
          {courses.map((course) => {
            const coverSource = videos.find(
              (video) => video.course_id === course.id && video.cover_url,
            );
            return (
            <button
              key={course.id}
              className={`course-stack${libCourseId === course.id ? " active" : ""}`}
              onClick={() => onLibCourseId(libCourseId === course.id ? "" : course.id)}
              title={`${course.name} ${course.term} · 点击筛选讲次`}
            >
              <span className="stack-layer layer-3" aria-hidden="true" />
              <span className="stack-layer layer-2" aria-hidden="true" />
              <div className="stack-front">
                <Cover
                  seed={course.id}
                  title={course.name}
                  coverUrl={coverSource?.cover_url}
                  badge={`${course.video_count} 讲`}
                />
              </div>
              <span className="stack-title">{course.name}</span>
              <span className="stack-meta">
                {course.term || "—"} · {course.cue_count} 句 · {course.passage_count} 片段
              </span>
            </button>
            );
          })}
        </div>
      ) : (
        <div className="empty">
          <strong>还没有课程</strong>
          <span className="small">去「导入」添加第一份字幕。</span>
        </div>
      )}

      <div className="section-title">
        讲次
        {libCourseId && (
          <button
            className="btn ghost sm"
            style={{ marginLeft: 10, verticalAlign: 2 }}
            onClick={() => onLibCourseId("")}
          >
            显示全部课程
          </button>
        )}
      </div>
      {shown.length > 0 ? (
        <div className="card-grid">
          {shown.map((video) => {
            const progress = video.passage_count
              ? (video.embedded_count / video.passage_count) * 100
              : 0;
            return (
              <button
                key={video.id}
                className="lecture-card"
                onClick={() => setSelected(selected?.id === video.id ? null : video)}
                title={video.title}
              >
                <Cover
                  seed={video.id}
                  title={video.title}
                  coverUrl={video.cover_url}
                  durationMs={video.duration_ms}
                  progress={progress}
                />
                <span className="card-title">{video.title}</span>
                <span className="card-meta">
                  {video.cue_count} 句 · {video.passage_count} 片段
                  {video.embedded_count > 0 ? " · 已向量化" : ""}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="empty">
          <strong>还没有讲次</strong>
          <span className="small">导入后这里会出现封面卡。</span>
        </div>
      )}

      {selected && (
        <div className="card" style={{ marginTop: 20 }}>
          <div className="inspector-head">
            <div>
              <div className="section-title" style={{ margin: 0 }}>{selected.title}</div>
              <div className="page-sub">
                {selected.cue_count} 句 · {selected.passage_count} 片段 · 时长 {fmtTime(selected.duration_ms)}
                {selected.source_url && (
                  <a href={selected.source_url} target="_blank" rel="noreferrer" style={{ marginLeft: 8 }}>
                    <ExternalLink size={12} style={{ verticalAlign: -1 }} /> 原视频
                  </a>
                )}
              </div>
            </div>
            <button className="btn ghost sm" onClick={() => setSelected(null)}>关闭</button>
          </div>
          <dl className="kv" style={{ marginBottom: 12 }}>
            <dt>视频 ID</dt><dd className="mono">{selected.id}</dd>
            <dt>来源类型</dt><dd>{selected.source_type}</dd>
            <dt>平台</dt><dd>{selected.platform} {selected.platform_video_id}</dd>
            <dt>时间偏移</dt><dd>{selected.offset_ms} ms</dd>
            <dt>来源 URL</dt><dd>{selected.source_url || "（本地字幕，无源视频）"}</dd>
          </dl>
          {loading && <div className="small muted"><Loader2 className="spin" size={14} /> 加载字幕…</div>}
          {error && <div className="notice error">{error}</div>}
          {!loading && !error && (
            <div className="transcript" style={{ maxHeight: 320 }}>
              {cues.slice(0, 80).map((cue) => (
                <div className="cue-row" key={cue.seq} style={{ cursor: "default" }}>
                  <span className="cue-time">{fmtTime(cue.start_ms)}</span>
                  <span>{cue.text}</span>
                </div>
              ))}
              {cues.length > 80 && <div className="small muted" style={{ padding: 8 }}>仅显示前 80 句，共 {cues.length} 句。</div>}
              {cues.length === 0 && <div className="small muted" style={{ padding: 8 }}>没有字幕。</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

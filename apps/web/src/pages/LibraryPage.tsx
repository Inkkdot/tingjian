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
}

export default function LibraryPage({ demo, courses, videos, fixture }: LibraryPageProps) {
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

  const totalCues = videos.reduce((sum, video) => sum + (video.cue_count ?? 0), 0);
  const totalPassages = videos.reduce((sum, video) => sum + (video.passage_count ?? 0), 0);
  const embedded = videos.reduce((sum, video) => sum + (video.embedded_count ?? 0), 0);

  return (
    <div>
      <div className="stats-row">
        <div className="stat"><div className="n">{courses.length}</div><div className="l">课程</div></div>
        <div className="stat"><div className="n">{videos.length}</div><div className="l">讲次</div></div>
        <div className="stat"><div className="n">{totalCues}</div><div className="l">原始字幕行</div></div>
        <div className="stat"><div className="n">{embedded}/{totalPassages}</div><div className="l">已生成向量片段</div></div>
      </div>

      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>课程</div>
        <table className="table">
          <thead>
            <tr><th>课程</th><th>学期</th><th>讲次</th><th>字幕行</th><th>片段</th></tr>
          </thead>
          <tbody>
            {courses.map((course) => (
              <tr key={course.id}>
                <td><strong>{course.name}</strong><div className="small muted mono">{course.id}</div></td>
                <td>{course.term || "—"}</td>
                <td>{course.video_count}</td>
                <td>{course.cue_count}</td>
                <td>{course.passage_count}</td>
              </tr>
            ))}
            {courses.length === 0 && (
              <tr><td colSpan={5} className="muted">还没有课程，去「导入」添加第一份字幕。</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="section-title" style={{ marginTop: 0 }}>讲次</div>
        <table className="table">
          <thead>
            <tr><th>讲次</th><th>课程</th><th>字幕</th><th>片段</th><th>向量</th><th>来源</th></tr>
          </thead>
          <tbody>
            {videos.map((video) => (
              <tr
                key={video.id}
                onClick={() => setSelected(video)}
                style={{ cursor: "pointer" }}
              >
                <td><strong>{video.title}</strong><div className="small muted mono">{video.id}</div></td>
                <td>{courses.find((course) => course.id === video.course_id)?.name ?? video.course_id}</td>
                <td>
                  <span className="badge ok">{video.cue_count ?? 0} 句</span>
                  <div className="small muted">{video.subtitle_kind}</div>
                </td>
                <td>{video.passage_count ?? 0}</td>
                <td>{video.embedded_count > 0 ? <span className="badge ok">{video.embedded_count}</span> : <span className="badge warn">未生成</span>}</td>
                <td className="small">
                  {video.platform}
                  {video.source_url && (
                    <a href={video.source_url} target="_blank" rel="noreferrer" style={{ marginLeft: 6 }}>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </td>
              </tr>
            ))}
            {videos.length === 0 && (
              <tr><td colSpan={6} className="muted">还没有讲次。</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="card" style={{ marginTop: 14 }}>
          <div className="inspector-head">
            <div>
              <div className="section-title" style={{ margin: 0 }}>{selected.title}</div>
              <div className="page-sub">
                {selected.cue_count} 句 · {selected.passage_count} 片段 · 时长 {fmtTime(selected.duration_ms)}
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

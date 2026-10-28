import { fmtTime } from "../lib/api";
import type { Course, Video } from "../lib/types";

interface LibraryPageProps {
  courses: Course[];
  videos: Video[];
  libCourseId: string;
  onLibCourseId: (courseId: string) => void;
  onOpenVideo: (video: Video) => void;
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
  courses, videos, libCourseId, onLibCourseId, onOpenVideo,
}: LibraryPageProps) {
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
                onClick={() => onOpenVideo(video)}
                title={`${video.title} · 点击进入搜索页播放`}
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
    </div>
  );
}

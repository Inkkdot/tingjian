import type { Course, Cue, Passage, Video } from "./types";

export interface DemoLesson {
  video: Video;
  course: Course;
  cues: Cue[];
  passages: Passage[];
}

export interface DemoLessonInput {
  courseId: string;
  courseName: string;
  term: string;
  title: string;
  sourceUrl: string;
  offsetMs: number;
  cues: Cue[];
}

export interface DemoLessonSummary {
  video: Video;
  course: Course;
  cueCount: number;
  passageCount: number;
  sourceHash: string;
}

let lessons: DemoLesson[] = [];

const TIME_RE = /^(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})/;

function toMs(part: string): number | null {
  const match = TIME_RE.exec(part.trim());
  if (!match) return null;
  const hours = Number(match[1] ?? 0);
  const minutes = Number(match[2]);
  const seconds = Number(match[3]);
  const millis = Number(match[4].padEnd(3, "0"));
  return hours * 3_600_000 + minutes * 60_000 + seconds * 1000 + millis;
}

function cleanText(lines: string[]): string {
  return lines
    .join(" ")
    .replace(/<[^>]+>/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function parseSubtitleText(content: string): Cue[] {
  const source = content.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").trim();
  if (!source) throw new Error("字幕文件是空的");
  const blocks = source.split(/\n{2,}/);
  const cues: Cue[] = [];
  for (const block of blocks) {
    const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
    if (!lines.length) continue;
    if (/^(NOTE|STYLE|REGION)\b/i.test(lines[0])) continue;
    let arrow = lines.findIndex((line) => line.includes("-->"));
    if (arrow < 0) continue;
    const [left, right] = lines[arrow].split("-->");
    const start = toMs(left ?? "");
    const end = toMs(right ?? "");
    const text = cleanText(lines.slice(arrow + 1));
    if (start == null || end == null || end <= start || !text) continue;
    cues.push({ seq: 0, start_ms: start, end_ms: end, text });
  }
  if (!cues.length) throw new Error("字幕文件不含任何有效 cue（需要 SRT/VTT 时间轴）");
  cues.sort((a, b) => a.start_ms - b.start_ms || a.end_ms - b.end_ms);
  cues.forEach((cue, index) => {
    cue.seq = index + 1;
  });
  return cues;
}

function chunkCues(cues: Cue[]): Passage[] {
  const drafts: Passage[] = [];
  const total = cues.length;
  let i = 0;
  while (i < total) {
    const start = cues[i];
    let j = i;
    let chars = 0;
    while (j < total) {
      const cue = cues[j];
      const nextChars = chars + cue.text.length;
      const duration = cue.end_ms - start.start_ms;
      if (j > i && (duration > 45_000 || nextChars > 260)) break;
      chars = nextChars;
      j += 1;
    }
    const window = cues.slice(i, j);
    drafts.push({
      id: "",
      start_ms: window[0].start_ms,
      end_ms: window[window.length - 1].end_ms,
      text: window.map((cue) => cue.text).join(""),
      cue_start_seq: window[0].seq,
      cue_end_seq: window[window.length - 1].seq,
    });
    if (j >= total) break;
    i += Math.max(1, j - i - 1);
  }
  return drafts;
}

function shortHash(text: string): string {
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < text.length; i += 1) {
    const code = text.charCodeAt(i);
    h1 ^= code;
    h1 = Math.imul(h1, 0x01000193);
    h2 = Math.imul(h2 ^ code, 0x85ebca6b);
  }
  return ((h1 >>> 0).toString(16) + (h2 >>> 0).toString(16)).padStart(16, "0").slice(0, 16);
}

function readVideoId(url: string): string {
  return url.match(/BV[0-9A-Za-z]{10}/)?.[0] ?? "";
}

function readPart(url: string): number {
  const match = url.match(/[?&]p=(\d+)/);
  return match ? Math.max(1, Number(match[1])) : 1;
}

export function addDemoLesson(input: DemoLessonInput): DemoLessonSummary {
  const { cues } = input;
  if (!cues.length) throw new Error("没有可导入的字幕");
  const now = Date.now().toString(36);
  const videoId = `local-${now}`;
  const bvid = readVideoId(input.sourceUrl);
  const platform = bvid ? "bilibili" : input.sourceUrl ? "generic" : "local";
  const passages = chunkCues(cues).map((draft) => ({
    ...draft,
    id: `p-${videoId}-${String(draft.cue_start_seq).padStart(4, "0")}`,
  }));
  const digest = shortHash(`${videoId}:${cues.length}:${cues[0].start_ms}:${input.title}`);
  const video: Video = {
    id: videoId,
    course_id: input.courseId,
    title: input.title,
    source_url: input.sourceUrl,
    source_type: bvid ? "bilibili_subtitle" : "srt_upload",
    platform,
    platform_video_id: bvid || videoId,
    part_index: bvid ? readPart(input.sourceUrl) : 1,
    cover_url: "",
    duration_ms: cues[cues.length - 1].end_ms,
    offset_ms: input.offsetMs,
    subtitle_kind: "uploaded_srt",
    cue_count: cues.length,
    passage_count: passages.length,
    embedded_count: 0,
    cues,
    passages,
  };
  const course: Course = {
    id: input.courseId,
    name: input.courseName,
    term: input.term,
    video_count: 0,
    cue_count: 0,
    passage_count: 0,
  };
  lessons = [...lessons, { video, course, cues, passages }];
  return {
    video,
    course,
    cueCount: cues.length,
    passageCount: passages.length,
    sourceHash: digest,
  };
}

export function localLessons(): DemoLesson[] {
  return lessons;
}

export function localCues(videoId: string): Cue[] | null {
  return lessons.find((lesson) => lesson.video.id === videoId)?.cues ?? null;
}

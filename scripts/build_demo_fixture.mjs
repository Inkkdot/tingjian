// Build the offline demo fixture for the published site from a local bilibili
// demo material directory (manifest.json + subtitles/ + covers/).
// The material is NOT committed to any repository; this script and the built
// output under apps/web/dist-demo are the only artifacts.
//
// Usage:
//   node scripts/build_demo_fixture.mjs --demo <demoDir> --out <distDemoDir>
//
// Replicates apps/api/subtitles.py chunk_passages so demo passages match the
// live seekdb chunking (20-45s windows, <=260 chars).

import { mkdir, readFile, copyFile, writeFile } from "node:fs/promises";
import path from "node:path";

function arg(name) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : undefined;
}

const root = path.resolve(import.meta.dirname, "..");
const demoDir = path.resolve(root, arg("demo") ?? ".tmp-bili-demo/demo");
const outDir = path.resolve(root, arg("out") ?? "apps/web/dist-demo");

const manifest = JSON.parse(await readFile(path.join(demoDir, "manifest.json"), "utf8"));

function chunkPassages(cues) {
  const drafts = [];
  const n = cues.length;
  let i = 0;
  while (i < n) {
    const start = cues[i];
    let j = i;
    let chars = 0;
    while (j < n) {
      const cue = cues[j];
      const nextChars = chars + cue.text.length;
      const duration = cue.end_ms - start.start_ms;
      if (j > i && (duration > 45_000 || nextChars > 260)) break;
      chars = nextChars;
      j += 1;
    }
    const window = cues.slice(i, j);
    drafts.push({
      start_ms: window[0].start_ms,
      end_ms: window[window.length - 1].end_ms,
      text: window.map((cue) => cue.text).join(""),
      cue_start_seq: window[0].seq,
      cue_end_seq: window[window.length - 1].seq,
    });
    i = j;
  }
  return drafts;
}

const videos = [];
for (const lecture of manifest.lectures) {
  const body = JSON.parse(await readFile(path.join(demoDir, lecture.subtitle_json), "utf8"));
  const items = Array.isArray(body) ? body : (body.body ?? []);
  const cues = [];
  for (const item of items) {
    const startMs = Math.round(Number(item.from ?? 0) * 1000);
    const endMs = Math.round(Number(item.to ?? 0) * 1000);
    const text = String(item.content ?? "").trim();
    if (!text || endMs <= startMs) continue;
    cues.push({ seq: cues.length + 1, start_ms: startMs, end_ms: endMs, text });
  }
  cues.sort((a, b) => a.start_ms - b.start_ms);
  cues.forEach((cue, index) => {
    cue.seq = index + 1;
  });
  const passages = chunkPassages(cues).map((draft, index) => ({
    id: `p-${lecture.id}-${draft.cue_start_seq.toString().padStart(4, "0")}`,
    ...draft,
  }));
  videos.push({
    id: lecture.id,
    course_id: lecture.course_id,
    title: lecture.title,
    source_url: lecture.source_url,
    source_type: lecture.source_type,
    platform: lecture.platform,
    platform_video_id: lecture.platform_video_id,
    part_index: lecture.part_index,
    cover_url: `./covers/${path.basename(lecture.cover)}`,
    duration_ms: lecture.duration_ms,
    offset_ms: 0,
    subtitle_kind: lecture.subtitle_kind,
    cue_count: cues.length,
    passage_count: passages.length,
    embedded_count: 0,
    cues,
    passages,
  });
}

const courses = Object.entries(manifest.courses).map(([id, meta]) => {
  const own = videos.filter((video) => video.course_id === id);
  return {
    id,
    name: meta.name,
    term: meta.term,
    video_count: own.length,
    cue_count: own.reduce((sum, video) => sum + video.cue_count, 0),
    passage_count: own.reduce((sum, video) => sum + video.passage_count, 0),
  };
});

const fixture = {
  generated_at: new Date().toISOString().slice(0, 19) + "Z",
  source: "bilibili demo material (local, not redistributed)",
  mode: "demo",
  notice:
    "Demo 模式：浏览器内关键词过滤 + B 站官方嵌入播放器（player.bilibili.com）。" +
    "封面与字幕仅用于演示，版权归原视频作者及 Bilibili，不随仓库分发。",
  counts: {
    courses: courses.length,
    videos: videos.length,
    cues: videos.reduce((sum, video) => sum + video.cue_count, 0),
    passages: videos.reduce((sum, video) => sum + video.passage_count, 0),
  },
  courses,
  videos,
};

await mkdir(path.join(outDir, "covers"), { recursive: true });
await writeFile(path.join(outDir, "fixture.json"), JSON.stringify(fixture), "utf8");
for (const lecture of manifest.lectures) {
  await copyFile(
    path.join(demoDir, lecture.cover),
    path.join(outDir, "covers", path.basename(lecture.cover)),
  );
}
console.log(
  `fixture: ${courses.length} courses / ${videos.length} videos / ` +
    `${fixture.counts.cues} cues / ${fixture.counts.passages} passages -> ${path.relative(root, outDir)}`,
);

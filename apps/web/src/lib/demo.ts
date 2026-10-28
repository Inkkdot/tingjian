import type { Course, Cue, Fixture, Health, SearchHit, Video } from "./types";

let cache: Fixture | null = null;

export async function loadFixture(): Promise<Fixture> {
  if (cache) return cache;
  const resp = await fetch(`${import.meta.env.BASE_URL}fixture.json`);
  if (!resp.ok) throw new Error("Demo fixture 加载失败");
  cache = (await resp.json()) as Fixture;
  return cache;
}

export function demoHealth(fixture: Fixture): Health {
  const counts = fixture.counts ?? {};
  return {
    mode: "demo",
    store_ok: true,
    database: "静态导出样本（非 seekdb 连接）",
    database_version: "live 导出快照",
    schema_version: "1",
    embedding_model: null,
    embedding_error: null,
    course_count: counts.courses ?? fixture.courses.length,
    video_count: counts.videos ?? fixture.videos.length,
    cue_count: counts.cues ?? 0,
    passage_count: counts.passages ?? 0,
    embedded_passage_count: 0,
    error: null,
    capabilities: {
      lexical_search: false,
      vector_search: false,
      hybrid_search: false,
      bilibili_import: false,
      bilibili_login: false,
      bilibili_browser_fallback: false,
      review_playlist: false,
      asr: false,
      llm_summary: false,
    },
  };
}

export function demoCourses(fixture: Fixture): Course[] {
  return fixture.courses;
}

export function demoVideos(fixture: Fixture): Video[] {
  return fixture.videos.map((video) => ({
    ...video,
    cue_count: video.cue_count ?? video.cues?.length ?? 0,
    passage_count: video.passage_count ?? video.passages?.length ?? 0,
    embedded_count: 0,
  }));
}

export function demoCues(fixture: Fixture, videoId: string): Cue[] {
  return fixture.videos.find((video) => video.id === videoId)?.cues ?? [];
}

function terms(query: string): string[] {
  const latin = query.toLowerCase().match(/[a-z][a-z0-9+.]{1,}/g) ?? [];
  const chinese = query.match(/[\u4e00-\u9fff]{2,}/g) ?? [];
  const grams: string[] = [...latin];
  for (const run of chinese) {
    for (let i = 0; i < run.length - 1; i += 1) grams.push(run.slice(i, i + 2));
  }
  return Array.from(new Set(grams));
}

export function demoSearch(
  fixture: Fixture,
  query: string,
  limit: number,
  courseId?: string,
): SearchHit[] {
  const q = query.trim();
  if (!q) return [];
  const tokens = terms(q);
  if (!tokens.length) return [];
  const needed = Math.max(1, Math.ceil(tokens.length / 2));
  const scored: SearchHit[] = [];
  for (const video of fixture.videos) {
    if (courseId && video.course_id !== courseId) continue;
    const course = fixture.courses.find((c) => c.id === video.course_id);
    for (const passage of video.passages ?? []) {
      const haystack = passage.text.toLowerCase();
      let matched = 0;
      for (const token of tokens) if (haystack.includes(token)) matched += 1;
      if (matched < needed) continue;
      const score = matched / tokens.length;
      scored.push({
        passage_id: passage.id,
        video_id: video.id,
        course_id: video.course_id,
        video_title: video.title,
        course_name: course?.name ?? video.course_id,
        start_ms: passage.start_ms,
        end_ms: passage.end_ms,
        cue_start_seq: passage.cue_start_seq,
        cue_end_seq: passage.cue_end_seq,
        text: passage.text,
        source_url: video.source_url,
        jump_url: video.source_url,
        playback_capability: video.platform === "bilibili" ? "external_seek" : "local_select",
        match_reason: "Demo 关键词过滤（非 seekdb 混合检索）",
        score,
      });
    }
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, limit);
}

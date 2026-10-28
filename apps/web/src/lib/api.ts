import type {
  Course, Cue, Health, PlaylistResponse, SearchHit, SearchResponse, Video,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";
const FORCED_DEMO = import.meta.env.VITE_DEMO === "true";

export function isDemoMode(): boolean {
  const params = new URLSearchParams(window.location.search);
  return FORCED_DEMO || params.get("demo") === "1";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, init);
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const message = body?.message ?? `HTTP ${resp.status}`;
    const error = new Error(message) as Error & { code?: string; status?: number; detail?: unknown };
    error.code = body?.code;
    error.status = resp.status;
    error.detail = body?.detail;
    throw error;
  }
  return body as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  courses: () => request<{ courses: Course[] }>("/api/courses"),
  videos: (courseId?: string) =>
    request<{ videos: Video[] }>(`/api/videos${courseId ? `?course_id=${encodeURIComponent(courseId)}` : ""}`),
  search: (params: { q: string; mode: string; limit?: number; course_id?: string }) => {
    const qs = new URLSearchParams({
      q: params.q,
      mode: params.mode,
      limit: String(params.limit ?? 8),
    });
    if (params.course_id) qs.set("course_id", params.course_id);
    return request<SearchResponse>(`/api/search?${qs.toString()}`);
  },
  cues: (videoId: string) => request<{ video_id: string; cues: Cue[] }>(`/api/videos/${videoId}/cues`),
  previewBilibili: (url: string) =>
    request<Record<string, unknown>>(`/api/bilibili/preview?url=${encodeURIComponent(url)}`),
  importSrt: (form: FormData) =>
    request<Record<string, unknown>>("/api/import/srt", { method: "POST", body: form }),
  importBilibili: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/import/bilibili", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  review: (payload: { topic: string; budget_ms: number; k?: number }) =>
    request<PlaylistResponse>("/api/review/playlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  getPlaylist: (playlistId: string) =>
    request<PlaylistResponse>(`/api/playlists/${encodeURIComponent(playlistId)}`),
};

export function fmtTime(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

export function fmtDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h} 小时 ${m % 60} 分`;
  }
  return m > 0 ? `${m} 分 ${s} 秒` : `${s} 秒`;
}

export function errorText(error: unknown): string {
  if (error instanceof Error) {
    const code = (error as Error & { code?: string }).code;
    return code ? `${code}: ${error.message}` : error.message;
  }
  return String(error);
}

export function hitFromPlaylist(item: {
  passage_id: string; video_id: string; course_id: string; video_title: string;
  course_name: string; text: string; clip_start_ms: number; clip_end_ms: number;
  jump_url?: string; playback_capability?: string;
}): SearchHit {
  return {
    passage_id: item.passage_id,
    video_id: item.video_id,
    course_id: item.course_id,
    video_title: item.video_title,
    course_name: item.course_name,
    start_ms: item.clip_start_ms,
    end_ms: item.clip_end_ms,
    cue_start_seq: 0,
    cue_end_seq: 0,
    text: item.text,
    source_url: "",
    jump_url: item.jump_url ?? "",
    playback_capability: item.playback_capability ?? "",
    match_reason: "复习清单",
    score: 0,
  };
}

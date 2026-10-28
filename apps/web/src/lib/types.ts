export type Mode = "live" | "demo";

export interface Course {
  id: string;
  name: string;
  term: string;
  video_count: number;
  cue_count: number;
  passage_count: number;
}

export interface Video {
  id: string;
  course_id: string;
  title: string;
  source_url: string;
  source_type: string;
  platform: string;
  platform_video_id: string;
  part_index: number;
  duration_ms: number;
  offset_ms: number;
  subtitle_kind: string;
  cue_count: number;
  passage_count: number;
  embedded_count: number;
  cues?: Cue[];
  passages?: Passage[];
}

export interface Cue {
  seq: number;
  start_ms: number;
  end_ms: number;
  text: string;
}

export interface Passage {
  id: string;
  start_ms: number;
  end_ms: number;
  text: string;
  cue_start_seq: number;
  cue_end_seq: number;
}

export interface SearchHit {
  passage_id: string;
  video_id: string;
  course_id: string;
  video_title: string;
  course_name: string;
  start_ms: number;
  end_ms: number;
  cue_start_seq: number;
  cue_end_seq: number;
  text: string;
  source_url: string;
  jump_url: string;
  playback_capability: string;
  match_reason: string;
  score: number;
  rank?: number;
  lexical_score?: number | null;
  semantic_score?: number | null;
}

export interface SearchResponse {
  query: string;
  mode: string;
  rrf_k: number;
  candidate_counts: { lexical: number; semantic: number };
  hits: SearchHit[];
  warnings: string[];
}

export interface Capabilities {
  lexical_search: boolean;
  vector_search: boolean;
  hybrid_search: boolean;
  bilibili_import: boolean;
  bilibili_browser_fallback: boolean;
  review_playlist: boolean;
  asr: boolean;
  llm_summary: boolean;
}

export interface Health {
  mode: string;
  store_ok: boolean;
  database: string;
  database_version: string;
  schema_version: string;
  embedding_model: string | null;
  embedding_error: string | null;
  course_count: number;
  video_count: number;
  cue_count: number;
  passage_count: number;
  embedded_passage_count: number;
  error: string | null;
  capabilities: Capabilities;
}

export interface Fixture {
  generated_at: string;
  source: string;
  mode: string;
  notice: string;
  counts: Record<string, number>;
  courses: Course[];
  videos: Video[];
  eval_summary?: Record<string, { hit_at_3: number; answered: number; no_answer_refused: number; latency_ms_mean: number }>;
}

export interface PlaylistItem {
  passage_id: string;
  rank: number;
  clip_start_ms: number;
  clip_end_ms: number;
  reason: string;
  video_id: string;
  course_id: string;
  video_title: string;
  course_name: string;
  text: string;
  score?: number;
  jump_url?: string;
  playback_capability?: string;
  duration_ms?: number;
}

export interface PlaylistResponse {
  playlist_id: string;
  title: string;
  topic: string;
  budget_ms: number;
  total_duration_ms: number;
  within_budget: boolean;
  course_coverage: number;
  candidate_count: number;
  algorithm: string;
  warnings: string[];
  items: PlaylistItem[];
}

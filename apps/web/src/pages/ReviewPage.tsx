import { useMemo, useState } from "react";
import { ArrowUpRight, ListChecks, Loader2, X } from "lucide-react";
import { api, errorText, fmtDuration, fmtTime } from "../lib/api";
import type { PlaylistResponse } from "../lib/types";

interface ReviewPageProps {
  demo: boolean;
}

const BUDGETS = [10, 15, 30, 45];

export default function ReviewPage({ demo }: ReviewPageProps) {
  const [topic, setTopic] = useState("数据库事务与索引");
  const [budget, setBudget] = useState(15);
  const [result, setResult] = useState<PlaylistResponse | null>(null);
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const remaining = useMemo(
    () => (result ? result.items.filter((item) => !removed.has(item.passage_id)) : []),
    [result, removed],
  );
  const totalMs = useMemo(() => {
    const byVideo = new Map<string, Array<[number, number]>>();
    for (const item of remaining) {
      const ranges = byVideo.get(item.video_id) ?? [];
      ranges.push([item.clip_start_ms, item.clip_end_ms]);
      byVideo.set(item.video_id, ranges);
    }
    let sum = 0;
    for (const ranges of byVideo.values()) {
      ranges.sort((a, b) => a[0] - b[0]);
      let [start, end] = ranges[0];
      for (const [nextStart, nextEnd] of ranges.slice(1)) {
        if (nextStart <= end) {
          end = Math.max(end, nextEnd);
        } else {
          sum += end - start;
          [start, end] = [nextStart, nextEnd];
        }
      }
      sum += end - start;
    }
    return sum;
  }, [remaining]);
  const budgetMs = budget * 60_000;

  async function generate() {
    if (!topic.trim()) {
      setError("请输入复习主题");
      return;
    }
    setLoading(true);
    setError(null);
    setRemoved(new Set());
    try {
      const created = await api.review({ topic: topic.trim(), budget_ms: budgetMs, k: 20 });
      try {
        const saved = await api.getPlaylist(created.playlist_id);
        const jumps = new Map(saved.items.map((item) => [item.passage_id, item]));
        setResult({
          ...created,
          items: created.items.map((item) => ({
            ...item,
            jump_url: jumps.get(item.passage_id)?.jump_url,
            playback_capability: jumps.get(item.passage_id)?.playback_capability,
          })),
        });
      } catch {
        setResult(created);
      }
    } catch (exc) {
      setError(errorText(exc));
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>按预算生成复习清单</div>
        <p className="small muted" style={{ marginTop: -4 }}>
          先检索主题相关片段，再按相关度与覆盖增益贪心选片，合并同视频重叠区间，
          实际播放时长不超过预算。算法为覆盖贪心，不冒充 MMR。
        </p>
        {demo ? (
          <div className="notice">
            Demo 静态站点不连接 seekdb，复习清单需在本地 Live 模式生成。
          </div>
        ) : (
          <>
            <div className="form-grid">
              <div className="field full">
                <label htmlFor="topic">考点 / 主题</label>
                <input
                  id="topic"
                  value={topic}
                  onChange={(event) => setTopic(event.target.value)}
                  placeholder="例如：事务隔离级别与 MVCC"
                  disabled={loading}
                />
              </div>
              <div className="field full">
                <label>时间预算</label>
                <div className="chips">
                  {BUDGETS.map((minute) => (
                    <button
                      key={minute}
                      className={`chip${budget === minute ? " active" : ""}`}
                      onClick={() => setBudget(minute)}
                      disabled={loading}
                    >
                      {minute} 分钟
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div style={{ marginTop: 14 }}>
              <button className="btn primary" onClick={() => void generate()} disabled={loading}>
                {loading ? <Loader2 className="spin" size={15} /> : <ListChecks size={15} />}
                生成并保存清单
              </button>
            </div>
          </>
        )}
        {error && <div className="notice error" style={{ marginTop: 10 }}>{error}</div>}
      </div>

      {result && (
        <div style={{ marginTop: 14 }}>
          <div className="stats-row">
            <div className="stat">
              <div className="n">{fmtDuration(totalMs)}</div>
              <div className="l">当前总时长（移除后）</div>
            </div>
            <div className="stat">
              <div className="n">{Math.round(budgetMs / 60_000)} 分</div>
              <div className="l">预算</div>
            </div>
            <div className="stat">
              <div className="n">{remaining.length}</div>
              <div className="l">片段</div>
            </div>
            <div className="stat">
              <div className="n">{result.course_coverage}</div>
              <div className="l">覆盖课程</div>
            </div>
          </div>
          <div className="card">
            <div className="inspector-head">
              <div>
                <strong>{result.title}</strong>
                <div className="page-sub mono">playlist {result.playlist_id} · 候选 {result.candidate_count} · {result.algorithm}</div>
              </div>
              <span className={`badge ${result.within_budget ? "ok" : "warn"}`}>
                {result.within_budget ? "总时长未超预算" : "超出预算"}
              </span>
            </div>
            <div className="meter" style={{ marginBottom: 12 }}>
              <i style={{ width: `${Math.min(100, (totalMs / budgetMs) * 100)}%` }} />
            </div>
            {result.warnings.map((warning) => <div className="notice" key={warning}>{warning}</div>)}
            {remaining.map((item) => (
              <div className="review-item" key={item.passage_id}>
                <div className="review-rank">{item.rank}</div>
                <div>
                  <div className="t">{item.video_title}</div>
                  <div className="r">
                    <span className="time-chip">{fmtTime(item.clip_start_ms)}–{fmtTime(item.clip_end_ms)}</span>
                    {" "}{item.course_name} · {fmtDuration(item.clip_end_ms - item.clip_start_ms)}
                  </div>
                  <div className="small" style={{ marginTop: 4 }}>{item.text.slice(0, 180)}…</div>
                  <div className="small muted" style={{ marginTop: 3 }}>{item.reason}</div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
                  {item.jump_url ? (
                    <a className="btn sm" href={item.jump_url} target="_blank" rel="noreferrer">
                      <ArrowUpRight size={13} /> 打开
                    </a>
                  ) : (
                    <span className="badge">本地字幕</span>
                  )}
                  <button
                    className="btn ghost sm"
                    onClick={() => {
                      const next = new Set(removed);
                      next.add(item.passage_id);
                      setRemoved(next);
                    }}
                    aria-label="从页面移除"
                  >
                    <X size={13} /> 移除
                  </button>
                </div>
              </div>
            ))}
            {remaining.length === 0 && (
              <div className="empty">
                <strong>清单为空</strong>
                <span className="small">换个主题或增加预算再试。</span>
              </div>
            )}
            <div className="small muted" style={{ marginTop: 10 }}>
              「移除」只影响本页展示；已保存的清单以 seekdb 中的 playlist 为准。总时长按合并后的播放区间计算。
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

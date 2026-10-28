import { useEffect, useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import type { Theme } from "../components/AppShell";
import type { Fixture, Health } from "../lib/types";

interface SettingsPageProps {
  demo: boolean;
  health: Health | null;
  fixture: Fixture | null;
  theme: Theme;
  onThemeChange: (theme: Theme) => void;
}

interface MetricMode {
  answered_queries: number;
  hit_at_3: number;
  no_answer_queries: number;
  no_answer_refused: number;
  latency_ms_mean: number;
  latency_ms_p95: number;
}

interface Metrics {
  corpus: Record<string, number>;
  annotation: Record<string, number | string>;
  modes: Record<string, MetricMode>;
}

const MODE_NAMES: Record<string, string> = {
  lexical: "全文",
  semantic: "语义",
  hybrid: "混合（RRF）",
};

export default function SettingsPage({ demo, health, fixture, theme, onThemeChange }: SettingsPageProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}metrics.json`)
      .then((resp) => (resp.ok ? resp.json() : Promise.reject(new Error(`HTTP ${resp.status}`))))
      .then((data: Metrics) => {
        if (!cancelled) setMetrics(data);
      })
      .catch((error: unknown) => {
        if (!cancelled) setMetricsError(String(error));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const capabilities = health?.capabilities;
  const rows: Array<[string, boolean | undefined, string]> = [
    ["seekdb 全文检索（ik 分词）", capabilities?.lexical_search, "/api/health lexical_search"],
    ["向量检索（bge-small-zh-v1.5）", capabilities?.vector_search, "/api/health vector_search"],
    ["混合检索（RRF k=60）", capabilities?.hybrid_search, "/api/health hybrid_search"],
    ["B 站字幕轨导入", capabilities?.bilibili_import, "meta.bilibili_import_ok"],
    ["B 站登录态（可选）", capabilities?.bilibili_login, "BILIBILI_COOKIE / BILIBILI_COOKIE_FILE"],
    ["浏览器 SRT 兜底导入", capabilities?.bilibili_browser_fallback, "/api/import/srt"],
    ["复习清单（覆盖贪心）", capabilities?.review_playlist, "/api/review/playlist"],
    ["ASR / LLM 摘要", capabilities?.asr, "路线功能，未实现"],
  ];

  return (
    <div>
      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>外观</div>
        <div className="field" style={{ maxWidth: 260 }}>
          <label htmlFor="theme">颜色模式</label>
          <select
            id="theme"
            value={theme}
            onChange={(event) => onThemeChange(event.target.value as Theme)}
          >
            <option value="auto">跟随系统</option>
            <option value="light">浅色</option>
            <option value="dark">深色</option>
          </select>
        </div>
        <div className="small muted" style={{ marginTop: 8 }}>
          图标轨底部的日月按钮可快速切换；布局、字号与层级不随主题变化。
        </div>
      </div>

      <div className="stats-row" style={{ marginTop: 14 }}>
        <div className="stat"><div className="n">{health?.course_count ?? 0}</div><div className="l">课程</div></div>
        <div className="stat"><div className="n">{health?.video_count ?? 0}</div><div className="l">讲次</div></div>
        <div className="stat"><div className="n">{health?.cue_count ?? 0}</div><div className="l">字幕行</div></div>
        <div className="stat"><div className="n">{health?.passage_count ?? 0}</div><div className="l">片段</div></div>
      </div>

      <div className="card">
        <div className="section-title" style={{ marginTop: 0 }}>运行状态</div>
        <dl className="kv">
          <dt>模式</dt><dd>{health?.mode ?? (demo ? "demo" : "live")}</dd>
          <dt>数据库</dt><dd>{health?.database ?? "seekdb"}{health?.database_version ? ` · ${health.database_version}` : ""}</dd>
          <dt>连接</dt><dd>{health?.store_ok ? <span className="badge ok">正常</span> : <span className="badge err">不可用</span>}</dd>
          <dt>Schema</dt><dd className="mono">{health?.schema_version ?? "—"}</dd>
          <dt>Embedding</dt><dd>{health?.embedding_model ?? "未加载"}</dd>
          <dt>向量片段</dt><dd>{health?.embedded_passage_count ?? 0} / {health?.passage_count ?? 0}</dd>
          <dt>导出快照</dt><dd className="mono">{fixture?.generated_at ?? "—"}</dd>
        </dl>
        {health?.error && <div className="notice error">{health.error}</div>}
        {health?.embedding_error && <div className="notice">{health.embedding_error}</div>}
        {demo && (
          <div className="notice">
            当前为 Qoder Sites 静态 Demo：健康数据来自 Live 模式导出的快照，站点本身不连接 seekdb。
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="section-title" style={{ marginTop: 0 }}>能力矩阵</div>
        {demo ? (
          <table className="table">
            <thead><tr><th>能力</th><th>Demo 站点状态</th></tr></thead>
            <tbody>
              <tr><td>seekdb 全文检索（ik 分词）</td><td><span className="badge ok">Live 已验证 · 17/17</span></td></tr>
              <tr><td>向量检索（bge-small-zh-v1.5）</td><td><span className="badge ok">Live 已验证 · 16/17</span></td></tr>
              <tr><td>混合检索（RRF k=60）</td><td><span className="badge ok">Live 已验证 · 17/17</span></td></tr>
              <tr><td>B 站公开字幕轨</td><td><span className="badge warn">本环境需登录，改用 SRT 兜底</span></td></tr>
              <tr><td>SRT 导入 / 复习清单</td><td><span className="badge warn">Live 可用；Demo 静态站不写库</span></td></tr>
              <tr><td>ASR / LLM 摘要</td><td><span className="badge err">路线功能，未实现</span></td></tr>
            </tbody>
          </table>
        ) : (
          <table className="table">
            <thead><tr><th>能力</th><th>状态</th><th>核对位置</th></tr></thead>
            <tbody>
              {rows.map(([label, value, where]) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td>
                    {value
                      ? <span className="badge ok"><CheckCircle2 size={11} /> 可用</span>
                      : <span className="badge err"><XCircle size={11} /> 不可用</span>}
                  </td>
                  <td className="small mono muted">{where}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {demo && (
          <div className="small muted" style={{ marginTop: 8 }}>
            Demo 站点的健康字段来自导出快照；上表按 Live 实测结果标注，运行本地 Live 模式可核对 /api/health 实时字段。
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="section-title" style={{ marginTop: 0 }}>检索评测（Live 实测）</div>
        {metricsError && <div className="notice">无法加载 metrics.json：{metricsError}</div>}
        {metrics && (
          <>
            <div className="small muted" style={{ marginBottom: 8 }}>
              语料 {metrics.corpus.courses} 门课 / {metrics.corpus.videos} 讲 / {metrics.corpus.cues} 句 /
              {" "}{metrics.corpus.passages} 片段；{String(metrics.annotation.total_queries)} 条标注查询
              （无答案 {String(metrics.annotation.no_answer)} 条），容差 ±{Number(metrics.annotation.tolerance_ms) / 1000}s。
              判定规则：{String(metrics.annotation.hit_rule)}。
            </div>
            <table className="table">
              <thead>
                <tr><th>模式</th><th>Hit@3</th><th>无答案拒绝</th><th>平均延迟</th><th>P95</th></tr>
              </thead>
              <tbody>
                {Object.entries(metrics.modes).map(([key, value]) => (
                  <tr key={key}>
                    <td>{MODE_NAMES[key] ?? key}</td>
                    <td>{value.hit_at_3}/{value.answered_queries}</td>
                    <td>{value.no_answer_refused}/{value.no_answer_queries}</td>
                    <td>{value.latency_ms_mean.toFixed(1)} ms</td>
                    <td>{value.latency_ms_p95.toFixed(1)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="small muted" style={{ marginTop: 8 }}>
              指标由 scripts/eval_run.py 真实运行生成，保留全部失败样本；语义模式有 1 条同义改写未命中。
            </div>
          </>
        )}
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="section-title" style={{ marginTop: 0 }}>产品与边界</div>
        <p className="small">
          「听见」把课程视频字幕切成可检索片段：B 站链接或 SRT/VTT 导入 → seekdb 落库 →
          全文 + 向量双路召回 → RRF 融合 → 带时间戳跳转；复习清单按时间预算选片。
          Live 模式由 FastAPI + seekdb v1.4.0.0 提供，Demo 模式为真实导出快照。
        </p>
        <ul className="small muted" style={{ margin: "6px 0 0 18px", padding: 0 }}>
          <li>B 站公开字幕轨在无登录环境不可用（实测 95 个榜单视频 + 6 个课程视频），产品引导用「视频字幕提取器 Pro」导出 SRT；服务端不接触 Cookie。</li>
          <li>Demo 静态站点只做浏览器关键词过滤，不等于 seekdb 混合检索。</li>
          <li>本地视频使用浏览器临时 URL，不上传、不托管，关闭页面后需重新选择。</li>
          <li>复习清单为相关度 + 覆盖贪心并合并区间，未实现 MMR，不宣称 MMR。</li>
          <li>无答案查询依赖语义阈值门禁，仍可能把弱相关片段判为有答案。</li>
          <li>界面布局参考 FlowOSS（app.flowoss.com）逆向规格：图标轨 + 上下文侧栏 + 标签栏 + 状态栏；来源记录见 THIRD_PARTY_NOTICES.md。</li>
          <li>界面设计参考 VideoNote（Apache-2.0）与 BiliNote（MIT），来源与修改记录见 THIRD_PARTY_NOTICES.md。</li>
        </ul>
      </div>
    </div>
  );
}

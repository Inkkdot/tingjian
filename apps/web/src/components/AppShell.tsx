import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  BookOpen, ListChecks, PanelLeftClose, PanelLeftOpen, Search, Settings, Upload,
  type LucideIcon,
} from "lucide-react";
import type { Health } from "../lib/types";

export type PageKey = "search" | "library" | "review" | "import" | "settings";

interface NavEntry {
  key: PageKey;
  label: string;
  icon: LucideIcon;
  group: string;
}

const NAV: NavEntry[] = [
  { key: "search", label: "搜索", icon: Search, group: "工作台" },
  { key: "library", label: "我的库", icon: BookOpen, group: "工作台" },
  { key: "review", label: "复习清单", icon: ListChecks, group: "工作台" },
  { key: "import", label: "导入", icon: Upload, group: "管理" },
  { key: "settings", label: "设置", icon: Settings, group: "管理" },
];

interface AppShellProps {
  page: PageKey;
  onNavigate: (page: PageKey) => void;
  collapsed: boolean;
  onToggle: () => void;
  health: Health | null;
  courses: number;
  videos: number;
  title: string;
  subtitle: string;
  query: string;
  onQueryChange: (query: string) => void;
  onSearch: (query: string) => void;
  children: ReactNode;
}

export default function AppShell(props: AppShellProps) {
  const {
    page, onNavigate, collapsed, onToggle, health, courses, videos,
    title, subtitle, query, onQueryChange, onSearch, children,
  } = props;
  const [draft, setDraft] = useState(query);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => setDraft(query), [query]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if (event.key === "/" && !typing) {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const mode = health?.mode === "demo" ? "demo" : "live";
  const groups = Array.from(new Set(NAV.map((item) => item.group)));

  return (
    <div className={`app-shell${collapsed ? " collapsed" : ""}`}>
      <aside className="sidebar" aria-label="主导航">
        <div className="brand">
          <div className="brand-mark">听</div>
          <div className="brand-copy">
            <div className="brand-name">听见</div>
            <div className="brand-sub">课程字幕检索</div>
          </div>
        </div>
        <button className="btn primary" onClick={() => onNavigate("import")} title="导入字幕">
          <Upload size={16} />
          <span className="nav-label">导入字幕</span>
        </button>
        <nav style={{ display: "grid", gap: 12 }}>
          {groups.map((group) => (
            <div className="nav-group" key={group}>
              <div className="nav-group-title">{group}</div>
              {NAV.filter((item) => item.group === group).map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.key}
                    className={`nav-item${page === item.key ? " active" : ""}`}
                    onClick={() => onNavigate(item.key)}
                    title={item.label}
                    aria-current={page === item.key ? "page" : undefined}
                  >
                    <Icon size={17} />
                    <span className="nav-label">{item.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="nav-spacer" />
        <div className="usage-card">
          <div className="num">{health?.passage_count ?? 0}</div>
          <div className="cap">已索引片段</div>
        </div>
        <div className="usage-card">
          <div className="num">{health?.cue_count ?? 0}</div>
          <div className="cap">原始字幕行</div>
        </div>
        <button className="collapse-btn" onClick={onToggle} aria-label="折叠侧栏">
          {collapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div>
            <div className="page-title">{title}</div>
            <div className="page-sub">{subtitle}</div>
          </div>
          <div className="topbar-spacer" />
          <form
            className="global-search"
            onSubmit={(event) => {
              event.preventDefault();
              onSearch(draft);
            }}
          >
            <Search size={15} color="var(--vm-muted)" />
            <input
              ref={searchRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="搜索字幕，按 / 聚焦"
              aria-label="全局搜索"
            />
            <span className="mono small muted" style={{ fontSize: 10 }}>Enter</span>
          </form>
          <div className={`mode-badge${mode === "live" ? " live" : ""}`}>
            <span className="dot" />
            {mode === "live" ? "LIVE · seekdb" : "DEMO · 离线样例"}
          </div>
        </header>
        {mode === "demo" && (
          <div className="notice" style={{ margin: "10px 20px 0" }}>
            <strong>Demo 模式：</strong>页面读取由 Live 模式真实 seekdb 导出的样例快照，
            浏览器内只做关键词过滤，不代表 seekdb 全文 + 向量混合检索。导入与复习清单需在本地 Live 运行。
          </div>
        )}
        <main className="page">{children}</main>
        <footer className="page-sub" style={{ padding: "0 22px 18px" }}>
          {courses} 门课程 · {videos} 讲 · {health?.database ?? "seekdb"}
          {health?.embedding_model ? ` · ${health.embedding_model}` : ""}
        </footer>
      </div>
    </div>
  );
}

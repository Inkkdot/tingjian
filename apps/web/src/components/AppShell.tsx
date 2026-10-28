import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import {
  BookOpen, ExternalLink, FileText, Github, ListChecks, Moon, Search, Settings, Sun, Upload, X,
  type LucideIcon,
} from "lucide-react";
import type { Course, Health, Video } from "../lib/types";

export type PageKey = "search" | "library" | "review" | "import" | "settings";
export type Theme = "auto" | "light" | "dark";

const PAGE_LABEL: Record<PageKey, string> = {
  search: "搜索",
  library: "我的库",
  review: "复习清单",
  import: "导入",
  settings: "设置",
};

const RAIL: Array<{ key: PageKey; label: string; icon: LucideIcon }> = [
  { key: "search", label: "搜索", icon: Search },
  { key: "library", label: "我的库", icon: BookOpen },
  { key: "import", label: "导入", icon: Upload },
  { key: "review", label: "复习清单", icon: ListChecks },
];

interface AppShellProps {
  page: PageKey;
  onNavigate: (page: PageKey) => void;
  openTabs: PageKey[];
  onCloseTab: (page: PageKey) => void;
  health: Health | null;
  courses: Course[];
  videos: Video[];
  query: string;
  onSearch: (query: string) => void;
  searchFocusRef: RefObject<HTMLInputElement | null>;
  searchCourseId: string;
  onSearchCourseId: (courseId: string) => void;
  activeVideo: Video | null;
  onActiveVideo: (video: Video | null) => void;
  libCourseId: string;
  onLibCourseId: (courseId: string) => void;
  theme: Theme;
  resolvedTheme: "light" | "dark";
  onThemeChange: (theme: Theme) => void;
  children: ReactNode;
}

const SIDE_MIN = 200;
const SIDE_MAX = 360;

export default function AppShell(props: AppShellProps) {
  const {
    page, onNavigate, openTabs, onCloseTab, health, courses, videos,
    query, onSearch, searchFocusRef, searchCourseId, onSearchCourseId,
    activeVideo, onActiveVideo, libCourseId, onLibCourseId,
    theme, resolvedTheme, onThemeChange, children,
  } = props;

  const [draft, setDraft] = useState(query);
  const [sideW, setSideW] = useState(() => {
    const saved = Number(window.localStorage.getItem("tj-side-w"));
    return saved >= SIDE_MIN && saved <= SIDE_MAX ? saved : 240;
  });
  const [dragging, setDragging] = useState(false);
  const lastSide = useRef<PageKey>("search");

  useEffect(() => setDraft(query), [query]);
  useEffect(() => {
    if (page !== "settings") lastSide.current = page;
  }, [page]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      const combo = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
      if ((combo || (event.key === "/" && !typing)) && !event.altKey) {
        event.preventDefault();
        onNavigate("search");
        requestAnimationFrame(() => searchFocusRef.current?.focus());
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onNavigate, searchFocusRef]);

  function startSashDrag(event: React.PointerEvent) {
    event.preventDefault();
    setDragging(true);
    const startX = event.clientX;
    const startW = sideW;
    let latest = sideW;
    const move = (ev: PointerEvent) => {
      latest = Math.min(SIDE_MAX, Math.max(SIDE_MIN, startW + ev.clientX - startX));
      setSideW(latest);
    };
    const up = () => {
      setDragging(false);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.localStorage.setItem("tj-side-w", String(latest));
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  const sideMode = page === "settings" ? lastSide.current : page;
  const mode = health?.mode === "demo" ? "demo" : "live";
  const railVideos = searchCourseId
    ? videos.filter((video) => video.course_id === searchCourseId)
    : videos;
  const libVideos = libCourseId
    ? videos.filter((video) => video.course_id === libCourseId)
    : videos;
  const totalCues = libVideos.reduce((sum, video) => sum + (video.cue_count ?? 0), 0);
  const totalPassages = libVideos.reduce((sum, video) => sum + (video.passage_count ?? 0), 0);
  const embedded = libVideos.reduce((sum, video) => sum + (video.embedded_count ?? 0), 0);

  return (
    <div className="tj-app">
      <nav className="tj-rail" aria-label="主导航">
        {RAIL.map((item) => {
          const Icon = item.icon;
          const active = page === item.key || (page === "settings" && lastSide.current === item.key);
          return (
            <button
              key={item.key}
              className={`tj-rail-btn${active ? " active" : ""}`}
              onClick={() => onNavigate(item.key)}
              title={item.label}
              aria-label={item.label}
              aria-current={page === item.key ? "page" : undefined}
            >
              <Icon />
            </button>
          );
        })}
        <div className="tj-rail-spacer" />
        <button
          className="tj-rail-btn"
          onClick={() => onThemeChange(resolvedTheme === "dark" ? "light" : "dark")}
          title={resolvedTheme === "dark" ? "切换到浅色" : "切换到深色"}
          aria-label="切换颜色模式"
        >
          {resolvedTheme === "dark" ? <Sun /> : <Moon />}
        </button>
        <button
          className={`tj-rail-btn${page === "settings" ? " active" : ""}`}
          onClick={() => onNavigate("settings")}
          title="设置"
          aria-label="设置"
        >
          <Settings />
        </button>
      </nav>

      <div className="tj-side-wrap">
        <aside
          className="tj-sidebar"
          style={{ width: sideW, maxWidth: sideW }}
          aria-label={`${PAGE_LABEL[sideMode]}面板`}
        >
          {sideMode === "search" && (
            <>
              <div className="tj-side-head">
                搜索
                <span className="tj-side-sub">{videos.length} 讲</span>
              </div>
              <div className="tj-side-body tj-scroll">
                <form
                  className="tj-side-search"
                  onSubmit={(event) => {
                    event.preventDefault();
                    onSearch(draft);
                  }}
                >
                  <Search size={14} color="var(--vm-muted)" />
                  <input
                    ref={searchFocusRef}
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="搜索字幕…"
                    aria-label="搜索课程字幕"
                  />
                  <span className="tj-kbd">Ctrl K</span>
                </form>
                <div className="tj-section">
                  课程
                  <span className="tj-count">{courses.length}</span>
                </div>
                <button
                  className={`tj-item${searchCourseId === "" ? " active" : ""}`}
                  onClick={() => onSearchCourseId("")}
                >
                  <span className="tj-item-label">全部课程</span>
                  <span className="tj-item-meta">{videos.length}</span>
                </button>
                {courses.map((course) => (
                  <button
                    key={course.id}
                    className={`tj-item${searchCourseId === course.id ? " active" : ""}`}
                    onClick={() => onSearchCourseId(course.id)}
                    title={`${course.name} ${course.term}`}
                  >
                    <span className="tj-item-label">{course.name}</span>
                    <span className="tj-item-meta">{course.video_count}</span>
                  </button>
                ))}
                <div className="tj-section">
                  讲次
                  <span className="tj-count">{railVideos.length}</span>
                </div>
                {railVideos.map((video) => (
                  <button
                    key={video.id}
                    className={`tj-item tall${activeVideo?.id === video.id ? " active" : ""}`}
                    onClick={() => onActiveVideo(video)}
                    title={video.title}
                  >
                    <span className="tj-item-label">{video.title}</span>
                  </button>
                ))}
                {railVideos.length === 0 && (
                  <div className="tj-item-note">暂无讲次，先去「导入」。</div>
                )}
              </div>
            </>
          )}

          {sideMode === "library" && (
            <>
              <div className="tj-side-head">
                我的库
                <span className="tj-side-sub">{libVideos.length} 讲</span>
              </div>
              <div className="tj-side-body tj-scroll">
                <div className="tj-section">
                  课程
                  <span className="tj-count">{courses.length}</span>
                </div>
                <button
                  className={`tj-item${libCourseId === "" ? " active" : ""}`}
                  onClick={() => onLibCourseId("")}
                >
                  <span className="tj-item-label">全部课程</span>
                  <span className="tj-item-meta">{videos.length}</span>
                </button>
                {courses.map((course) => (
                  <button
                    key={course.id}
                    className={`tj-item${libCourseId === course.id ? " active" : ""}`}
                    onClick={() => onLibCourseId(course.id)}
                    title={`${course.name} ${course.term}`}
                  >
                    <span className="tj-item-label">{course.name}</span>
                    <span className="tj-item-meta">{course.video_count}</span>
                  </button>
                ))}
                <div className="tj-section">概览</div>
                <div className="tj-item-note">
                  {totalCues} 条字幕 · {totalPassages} 片段 · {embedded} 已向量化
                </div>
                <div className="tj-item-note">点击封面卡查看讲次字幕。</div>
              </div>
            </>
          )}

          {sideMode === "import" && (
            <>
              <div className="tj-side-head">导入</div>
              <div className="tj-side-body tj-scroll">
                <div className="tj-section">导入方式</div>
                <div className="tj-item-note">
                  <FileText size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
                  B 站链接：读取字幕轨（wbi 签名），自动切句与向量化。
                </div>
                <div className="tj-item-note">
                  <FileText size={12} style={{ verticalAlign: -2, marginRight: 4 }} />
                  SRT / VTT：本地字幕文件兜底，UTF-8。
                </div>
                <div className="tj-section">B 站登录态</div>
                <div className="tj-item-note">
                  {health?.capabilities.bilibili_login
                    ? "已配置（BILIBILI_COOKIE），可读取登录态字幕轨。"
                    : "未配置，只读取匿名公开轨；失败时用 SRT 兜底。"}
                </div>
              </div>
            </>
          )}

          {sideMode === "review" && (
            <>
              <div className="tj-side-head">复习清单</div>
              <div className="tj-side-body tj-scroll">
                <div className="tj-section">流程</div>
                <div className="tj-item-note">1 · 输入考点 / 主题</div>
                <div className="tj-item-note">2 · 选择时间预算</div>
                <div className="tj-item-note">3 · 生成并保存清单，逐段跳转复习</div>
                <div className="tj-item-note">
                  算法为相关度 + 覆盖贪心并合并区间，不冒充 MMR。
                </div>
              </div>
            </>
          )}
          <a
            className="tj-side-repo"
            href="https://github.com/Inkkdot/tingjian"
            target="_blank"
            rel="noreferrer"
            title="源码仓库 https://github.com/Inkkdot/tingjian"
          >
            <Github size={13} />
            <span>源码仓库</span>
            <span className="tj-side-repo-name">Inkkdot/tingjian</span>
            <ExternalLink size={11} />
          </a>
        </aside>
        <div
          className={`tj-sash${dragging ? " dragging" : ""}`}
          role="separator"
          aria-orientation="vertical"
          aria-label="调整侧栏宽度"
          onPointerDown={startSashDrag}
        />
      </div>

      <div className="tj-main">
        <div className="tj-tabbar" role="tablist" aria-label="打开的页面">
          {openTabs.map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={page === tab}
              className={`tj-tab${page === tab ? " active" : ""}`}
              onClick={() => onNavigate(tab)}
            >
              <span className="tj-tab-label">{PAGE_LABEL[tab]}</span>
              {openTabs.length > 1 && (
                <span
                  className="tj-tab-close"
                  role="button"
              aria-label={`关闭 ${PAGE_LABEL[tab]}`}
                  onClick={(event) => {
                    event.stopPropagation();
                    onCloseTab(tab);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      event.stopPropagation();
                      onCloseTab(tab);
                    }
                  }}
                  tabIndex={0}
                >
                  <X size={13} />
                </span>
              )}
            </button>
          ))}
        </div>

        <main className="tj-content tj-scroll">
          {mode === "demo" && (
            <div className="notice" style={{ marginTop: 0 }}>
              <strong>Demo 模式：</strong>页面读取离线字幕快照，浏览器内只做关键词过滤，
              不代表 seekdb 全文 + 向量混合检索。
              SRT 导入写入浏览器内临时索引；复习清单需在本地 Live 运行。
            </div>
          )}
          {children}
        </main>

        <footer className="tj-statusbar">
          <span className={`tj-status-item ${mode}`}>
            <span className="tj-status-dot" />
            {mode === "live"
              ? `LIVE · ${health?.database ?? "seekdb"}`
              : "DEMO · 离线样例快照"}
            {health?.embedding_model ? ` · ${health.embedding_model}` : ""}
          </span>
          <span className="tj-status-item">
            {courses.length} 门课程 · {videos.length} 讲 · {health?.passage_count ?? 0} 片段
            <span style={{ color: "var(--vm-faint)" }}>{theme === "auto" ? "" : ` · ${theme === "dark" ? "深色" : "浅色"}`}</span>
          </span>
        </footer>
      </div>
    </div>
  );
}

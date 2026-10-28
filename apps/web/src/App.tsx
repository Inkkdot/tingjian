import { useCallback, useEffect, useRef, useState } from "react";
import AppShell, { type PageKey, type Theme } from "./components/AppShell";
import { api, errorText, isDemoMode } from "./lib/api";
import { demoCourses, demoHealth, demoVideos, loadFixture } from "./lib/demo";
import type { Course, Fixture, Health, Video } from "./lib/types";
import ImportPage from "./pages/ImportPage";
import LibraryPage from "./pages/LibraryPage";
import ReviewPage from "./pages/ReviewPage";
import SearchPage from "./pages/SearchPage";
import SettingsPage from "./pages/SettingsPage";

const PAGE_TITLES: Record<PageKey, { title: string; sub: string }> = {
  search: { title: "搜索", sub: "" },
  library: {
    title: "我的库",
    sub: "课程与讲次 · 封面即卡片",
  },
  review: {
    title: "复习清单",
    sub: "输入考点与时间预算，生成带理由的片段清单",
  },
  import: {
    title: "导入",
    sub: "B 站链接或 SRT / VTT，写入真实 seekdb",
  },
  settings: {
    title: "设置",
    sub: "外观、运行状态、能力矩阵与检索评测",
  },
};

export default function App() {
  const demo = isDemoMode();
  const [page, setPage] = useState<PageKey>("search");
  const [tabs, setTabs] = useState<PageKey[]>(["search"]);
  const [health, setHealth] = useState<Health | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [fixture, setFixture] = useState<Fixture | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [query, setQuery] = useState("");
  const [searchCourseId, setSearchCourseId] = useState("");
  const [libCourseId, setLibCourseId] = useState("");
  const [activeVideo, setActiveVideo] = useState<Video | null>(null);
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = window.localStorage.getItem("tj-theme");
    return saved === "light" || saved === "dark" || saved === "auto" ? saved : "auto";
  });
  const [resolvedTheme, setResolvedTheme] = useState<"light" | "dark">("light");
  const searchFocusRef = useRef<HTMLInputElement | null>(null);

  const refresh = useCallback(async () => {
    try {
      if (demo) {
        const data = await loadFixture();
        setFixture(data);
        setCourses(demoCourses(data));
        setVideos(demoVideos(data));
        setHealth(demoHealth(data));
      } else {
        const [nextHealth, nextCourses, nextVideos] = await Promise.all([
          api.health(),
          api.courses(),
          api.videos(),
        ]);
        setHealth(nextHealth);
        setCourses(nextCourses.courses);
        setVideos(nextVideos.videos);
      }
      setBootError(null);
    } catch (exc) {
      setBootError(errorText(exc));
    } finally {
      setBooting(false);
    }
  }, [demo]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = theme === "dark" || (theme === "auto" && mq.matches);
      document.documentElement.classList.toggle("dark", dark);
      setResolvedTheme(dark ? "dark" : "light");
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem("tj-theme", theme);
  }, [theme]);

  const navigate = useCallback((next: PageKey) => {
    setPage(next);
    setTabs((open) => (open.includes(next) ? open : [...open, next]));
  }, []);

  const closeTab = useCallback(
    (target: PageKey) => {
      if (tabs.length <= 1) return;
      const index = tabs.indexOf(target);
      const next = tabs.filter((item) => item !== target);
      setTabs(next);
      if (page === target) setPage(next[Math.max(0, index - 1)] ?? next[0]);
    },
    [tabs, page],
  );

  const handleSearch = useCallback((next: string) => {
    setQuery(next.trim());
    setPage("search");
    setTabs((open) => (open.includes("search") ? open : [...open, "search"]));
  }, []);

  const head = PAGE_TITLES[page];

  return (
    <AppShell
      page={page}
      onNavigate={navigate}
      openTabs={tabs}
      onCloseTab={closeTab}
      health={health}
      courses={courses}
      videos={videos}
      query={query}
      onSearch={handleSearch}
      searchFocusRef={searchFocusRef}
      searchCourseId={searchCourseId}
      onSearchCourseId={setSearchCourseId}
      activeVideo={activeVideo}
      onActiveVideo={setActiveVideo}
      libCourseId={libCourseId}
      onLibCourseId={setLibCourseId}
      theme={theme}
      resolvedTheme={resolvedTheme}
      onThemeChange={setTheme}
    >
      {booting && (
        <div className="empty">
          <strong>正在加载</strong>
          <span className="small">{demo ? "读取离线样例快照" : "连接 FastAPI 与 seekdb"}</span>
        </div>
      )}
      {bootError && (
        <div className="notice error" style={{ marginBottom: 14 }}>
          <strong>初始化失败：</strong>{bootError}
          {!demo && (
            <div className="small">
              请确认已启动 FastAPI（默认 http://127.0.0.1:8000）且 seekdb 容器可连接；
              也可在 URL 加 <code>?demo=1</code> 查看静态样例。
            </div>
          )}
        </div>
      )}

      {page !== "search" && head.sub && (
        <div className="page-head">
          <h1>{head.title}</h1>
          <span className="page-sub">{head.sub}</span>
        </div>
      )}

      {page === "search" && (
        <SearchPage
          demo={demo}
          health={health}
          courses={courses}
          videos={videos}
          fixture={fixture}
          query={query}
          onSearch={handleSearch}
          courseId={searchCourseId}
          onCourseId={setSearchCourseId}
          activeVideo={activeVideo}
          onActiveVideo={setActiveVideo}
        />
      )}
      {page === "library" && (
        <LibraryPage
          demo={demo}
          courses={courses}
          videos={videos}
          fixture={fixture}
          libCourseId={libCourseId}
          onLibCourseId={setLibCourseId}
        />
      )}
      {page === "review" && <ReviewPage demo={demo} />}
      {page === "import" && (
        <ImportPage demo={demo} courses={courses} onImported={refresh} />
      )}
      {page === "settings" && (
        <SettingsPage
          demo={demo}
          health={health}
          fixture={fixture}
          theme={theme}
          onThemeChange={setTheme}
        />
      )}
    </AppShell>
  );
}

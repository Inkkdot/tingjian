import { useCallback, useEffect, useState } from "react";
import AppShell, { type PageKey } from "./components/AppShell";
import { api, errorText, isDemoMode } from "./lib/api";
import { demoCourses, demoHealth, demoVideos, loadFixture } from "./lib/demo";
import type { Course, Fixture, Health, Video } from "./lib/types";
import ImportPage from "./pages/ImportPage";
import LibraryPage from "./pages/LibraryPage";
import ReviewPage from "./pages/ReviewPage";
import SearchPage from "./pages/SearchPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  const demo = isDemoMode();
  const [page, setPage] = useState<PageKey>("search");
  const [collapsed, setCollapsed] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [fixture, setFixture] = useState<Fixture | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const [booting, setBooting] = useState(true);
  const [query, setQuery] = useState("");

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

  const handleSearch = (next: string) => {
    setQuery(next.trim());
    setPage("search");
  };

  const titles: Record<PageKey, { title: string; sub: string }> = {
    search: {
      title: "搜索",
      sub: `${courses.length} 门课 · ${videos.length} 讲 · ${health?.passage_count ?? 0} 个可检索片段`,
    },
    library: {
      title: "我的库",
      sub: `${health?.cue_count ?? 0} 条原始字幕 · ${health?.embedded_passage_count ?? 0} 个片段已生成向量`,
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
      sub: "运行状态、能力矩阵与检索评测",
    },
  };

  return (
    <AppShell
      page={page}
      onNavigate={setPage}
      collapsed={collapsed}
      onToggle={() => setCollapsed((value) => !value)}
      health={health}
      courses={courses.length}
      videos={videos.length}
      title={titles[page].title}
      subtitle={titles[page].sub}
      query={query}
      onQueryChange={setQuery}
      onSearch={handleSearch}
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

      {page === "search" && (
        <SearchPage
          demo={demo}
          health={health}
          courses={courses}
          videos={videos}
          fixture={fixture}
          query={query}
          onSearch={handleSearch}
        />
      )}
      {page === "library" && (
        <LibraryPage demo={demo} courses={courses} videos={videos} fixture={fixture} />
      )}
      {page === "review" && <ReviewPage demo={demo} />}
      {page === "import" && (
        <ImportPage demo={demo} courses={courses} onImported={refresh} />
      )}
      {page === "settings" && (
        <SettingsPage demo={demo} health={health} fixture={fixture} />
      )}
    </AppShell>
  );
}

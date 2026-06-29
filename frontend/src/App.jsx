import { useCallback, useEffect, useMemo, useState } from "react";
import { Trophy, Plus, RefreshCw, Settings } from "lucide-react";
import {
  createInvite,
  deleteBracket,
  enableDeveloperMode,
  exportData,
  getInvites,
  getLeaderboard,
  getTournament,
  importData,
  setSubmissionsLocked,
  syncEspn
} from "./api/client.js";
import SettingsPanel from "./components/SettingsPanel.jsx";
import Leaderboard from "./pages/Leaderboard.jsx";
import LiveBracket from "./pages/LiveBracket.jsx";
import BracketDetail from "./pages/BracketDetail.jsx";
import NewBracket from "./pages/NewBracket.jsx";
import InviteBracket from "./pages/InviteBracket.jsx";

function routeFromLocation() {
  const path = window.location.pathname;
  if (path === "/new") return { page: "new" };
  if (path === "/live") return { page: "live" };
  const inviteMatch = path.match(/^\/invite\/([^/]+)/);
  if (inviteMatch) return { page: "invite", token: inviteMatch[1] };
  const match = path.match(/^\/brackets\/([^/]+)/);
  if (match) return { page: "detail", slug: match[1] };
  return { page: "leaderboard" };
}

export default function App() {
  const [route, setRoute] = useState(routeFromLocation);
  const [tournament, setTournament] = useState({ matches: [], rounds: [] });
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [invites, setInvites] = useState([]);
  const [submissionsLocked, setSubmissionsLockedState] = useState(false);
  const [developerToken, setDeveloperToken] = useState(
    () => window.localStorage.getItem("bracket_developer_token") || ""
  );
  const developerMode = Boolean(developerToken);

  const navigate = useCallback((path) => {
    window.history.pushState({}, "", path);
    setRoute(routeFromLocation());
  }, []);

  const load = useCallback(async (refresh = false) => {
    try {
      setError("");
      const [tournamentData, leaderboardData] = await Promise.all([
        getTournament(refresh),
        getLeaderboard()
      ]);
      setTournament(tournamentData);
      setLeaderboard(leaderboardData.brackets);
      setSubmissionsLockedState(Boolean(leaderboardData.submissions_locked));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(true);
    const timer = window.setInterval(() => load(true), 5 * 60 * 1000);
    const onPop = () => setRoute(routeFromLocation());
    window.addEventListener("popstate", onPop);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("popstate", onPop);
    };
  }, [load]);

  const onSync = async () => {
    setSyncing(true);
    try {
      await syncEspn();
      await load(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSyncing(false);
    }
  };

  const onDeleteBracket = async (bracket) => {
    if (!window.confirm(`Delete ${bracket.title}?`)) return;
    try {
      await deleteBracket(bracket.slug, "", developerToken);
      await load(false);
    } catch (err) {
      setError(err.message);
    }
  };

  const unlockDeveloperMode = async (password) => {
    setSettingsError("");
    try {
      const payload = await enableDeveloperMode(password);
      window.localStorage.setItem("bracket_developer_token", payload.developer_token);
      setDeveloperToken(payload.developer_token);
      await refreshInvites(payload.developer_token);
      setSettingsOpen(false);
    } catch (err) {
      setSettingsError(err.message);
    }
  };

  const disableDeveloperMode = () => {
    window.localStorage.removeItem("bracket_developer_token");
    setDeveloperToken("");
    setInvites([]);
    setSettingsError("");
  };

  const refreshInvites = async (token = developerToken) => {
    if (!token) return;
    setSettingsError("");
    try {
      const payload = await getInvites(token);
      setInvites(payload.invites);
      setSubmissionsLockedState(Boolean(payload.submissions_locked));
    } catch (err) {
      setSettingsError(err.message);
    }
  };

  const generateInvite = async (bracketTitle) => {
    setSettingsError("");
    try {
      const invite = await createInvite(bracketTitle, developerToken);
      await refreshInvites();
      return `${window.location.origin}/invite/${invite.token}`;
    } catch (err) {
      setSettingsError(err.message);
      return "";
    }
  };

  const toggleSubmissionsLocked = async () => {
    setSettingsError("");
    try {
      const payload = await setSubmissionsLocked(!submissionsLocked, developerToken);
      setSubmissionsLockedState(Boolean(payload.submissions_locked));
      await refreshInvites();
    } catch (err) {
      setSettingsError(err.message);
    }
  };

  const exportBackup = async () => {
    setSettingsError("");
    try {
      const payload = await exportData(developerToken);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const date = new Date().toISOString().slice(0, 10);
      link.href = url;
      link.download = `world-cup-brackets-${date}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setSettingsError(err.message);
    }
  };

  const importBackup = async (file) => {
    setSettingsError("");
    try {
      const text = await file.text();
      const payload = JSON.parse(text);
      const result = await importData(payload, developerToken);
      await Promise.all([load(false), refreshInvites()]);
      return result.summary;
    } catch (err) {
      setSettingsError(err.message);
      return null;
    }
  };

  const currentView = useMemo(() => {
    if (route.page === "new") {
      if (submissionsLocked) {
        return (
          <section className="page-panel">
            <div className="empty-state">Bracket submissions are locked.</div>
          </section>
        );
      }
      return (
        <NewBracket
          tournament={tournament}
          navigate={navigate}
          developerMode={developerMode}
          refresh={load}
        />
      );
    }
    if (route.page === "invite") {
      return (
        <InviteBracket
          token={route.token}
          tournament={tournament}
          navigate={navigate}
          developerMode={developerMode}
          refresh={load}
        />
      );
    }
    if (route.page === "detail") {
      return (
        <BracketDetail
          slug={route.slug}
          tournament={tournament}
          navigate={navigate}
          developerMode={developerMode}
          developerToken={developerToken}
          refreshLeaderboard={load}
        />
      );
    }
    if (route.page === "live") {
      return <LiveBracket tournament={tournament} />;
    }
    return (
      <Leaderboard
        brackets={leaderboard}
        navigate={navigate}
        loading={loading}
        developerMode={developerMode}
        onDelete={onDeleteBracket}
      />
    );
  }, [
    route,
    tournament,
    navigate,
    load,
    leaderboard,
    loading,
    developerMode,
    developerToken,
    submissionsLocked
  ]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand-button" onClick={() => navigate("/")}>
          <Trophy size={22} />
          <span>World Cup Brackets</span>
        </button>
        <div className="topbar-actions">
          <button
            className="icon-button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Settings"
            title="Settings"
          >
            <Settings size={18} />
          </button>
          <button className="icon-button" onClick={onSync} aria-label="Sync ESPN" title="Sync ESPN">
            <RefreshCw size={18} className={syncing ? "spin" : ""} />
          </button>
          <button
            className="primary-button"
            disabled={submissionsLocked}
            onClick={() => navigate("/new")}
            title={submissionsLocked ? "Bracket submissions are locked" : "New Bracket"}
          >
            <Plus size={18} />
            New Bracket
          </button>
        </div>
      </header>
      {settingsOpen ? (
        <SettingsPanel
          developerMode={developerMode}
          invites={invites}
          submissionsLocked={submissionsLocked}
          error={settingsError}
          onClose={() => setSettingsOpen(false)}
          onDisableDeveloperMode={disableDeveloperMode}
          onEnableDeveloperMode={unlockDeveloperMode}
          onGenerateInvite={generateInvite}
          onExportBackup={exportBackup}
          onImportBackup={importBackup}
          onRefreshInvites={() => refreshInvites()}
          onToggleSubmissionsLocked={toggleSubmissionsLocked}
        />
      ) : null}
      {error ? <div className="error-banner">{error}</div> : null}
      {["leaderboard", "live"].includes(route.page) ? (
        <nav className="view-tabs" aria-label="Main views">
          <button
            className={route.page === "leaderboard" ? "active" : ""}
            onClick={() => navigate("/")}
          >
            Leaderboard
          </button>
          <button
            className={route.page === "live" ? "active" : ""}
            onClick={() => navigate("/live")}
          >
            Live Bracket
          </button>
        </nav>
      ) : null}
      <main>{currentView}</main>
    </div>
  );
}

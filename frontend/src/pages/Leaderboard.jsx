import { useEffect, useState } from "react";
import ScorePill from "../components/ScorePill.jsx";

export default function Leaderboard({ brackets, spotlightMatch, spotlightState, navigate, loading }) {
  const ranks = tiedRanks(brackets);

  return (
    <section className="page-panel">
      <div className="page-heading">
        <div>
          <h1>Leaderboard</h1>
        </div>
        {spotlightMatch ? (
          <SpotlightMatchCard match={spotlightMatch} state={spotlightState} />
        ) : null}
      </div>
      <div className="leaderboard">
        {loading ? <div className="empty-state">Loading brackets...</div> : null}
        {!loading && brackets.length === 0 ? (
          <div className="empty-state">No brackets yet.</div>
        ) : null}
        {brackets.map((bracket, index) => (
          <div
            className={`leader-row${spotlightMatch ? " with-live-pick" : ""}`}
            key={bracket.slug}
            onClick={() => navigate(`/brackets/${bracket.slug}`)}
            role="button"
            tabIndex={0}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                navigate(`/brackets/${bracket.slug}`);
              }
            }}
          >
            <span className="rank">{ranks[index]}</span>
            <span className="leader-main">
              <span className="leader-title">{bracket.title}</span>
              <ChampionFlag team={bracket.champion_pick?.team} />
            </span>
            {spotlightMatch ? (
              <SpotlightPick pick={bracket.spotlight_pick || bracket.live_pick} />
            ) : null}
            <ScorePill score={bracket.score} />
            <span className="leader-max">
              <span>MAX</span>
              <strong>{bracket.score.max_possible}</strong>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function SpotlightMatchCard({ match, state }) {
  const countdown = useCountdown(match.starts_at, state === "upcoming");

  return (
    <section
      className="leader-live-card"
      aria-label={state === "upcoming" ? "Next match" : "Current live match"}
    >
      <div className="leader-live-meta">
        <span>
          {state === "upcoming" ? "Next: Match" : "Match"} {match.match_number || match.position}
        </span>
        <strong>{state === "upcoming" ? countdown : liveLabel(match)}</strong>
      </div>
      {formatVenue(match) ? <div className="leader-live-venue">{formatVenue(match)}</div> : null}
      <div className="leader-live-teams">
        <LiveTeam team={match.team_one} score={match.score_one} />
        <LiveTeam team={match.team_two} score={match.score_two} />
      </div>
    </section>
  );
}

function LiveTeam({ team, score }) {
  return (
    <span className="leader-live-team">
      {team?.logo_url ? <img src={team.logo_url} alt="" /> : <span className="leader-live-mark" />}
      <span>{team?.display_name || "TBD"}</span>
      {score !== null && score !== undefined ? <strong>{score}</strong> : null}
    </span>
  );
}

function SpotlightPick({ pick }) {
  if (!pick?.team) {
    return <span className="leader-live-pick empty">No pick</span>;
  }
  return (
    <span className="leader-live-pick" title={`Match pick: ${pick.team.display_name}`}>
      {pick.team.logo_url ? <img src={pick.team.logo_url} alt="" /> : null}
      <span>{pick.team.abbreviation || pick.team.display_name}</span>
    </span>
  );
}

function liveLabel(match) {
  const status = (match.status || "").trim();
  return status || "Live";
}

function useCountdown(startsAt, active) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active || !startsAt) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active, startsAt]);

  if (!active) return "";
  return formatCountdown(startsAt, now);
}

function formatCountdown(startsAt, now) {
  const target = new Date(startsAt).getTime();
  if (Number.isNaN(target)) return "";
  const diff = Math.max(0, target - now);
  if (diff === 0) return "Starting";
  const totalSeconds = Math.floor(diff / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

function formatVenue(match) {
  return [match.venue_name, match.venue_city].filter(Boolean).join(" · ");
}

function tiedRanks(brackets) {
  return brackets.map((bracket, index) => {
    return brackets.filter((other) => other.score.total > bracket.score.total).length + 1;
  });
}

function ChampionFlag({ team }) {
  if (!team) {
    return <span className="leader-flag-placeholder" aria-label="No champion selected" />;
  }
  return (
    <span className="leader-flag" title={team.display_name} aria-label={team.display_name}>
      {team.logo_url ? <img src={team.logo_url} alt="" /> : team.abbreviation}
    </span>
  );
}

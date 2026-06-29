import ScorePill from "../components/ScorePill.jsx";

export default function Leaderboard({ brackets, liveMatch, navigate, loading }) {
  const ranks = tiedRanks(brackets);

  return (
    <section className="page-panel">
      <div className="page-heading">
        <div>
          <h1>Leaderboard</h1>
        </div>
        {liveMatch ? <LiveMatchCard match={liveMatch} /> : null}
      </div>
      <div className="leaderboard">
        {loading ? <div className="empty-state">Loading brackets...</div> : null}
        {!loading && brackets.length === 0 ? (
          <div className="empty-state">No brackets yet.</div>
        ) : null}
        {brackets.map((bracket, index) => (
          <div
            className={`leader-row${liveMatch ? " with-live-pick" : ""}`}
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
            {liveMatch ? <LivePick pick={bracket.live_pick} /> : null}
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

function LiveMatchCard({ match }) {
  return (
    <section className="leader-live-card" aria-label="Current live match">
      <div className="leader-live-meta">
        <span>Match {match.match_number || match.position}</span>
        <strong>{liveLabel(match)}</strong>
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

function LivePick({ pick }) {
  if (!pick?.team) {
    return <span className="leader-live-pick empty">No pick</span>;
  }
  return (
    <span className="leader-live-pick" title={`Live pick: ${pick.team.display_name}`}>
      {pick.team.logo_url ? <img src={pick.team.logo_url} alt="" /> : null}
      <span>{pick.team.abbreviation || pick.team.display_name}</span>
    </span>
  );
}

function liveLabel(match) {
  const status = (match.status || "").trim();
  return status || "Live";
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

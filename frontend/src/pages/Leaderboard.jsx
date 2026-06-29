import ScorePill from "../components/ScorePill.jsx";
import { Trash2 } from "lucide-react";

export default function Leaderboard({ brackets, navigate, loading, developerMode, onDelete }) {
  const ranks = tiedRanks(brackets);

  return (
    <section className="page-panel">
      <div className="page-heading">
        <div>
          <h1>Leaderboard</h1>
        </div>
      </div>
      <div className="leaderboard">
        {loading ? <div className="empty-state">Loading brackets...</div> : null}
        {!loading && brackets.length === 0 ? (
          <div className="empty-state">No brackets yet.</div>
        ) : null}
        {brackets.map((bracket, index) => (
          <div
            className="leader-row"
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
            <span className="remaining">
              MAX {bracket.score.max_possible}
            </span>
            <ScorePill score={bracket.score} />
            {developerMode ? (
              <button
                className="icon-danger-button"
                aria-label={`Delete ${bracket.title}`}
                title="Delete"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(bracket);
                }}
              >
                <Trash2 size={18} />
              </button>
            ) : (
              <span className="leader-lock-space" />
            )}
          </div>
        ))}
      </div>
    </section>
  );
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

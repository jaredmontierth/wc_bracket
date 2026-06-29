import TeamButton from "./TeamButton.jsx";
import {
  ROUND_KEYS,
  ROUND_LABELS,
  advancePick,
  groupMatches,
  projectedTeams
} from "../bracket/structure.js";

export default function BracketBoard({ matches, picks, onPick, scoringPicks = [] }) {
  const pickingMode = Boolean(onPick);
  const matchesByRound = groupMatches(matches);
  const scoringBySlot = scoringPicks.reduce((map, pick) => {
    map[pick.slot_key] = pick;
    return map;
  }, {});

  const chooseWinner = (match, winner) => {
    if (!onPick) return;
    onPick(advancePick(match, winner, picks, matchesByRound));
  };

  return (
    <section className="bracket-board" aria-label="Tournament bracket">
      {ROUND_KEYS.map((roundKey) => (
        <div className="round-column" key={roundKey}>
          <div className="round-header">
            <span>{ROUND_LABELS[roundKey]}</span>
            <small>{matchesByRound[roundKey]?.[0]?.points || 0} pts</small>
          </div>
          <div className="match-list">
            {(matchesByRound[roundKey] || []).map((match) => {
              const teams = projectedTeams(match, picks, matchesByRound);
              const selected = picks[match.slot_key];
              const scoring = scoringBySlot[match.slot_key];
              const winnerScore = winnerFirstScore(match);
              return (
                <article className="match-card" key={match.slot_key}>
                  <div className="match-meta">
                    <span>Match {match.match_number || match.position}</span>
                    {!pickingMode ? (
                      <strong>{match.is_complete ? "Final" : formatMatchTime(match.starts_at)}</strong>
                    ) : null}
                  </div>
                  {formatVenue(match) ? (
                    <div className="match-details">
                      <span>{formatVenue(match)}</span>
                    </div>
                  ) : null}
                  <TeamButton
                    team={teams[0]}
                    selected={selected?.espn_id === teams[0]?.espn_id}
                    disabled={!onPick}
                    result={resultClass(scoring, teams[0])}
                    onSelect={(team) => chooseWinner(match, team)}
                  />
                  <TeamButton
                    team={teams[1]}
                    selected={selected?.espn_id === teams[1]?.espn_id}
                    disabled={!onPick}
                    result={resultClass(scoring, teams[1])}
                    onSelect={(team) => chooseWinner(match, team)}
                  />
                  {!pickingMode && match.is_complete && match.winner ? (
                    <div className="match-result">
                      Winner: {match.winner.display_name}
                      {winnerScore ? ` ${winnerScore}` : ""}
                    </div>
                  ) : null}
                </article>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}

function formatMatchTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function formatVenue(match) {
  return [match.venue_name, match.venue_city].filter(Boolean).join(" · ");
}

function resultClass(scoring, team) {
  if (!scoring || scoring.correct === null || !team) return "";
  if (scoring.team.espn_id !== team.espn_id) return "";
  return scoring.correct ? "correct" : "incorrect";
}

function winnerFirstScore(match) {
  if (match.score_one === null || match.score_two === null || !match.winner) {
    return "";
  }
  if (match.winner.espn_id === match.team_one?.espn_id) {
    return `${match.score_one}-${match.score_two}`;
  }
  if (match.winner.espn_id === match.team_two?.espn_id) {
    return `${match.score_two}-${match.score_one}`;
  }
  return `${Math.max(match.score_one, match.score_two)}-${Math.min(match.score_one, match.score_two)}`;
}

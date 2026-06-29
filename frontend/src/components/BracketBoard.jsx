import TeamButton from "./TeamButton.jsx";
import {
  ROUND_KEYS,
  ROUND_LABELS,
  advancePick,
  groupMatches,
  projectedTeams
} from "../bracket/structure.js";

export default function BracketBoard({
  matches,
  picks,
  onPick,
  scoringPicks = [],
  actualMode = false,
  showActualMismatch = false
}) {
  const pickingMode = Boolean(onPick);
  const matchesByRound = groupMatches(matches);
  const scoringBySlot = scoringPicks.reduce((map, pick) => {
    map[pick.slot_key] = pick;
    return map;
  }, {});
  const eliminatedTeamIds = eliminatedTeamsFromScoring(scoringPicks);

  const chooseWinner = (match, winner) => {
    if (!onPick) return;
    onPick(advancePick(match, winner, picks, matchesByRound));
  };

  return (
    <section className={`bracket-board${actualMode ? " actual-mode" : ""}`} aria-label="Tournament bracket">
      {ROUND_KEYS.map((roundKey) => (
        <div className="round-column" key={roundKey}>
          <div className="round-header">
            <span>{ROUND_LABELS[roundKey]}</span>
            <small>{matchesByRound[roundKey]?.[0]?.points || 0} pts</small>
          </div>
          <div className="match-list">
            {(matchesByRound[roundKey] || []).map((match) => {
              const teams = actualMode ? [match.team_one, match.team_two] : projectedTeams(match, picks, matchesByRound);
              const selected = picks[match.slot_key];
              const scoring = scoringBySlot[match.slot_key];
              const winnerScore = winnerFirstScore(match);
              const live = isLiveMatch(match);
              const showScore = !pickingMode && (match.is_complete || live);
              const actualText = showActualMismatch ? actualMatchText(match, teams, showScore) : "";
              const cardClass = ["match-card", live ? "live" : "", matchResultClass(scoring, teams, eliminatedTeamIds)]
                .filter(Boolean)
                .join(" ");
              return (
                <article className={cardClass} key={match.slot_key}>
                  <div className="match-meta">
                    <span>Match {match.match_number || match.position}</span>
                    {!pickingMode ? (
                      <strong className={live ? "live-label" : ""}>
                        {match.is_complete ? "Final" : live ? liveLabel(match) : formatMatchTime(match.starts_at)}
                      </strong>
                    ) : null}
                  </div>
                  {formatVenue(match) ? (
                    <div className="match-details">
                      <span>{formatVenue(match)}</span>
                    </div>
                  ) : null}
                  <TeamButton
                    team={teams[0]}
                    selected={isSelected(selected, teams[0])}
                    disabled={!onPick}
                    result={actualResultClass(actualMode, match, teams[0]) || resultClass(scoring, teams[0])}
                    eliminated={isEliminated(eliminatedTeamIds, teams[0])}
                    score={showScore ? scoreForTeam(match, teams[0]) : null}
                    onSelect={(team) => chooseWinner(match, team)}
                  />
                  <TeamButton
                    team={teams[1]}
                    selected={isSelected(selected, teams[1])}
                    disabled={!onPick}
                    result={actualResultClass(actualMode, match, teams[1]) || resultClass(scoring, teams[1])}
                    eliminated={isEliminated(eliminatedTeamIds, teams[1])}
                    score={showScore ? scoreForTeam(match, teams[1]) : null}
                    onSelect={(team) => chooseWinner(match, team)}
                  />
                  {!pickingMode && match.is_complete && match.winner ? (
                    <div className="match-result">
                      Winner: {match.winner.display_name}
                      {winnerScore ? ` ${winnerScore}` : ""}
                    </div>
                  ) : null}
                  {actualText ? <div className="actual-match-strip">{actualText}</div> : null}
                </article>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}

function eliminatedTeamsFromScoring(scoringPicks) {
  return new Set(
    scoringPicks
      .filter((pick) => pick.correct === false && pick.team?.espn_id)
      .map((pick) => pick.team.espn_id)
  );
}

function isEliminated(eliminatedTeamIds, team) {
  return Boolean(team?.espn_id && eliminatedTeamIds.has(team.espn_id));
}

function isSelected(selected, team) {
  return Boolean(selected?.espn_id && team?.espn_id && selected.espn_id === team.espn_id);
}

function matchResultClass(scoring, teams, eliminatedTeamIds) {
  if (scoring?.correct === true) return "correct";
  if (scoring?.correct === false) return "incorrect";
  const presentTeams = teams.filter(Boolean);
  if (
    presentTeams.length === 2 &&
    presentTeams.every((team) => isEliminated(eliminatedTeamIds, team))
  ) {
    return "incorrect";
  }
  return "";
}

function actualMatchText(match, projectedTeamsForCard, showScore) {
  if (!match.team_one || !match.team_two) return "";
  const projected = projectedTeamsForCard.filter(Boolean);
  if (projected.length !== 2) return "";
  const projectedIds = projected.map((team) => team.espn_id).sort().join("|");
  const actualIds = [match.team_one.espn_id, match.team_two.espn_id].sort().join("|");
  if (projectedIds === actualIds) return "";

  const teamOneScore = showScore && match.score_one !== null && match.score_one !== undefined ? ` ${match.score_one}` : "";
  const teamTwoScore = showScore && match.score_two !== null && match.score_two !== undefined ? `${match.score_two} ` : "";
  const separator = showScore && (teamOneScore || teamTwoScore) ? "-" : " vs ";
  return `Actual: ${match.team_one.display_name}${teamOneScore}${separator}${teamTwoScore}${match.team_two.display_name}`;
}

function isLiveMatch(match) {
  if (match.is_complete) return false;
  const status = (match.status || "").toLowerCase();
  return /live|progress|half|extra|^[1-9]\d*'?$/.test(status);
}

function liveLabel(match) {
  const status = (match.status || "").trim();
  if (/^\d+'?$/.test(status)) {
    return status.endsWith("'") ? status : `${status}'`;
  }
  if (/half/i.test(status)) return "HT";
  return "Live";
}

function scoreForTeam(match, team) {
  if (!team) return null;
  if (team.espn_id === match.team_one?.espn_id) return match.score_one;
  if (team.espn_id === match.team_two?.espn_id) return match.score_two;
  return null;
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

function actualResultClass(actualMode, match, team) {
  if (!actualMode || !match.is_complete || !match.winner || !team) return "";
  return match.winner.espn_id === team.espn_id ? "winner" : "";
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

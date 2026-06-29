export const ROUND_KEYS = ["r32", "r16", "qf", "sf", "final"];

export const ROUND_LABELS = {
  r32: "Round of 32",
  r16: "Round of 16",
  qf: "Quarterfinals",
  sf: "Semifinals",
  final: "Final"
};

export function groupMatches(matches) {
  return ROUND_KEYS.reduce((grouped, roundKey) => {
    grouped[roundKey] = matches
      .filter((match) => match.round_key === roundKey)
      .sort((a, b) => a.position - b.position);
    return grouped;
  }, {});
}

export function nextSlotKey(match) {
  return (match.next_slot_key || null);
}

export function pickMapFromArray(picks = []) {
  return picks.reduce((map, pick) => {
    map[pick.slot_key] = pick.team;
    return map;
  }, {});
}

export function picksArrayFromMap(pickMap) {
  return Object.entries(pickMap).map(([slot_key, team]) => ({ slot_key, team }));
}

export function projectedTeams(match, picks, matchesByRound) {
  if (match.round_key === "r32") {
    return [match.team_one, match.team_two];
  }
  return [
    match.previous_slot_one ? picks[match.previous_slot_one] : null,
    match.previous_slot_two ? picks[match.previous_slot_two] : null
  ];
}

export function advancePick(match, winner, pickMap, matchesByRound) {
  const nextSlot = findNextSlotKey(match, matchesByRound);
  const nextPicks = { ...pickMap, [match.slot_key]: winner };
  if (!nextSlot) return nextPicks;

  const nextMatch = Object.values(matchesByRound)
    .flat()
    .find((candidate) => candidate.slot_key === nextSlot);
  if (!nextMatch) return nextPicks;

  const staleWinner = nextPicks[nextSlot];
  const teams = projectedTeams(nextMatch, nextPicks, matchesByRound).filter(Boolean);
  if (staleWinner && !teams.some((team) => team.espn_id === staleWinner.espn_id)) {
    delete nextPicks[nextSlot];
  }
  return nextPicks;
}

export function findNextSlotKey(match, matchesByRound) {
  const nextMatch = Object.values(matchesByRound)
    .flat()
    .find(
      (candidate) =>
        candidate.previous_slot_one === match.slot_key ||
        candidate.previous_slot_two === match.slot_key
    );
  return nextMatch?.slot_key || null;
}

export function autofillPicks(matches, existingPicks = {}) {
  const matchesByRound = groupMatches(matches);
  const nextPicks = { ...existingPicks };
  for (const roundKey of ROUND_KEYS) {
    for (const match of matchesByRound[roundKey] || []) {
      const teams = projectedTeams(match, nextPicks, matchesByRound).filter(Boolean);
      if (teams.length === 0) continue;
      const winner = teams[Math.floor(Math.random() * teams.length)];
      Object.assign(nextPicks, advancePick(match, winner, nextPicks, matchesByRound));
    }
  }
  return nextPicks;
}

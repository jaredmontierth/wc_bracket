export default function TeamButton({ team, selected, disabled, result, onSelect }) {
  const className = ["team-button", selected ? "selected" : "", result || ""]
    .filter(Boolean)
    .join(" ");
  return (
    <button className={className} disabled={disabled || !team} onClick={() => team && onSelect(team)}>
      {team?.logo_url ? <img src={team.logo_url} alt="" /> : <span className="team-mark" />}
      <span className="team-name">{team?.display_name || "TBD"}</span>
      {team?.abbreviation ? <span className="team-code">{team.abbreviation}</span> : null}
    </button>
  );
}


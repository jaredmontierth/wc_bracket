import { useEffect, useState } from "react";
import { Dices, Edit3, Save, Trash2 } from "lucide-react";
import { deleteBracket, getBracket, updateBracket } from "../api/client.js";
import BracketBoard from "../components/BracketBoard.jsx";
import ScorePill from "../components/ScorePill.jsx";
import { autofillPicks, pickMapFromArray, picksArrayFromMap } from "../bracket/structure.js";

export default function BracketDetail({
  slug,
  tournament,
  navigate,
  developerMode,
  developerToken,
  refreshLeaderboard
}) {
  const [bracket, setBracket] = useState(null);
  const [picks, setPicks] = useState({});
  const [titleDraft, setTitleDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const editToken = new URLSearchParams(window.location.search).get("edit") || "";

  useEffect(() => {
    let mounted = true;
    getBracket(slug, editToken, developerToken)
      .then((data) => {
        if (!mounted) return;
        setBracket(data);
        setPicks(pickMapFromArray(data.picks));
        setTitleDraft(data.title);
      })
      .catch((err) => setError(err.message));
    return () => {
      mounted = false;
    };
  }, [slug, editToken, developerToken]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await updateBracket(
        slug,
        titleDraft,
        picksArrayFromMap(picks),
        editToken,
        developerToken
      );
      setBracket(updated);
      setPicks(pickMapFromArray(updated.picks));
      setTitleDraft(updated.title);
      setEditing(false);
      await refreshLeaderboard(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete ${bracket.title}?`)) return;
    setSaving(true);
    setError("");
    try {
      await deleteBracket(slug, editToken, developerToken);
      await refreshLeaderboard(false);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (error) return <div className="error-banner">{error}</div>;
  if (!bracket) return <div className="page-panel">Loading bracket...</div>;

  return (
    <section className="page-panel wide">
      <div className="detail-header">
        <div>
          {editing ? (
            <label className="detail-title-field">
              <span>Bracket name</span>
              <input
                value={titleDraft}
                onChange={(event) => setTitleDraft(event.target.value)}
                placeholder="Bracket name"
              />
            </label>
          ) : (
            <h1>{bracket.title}</h1>
          )}
        </div>
        <div className="detail-actions">
          <ScorePill score={bracket.score} />
          {editing ? (
            <>
              {developerMode ? (
                <button
                  className="secondary-button"
                  onClick={() => setPicks(autofillPicks(tournament.matches, picks))}
                >
                  <Dices size={18} />
                  Autofill
                </button>
              ) : null}
            <button className="primary-button" disabled={saving || !titleDraft.trim()} onClick={save}>
              <Save size={18} />
              Save
            </button>
            </>
          ) : bracket.can_edit ? (
            <>
            <button
              className="secondary-button"
              onClick={() => {
                setTitleDraft(bracket.title);
                setEditing(true);
              }}
            >
              <Edit3 size={18} />
              Edit
            </button>
              {developerMode ? (
                <button className="danger-button" disabled={saving} onClick={remove}>
                  <Trash2 size={18} />
                  Delete
                </button>
              ) : null}
            </>
          ) : developerMode ? (
            <button className="danger-button" disabled={saving} onClick={remove}>
                <Trash2 size={18} />
                Delete
            </button>
          ) : (
            <span className="locked-note">Locked</span>
          )}
        </div>
      </div>
      <div className="round-score-strip">
        {bracket.score.rounds.map((round) => (
          <div key={round.round_key}>
            <span>{round.round_name}</span>
            <strong>
              {round.earned}/{round.possible}
            </strong>
          </div>
        ))}
      </div>
      <BracketBoard
        matches={tournament.matches}
        picks={picks}
        onPick={editing ? setPicks : null}
        scoringPicks={bracket.score.picks}
      />
    </section>
  );
}

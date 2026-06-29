import { useMemo, useState } from "react";
import { Dices, Save } from "lucide-react";
import { createBracket } from "../api/client.js";
import BracketBoard from "../components/BracketBoard.jsx";
import { autofillPicks, picksArrayFromMap } from "../bracket/structure.js";

export default function NewBracket({ tournament, navigate, developerMode, refresh }) {
  const [title, setTitle] = useState("");
  const [picks, setPicks] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const pickCount = useMemo(() => Object.keys(picks).length, [picks]);
  const canSave = title.trim() && pickCount === 31;

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const bracket = await createBracket(title, picksArrayFromMap(picks));
      await refresh(false);
      navigate(`/brackets/${bracket.slug}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-panel wide">
      <div className="editor-bar">
        <div className="title-field">
          <label htmlFor="title">Bracket title</label>
          <input
            id="title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Name"
          />
        </div>
        <div className="save-group">
          <span>{pickCount}/31 picks</span>
          {developerMode ? (
            <button
              className="secondary-button"
              onClick={() => setPicks(autofillPicks(tournament.matches, picks))}
            >
              <Dices size={18} />
              Autofill
            </button>
          ) : null}
          <button className="primary-button" disabled={!canSave || saving} onClick={save}>
            <Save size={18} />
            Save
          </button>
        </div>
      </div>
      {error ? <div className="error-banner inline">{error}</div> : null}
      <BracketBoard matches={tournament.matches} picks={picks} onPick={setPicks} />
    </section>
  );
}

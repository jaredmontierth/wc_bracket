import { useEffect, useMemo, useState } from "react";
import { Dices, Lock, Save } from "lucide-react";
import { getInvite, submitInvite } from "../api/client.js";
import BracketBoard from "../components/BracketBoard.jsx";
import { autofillPicks, pickMapFromArray, picksArrayFromMap } from "../bracket/structure.js";

export default function InviteBracket({ token, tournament, navigate, developerMode, refresh }) {
  const [invite, setInvite] = useState(null);
  const [title, setTitle] = useState("");
  const [picks, setPicks] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const deviceKey = useMemo(getDeviceKey, []);
  const pickCount = useMemo(() => Object.keys(picks).length, [picks]);
  const canSave = title.trim() && pickCount === 31 && !invite?.submitted;

  useEffect(() => {
    let mounted = true;
    getInvite(token, deviceKey)
      .then((data) => {
        if (!mounted) return;
        setInvite(data);
        if (data.bracket) {
          setTitle(data.bracket.title);
          setPicks(pickMapFromArray(data.bracket.picks));
        } else if (data.bracket_title) {
          setTitle(data.bracket_title);
        }
      })
      .catch((err) => setError(err.message));
    return () => {
      mounted = false;
    };
  }, [token, deviceKey]);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const bracket = await submitInvite(token, title, picksArrayFromMap(picks), deviceKey);
      setInvite((current) => ({ ...current, submitted: true, bracket }));
      setPicks(pickMapFromArray(bracket.picks));
      await refresh(false);
      navigate(`/brackets/${bracket.slug}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (error) return <div className="error-banner">{error}</div>;
  if (!invite) return <div className="page-panel">Loading invite...</div>;

  return (
    <section className="page-panel wide">
      <div className="editor-bar">
        <div className="title-field">
          <label htmlFor="title">Bracket title</label>
          <input
            id="title"
            value={title}
            disabled={invite.submitted || Boolean(invite.bracket_title)}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Your name"
          />
        </div>
        <div className="save-group">
          {invite.submitted ? (
            <span className="locked-note">
              <Lock size={16} />
              Submitted
            </span>
          ) : (
            <span>{pickCount}/31 picks</span>
          )}
          {!invite.submitted && developerMode ? (
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
            Submit
          </button>
        </div>
      </div>
      {invite.submitted ? (
        <div className="notice-banner">
          This device has already submitted a bracket for this invite.
        </div>
      ) : null}
      <BracketBoard
        matches={tournament.matches}
        picks={picks}
        onPick={invite.submitted ? null : setPicks}
      />
    </section>
  );
}

function getDeviceKey() {
  const storageKey = "world_cup_bracket_device_key";
  try {
    const existing = window.localStorage.getItem(storageKey);
    if (existing) return existing;
    const key = makeDeviceKey();
    window.localStorage.setItem(storageKey, key);
    return key;
  } catch {
    return makeDeviceKey();
  }
}

function makeDeviceKey() {
  if (window.crypto?.randomUUID) {
    return window.crypto.randomUUID();
  }
  if (window.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }
  const key = `${Date.now()}-${Math.random()}`;
  return key;
}

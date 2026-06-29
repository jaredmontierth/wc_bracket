import {
  Clipboard,
  Download,
  Lock,
  LogOut,
  RefreshCw,
  ShieldCheck,
  Upload,
  Unlock,
  X
} from "lucide-react";
import { useState } from "react";

export default function SettingsPanel({
  developerMode,
  invites,
  submissionsLocked,
  error,
  onClose,
  onDisableDeveloperMode,
  onEnableDeveloperMode,
  onExportBackup,
  onGenerateInvite,
  onImportBackup,
  onRefreshInvites,
  onToggleSubmissionsLocked
}) {
  const [password, setPassword] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [copied, setCopied] = useState(false);
  const [importSummary, setImportSummary] = useState(null);

  const submit = (event) => {
    event.preventDefault();
    onEnableDeveloperMode(password);
    setPassword("");
  };

  const generateInvite = async (event) => {
    event.preventDefault();
    const link = await onGenerateInvite(inviteName);
    if (link) {
      setInviteLink(link);
      setCopied(false);
    }
  };

  const copyInviteLink = async () => {
    if (!inviteLink) return;
    try {
      await navigator.clipboard.writeText(inviteLink);
      setCopied(true);
    } catch {
      window.prompt("Copy invite link", inviteLink);
    }
  };

  const importBackup = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const summary = await onImportBackup(file);
    if (summary) {
      setImportSummary(summary);
    }
  };

  return (
    <div className="modal-backdrop">
      <section className="settings-panel" aria-label="Settings">
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="icon-button" onClick={onClose} aria-label="Close settings">
            <X size={18} />
          </button>
        </div>
        <div className="settings-row">
          <div>
            <strong>Developer mode</strong>
            <p>Unlocks delete controls for every bracket on this device.</p>
          </div>
          {developerMode ? (
            <span className="developer-badge">
              <ShieldCheck size={16} />
              On
            </span>
          ) : null}
        </div>
        {developerMode ? (
          <>
            <div className="settings-row lock-row">
              <div>
                <strong>Submissions</strong>
                <p>{submissionsLocked ? "Invite submissions are locked." : "Invite submissions are open."}</p>
              </div>
              <button className={submissionsLocked ? "secondary-button" : "danger-button"} onClick={onToggleSubmissionsLocked}>
                {submissionsLocked ? <Unlock size={18} /> : <Lock size={18} />}
                {submissionsLocked ? "Unlock" : "Lock"}
              </button>
            </div>
            <form className="settings-form invite-form" onSubmit={generateInvite}>
              <input
                value={inviteName}
                onChange={(event) => setInviteName(event.target.value)}
                placeholder="Bracket name"
              />
              <button className="primary-button" disabled={!inviteName.trim()}>
                Generate
              </button>
            </form>
            {inviteLink ? (
              <button className="copy-link-button" onClick={copyInviteLink}>
                <Clipboard size={18} />
                <span>{inviteLink}</span>
                <strong>{copied ? "Copied" : "Copy"}</strong>
              </button>
            ) : null}
            <div className="settings-row backup-row">
              <div>
                <strong>Backup</strong>
                <p>Move brackets and invite data between local and Render.</p>
              </div>
              <div className="backup-actions">
                <button className="secondary-button" onClick={onExportBackup}>
                  <Download size={18} />
                  Export
                </button>
                <label className="secondary-button file-button">
                  <Upload size={18} />
                  Import
                  <input type="file" accept="application/json" onChange={importBackup} />
                </label>
              </div>
            </div>
            {importSummary ? (
              <div className="import-summary">
                Imported {importSummary.brackets} brackets, {importSummary.picks} picks,{" "}
                {importSummary.invites} invites.
              </div>
            ) : null}
            <div className="invites-section">
              <div className="invites-header">
                <strong>Invites</strong>
                <button className="icon-button" onClick={onRefreshInvites} aria-label="Refresh invites">
                  <RefreshCw size={16} />
                </button>
              </div>
              {invites.length === 0 ? (
                <p>No invites yet.</p>
              ) : (
                <div className="invite-list">
                  {invites.map((invite) => (
                    <InviteRow key={invite.token} invite={invite} />
                  ))}
                </div>
              )}
            </div>
            <button className="secondary-button" onClick={onDisableDeveloperMode}>
              <LogOut size={18} />
              Turn Off
            </button>
          </>
        ) : (
          <form className="settings-form" onSubmit={submit}>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Developer password"
              type="password"
            />
            <button className="primary-button" disabled={!password.trim()}>
              Unlock
            </button>
          </form>
        )}
        {error ? <div className="settings-error">{error}</div> : null}
      </section>
    </div>
  );
}

function InviteRow({ invite }) {
  const link = `${window.location.origin}/invite/${invite.token}`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link);
    } catch {
      window.prompt("Copy invite link", link);
    }
  };

  return (
    <button className="invite-row" onClick={copy}>
      <span>
        <strong>{invite.bracket_title}</strong>
        <small>{invite.submitted ? "Submitted" : "Not submitted"}</small>
      </span>
      <em>{invite.submitted && invite.bracket ? invite.bracket.slug : "Copy link"}</em>
    </button>
  );
}

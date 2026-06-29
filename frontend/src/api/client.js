async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const text = await response.text();
  let payload = {};
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { error: summarizeErrorText(text) };
  }
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function summarizeErrorText(text) {
  if (!text) return "Request failed";
  const title = text.match(/<title>(.*?)<\/title>/is)?.[1];
  const message = title || text;
  return message
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
}

export function getTournament(refresh = false) {
  return request(`/matches/${refresh ? "?refresh=1" : ""}`);
}

export function syncEspn() {
  return request("/sync-espn/", { method: "POST" });
}

export function enableDeveloperMode(password) {
  return request("/developer-mode/", {
    method: "POST",
    body: JSON.stringify({ password })
  });
}

export function createInvite(bracketTitle, developerToken) {
  return request("/invites/", {
    method: "POST",
    body: JSON.stringify({
      bracket_title: bracketTitle,
      developer_token: developerToken
    })
  });
}

export function getInvites(developerToken) {
  return request("/invites/", {
    headers: {
      "Content-Type": "application/json",
      "X-Developer-Token": developerToken
    }
  });
}

export function setSubmissionsLocked(submissionsLocked, developerToken) {
  return request("/submissions-lock/", {
    method: "PUT",
    body: JSON.stringify({
      submissions_locked: submissionsLocked,
      developer_token: developerToken
    })
  });
}

export function exportData(developerToken) {
  return request("/data/export/", {
    headers: {
      "Content-Type": "application/json",
      "X-Developer-Token": developerToken
    }
  });
}

export function importData(data, developerToken) {
  return request("/data/import/", {
    method: "POST",
    body: JSON.stringify({ ...data, developer_token: developerToken })
  });
}

export function getLeaderboard() {
  return request("/leaderboard/");
}

export function getBrackets() {
  return request("/brackets/");
}

export function createBracket(title, picks) {
  return request("/brackets/", {
    method: "POST",
    body: JSON.stringify({ title, picks })
  });
}

export function getBracket(slug, editToken = "", developerToken = "") {
  const query = editToken ? `?edit_token=${encodeURIComponent(editToken)}` : "";
  return request(`/brackets/${slug}/${query}`, {
    headers: {
      "Content-Type": "application/json",
      "X-Developer-Token": developerToken
    }
  });
}

export function updateBracket(slug, title, picks, editToken = "", developerToken = "") {
  return request(`/brackets/${slug}/`, {
    method: "PUT",
    body: JSON.stringify({ title, picks, edit_token: editToken, developer_token: developerToken })
  });
}

export function deleteBracket(slug, editToken = "", developerToken = "") {
  return request(`/brackets/${slug}/`, {
    method: "DELETE",
    body: JSON.stringify({ edit_token: editToken, developer_token: developerToken })
  });
}

export function getInvite(token, deviceKey) {
  return request(`/invites/${token}/?device_key=${encodeURIComponent(deviceKey)}`);
}

export function submitInvite(token, title, picks, deviceKey) {
  return request(`/invites/${token}/`, {
    method: "POST",
    body: JSON.stringify({ title, picks, device_key: deviceKey })
  });
}

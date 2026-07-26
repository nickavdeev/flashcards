const API = "/api/v1";

export async function apiGet(path) {
  const res = await fetch(`${API}/${path}`);
  return res.json();
}

export async function apiPost(path) {
  const res = await fetch(`${API}/${path}`, { method: "POST" });
  return res.json();
}

export function getDeckIdFromPath() {
  const match = window.location.pathname.match(/^\/deck\/(\d+)$/);

  if (!match) {
    throw new Error(`Could not extract deck ID from path: ${window.location.pathname}`);
  }

  return Number(match[1]);
}

const API = "/api/v1";

export async function apiGet(path) {
  const res = await fetch(`${API}/${path}`);
  return res.json();
}

export async function apiPost(path, body = {}) {
  const res = await fetch(`${API}/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

export function getDeckIdFromPath() {
  const match = window.location.pathname.match(/^\/deck\/(\d+)$/);

  if (!match) {
    throw new Error(`Could not extract deck ID from path: ${window.location.pathname}`);
  }

  return Number(match[1]);
}

export async function sendCode(email) {
  const response = await apiPost(`request-code`, {
    email: email,
  });
  if (response.ok) {
    alert("Verification code sent! Please check your email.");
  } else {
    alert(response.message || "Failed to send code. Please try again.");
  }
}

export async function verifyCode(email, code) {
  const response = await apiPost(`login`, {
    email: email,
    code: code,
  });
  if (response.ok) {
    window.location.href = "/";
  } else {
    alert(response.message || "Verification failed. Please try again.");
  }
}

export async function logout() {
  const response = await apiPost(`logout`);
  if (response.ok) {
    alert("Logged out successfully! Redirecting to the main page...");
    window.location.href = "/";
  } else {
    alert(response.message || "Logout failed. Please try again.");
  }
}

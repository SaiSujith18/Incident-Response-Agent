const API_BASE_URL = "http://127.0.0.1:8000";

async function request(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail || `Request failed with status ${response.status}`
    );
  }

  return data;
}

// Analyze current incident
export async function analyzeIncident(incident) {
  return request("/analyze", {
    method: "POST",
    body: JSON.stringify({
      incident,
    }),
  });
}

// Detect patterns from historical incidents
export async function detectPatterns(incident) {
  return request("/patterns", {
    method: "POST",
    body: JSON.stringify({
      incident,
    }),
  });
}

// Store incident resolution
export async function resolveIncident(data) {
  return request("/resolve", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Store postmortem
export async function createPostmortem(data) {
  return request("/postmortem", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
function extractErrorMessage(payload) {
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg || JSON.stringify(item)).join("; ");
  }
  return payload?.detail || payload?.message || "请求失败，请稍后重试。";
}

export async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    throw new Error(extractErrorMessage(payload));
  }

  return payload;
}

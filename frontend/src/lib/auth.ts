/**
 * Fetch wrapper for the API's HttpOnly cookie session.
 */
export async function apiFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const mergedHeaders = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (options.body && !isFormData && !mergedHeaders.has("Content-Type")) {
    mergedHeaders.set("Content-Type", "application/json");
  }
  return fetch(url, {
    ...options,
    headers: mergedHeaders,
    credentials: "include",
  });
}

export async function apiErrorMessage(
  response: Response,
  fallback = "The request could not be completed."
): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail)) {
      return body.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(" ") || fallback;
    }
  } catch {
    // The server did not return JSON.
  }
  return fallback;
}

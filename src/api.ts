// All browser requests use the same /api prefix and session cookie.
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

let guestRefresh: Promise<void> | null = null;

async function renewGuestSession() {
  if (!guestRefresh) {
    guestRefresh = fetch("/api/auth/guest", {
      method: "POST",
      credentials: "same-origin",
    }).then(async (response) => {
      if (!response.ok) throw new Error("Could not restore your guest session. Please refresh the page.");
    }).finally(() => { guestRefresh = null; });
  }
  return guestRefresh;
}

export async function api<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const request = () => fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers:
      options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json", ...options.headers },
  });
  let r = await request();
  if (r.status === 401 && !path.startsWith("/auth/")) {
    await renewGuestSession();
    r = await request();
  }
  if (!r.ok) {
    const text = await r.text();
    let message = text;
    try {
      const j = JSON.parse(text);
      message =
        typeof j.detail === "string"
          ? j.detail
          : j.detail?.[0]?.msg || "Please try again.";
    } catch {}
    throw new ApiError(message, r.status);
  }
  return r.json();
}
export const post = (body?: unknown) => ({
  method: "POST",
  body: body ? JSON.stringify(body) : undefined,
});

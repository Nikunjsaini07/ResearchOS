// All browser requests use the same /api prefix and session cookie.
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
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
  const r = await request();
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

export class APIError extends Error {
  constructor(
    public code: string,
    public status = 0,
  ) {
    super(code);
  }
}
export async function request<T>(
  path: string,
  context?: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...options,
      credentials: "same-origin",
      signal: options.signal ?? AbortSignal.timeout(10000),
      headers: {
        "Content-Type": "application/json",
        ...(context ? { "X-Context-ID": context } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new APIError("NETWORK");
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(error.error?.code ?? "NETWORK", response.status);
  }
  return response.json();
}

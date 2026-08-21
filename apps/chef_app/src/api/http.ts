import { TokenStore } from "../auth/tokenStore";

export interface ApiErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    details?: unknown;
  };
  request_id?: string | null;
  detail?: unknown;
}

export class ApiClientError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
    readonly requestId?: string | null,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

interface Options extends RequestInit {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
}

export class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;

  constructor(
    private readonly baseUrl: string,
    private readonly tokens: TokenStore,
    private readonly fetchImpl: typeof fetch = fetch,
  ) {}

  async request<T>(path: string, options: Options = {}): Promise<T> {
    const { auth = true, retryOnUnauthorized = true, headers, ...rest } = options;
    const h = new Headers(headers);
    h.set("Accept", "application/json");
    if (rest.body && typeof rest.body === "string") {
      h.set("Content-Type", "application/json");
    }

    if (auth) {
      const pair = await this.tokens.get();
      if (pair?.accessToken) h.set("Authorization", `Bearer ${pair.accessToken}`);
    }

    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, { ...rest, headers: h });
    } catch (error) {
      throw new ApiClientError(
        0,
        "network_error",
        "تعذر الاتصال بخادم بيتنا. تأكد أن الـ Backend شغال وأن الهاتف والكمبيوتر على نفس الشبكة.",
        error,
      );
    }

    if (
      response.status === 401 &&
      auth &&
      retryOnUnauthorized &&
      await this.refresh()
    ) {
      return this.request<T>(path, { ...options, retryOnUnauthorized: false });
    }

    if (!response.ok) {
      throw await this.toApiError(response);
    }

    if (response.status === 204) return undefined as T;

    try {
      return await response.json() as T;
    } catch (error) {
      throw new ApiClientError(
        response.status,
        "invalid_json_response",
        "الخادم أعاد استجابة غير متوقعة.",
        error,
        response.headers.get("x-request-id"),
      );
    }
  }

  resolveTransferUrl(url: string) {
    return /^https?:\/\//i.test(url)
      ? url
      : `${this.baseUrl}${url.startsWith("/") ? url : `/${url}`}`;
  }

  async refresh(): Promise<boolean> {
    if (this.refreshPromise) return this.refreshPromise;
    this.refreshPromise = this.doRefresh();
    try {
      return await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async doRefresh(): Promise<boolean> {
    const pair = await this.tokens.get();
    if (!pair) return false;

    try {
      const response = await this.fetchImpl(`${this.baseUrl}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: pair.refreshToken }),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          await this.tokens.clear();
        }
        return false;
      }

      const body = await response.json() as {
        access_token: string;
        refresh_token: string;
      };
      await this.tokens.set({
        accessToken: body.access_token,
        refreshToken: body.refresh_token,
      });
      return true;
    } catch {
      // A temporary network failure must not destroy a valid local session.
      return false;
    }
  }

  private async toApiError(response: Response): Promise<ApiClientError> {
    let raw: ApiErrorEnvelope | null = null;
    try {
      raw = await response.json() as ApiErrorEnvelope;
    } catch {
      raw = null;
    }

    const code = raw?.error?.code?.trim() || `http_${response.status}`;
    const message =
      raw?.error?.message?.trim() ||
      this.fastApiDetailMessage(raw?.detail) ||
      `HTTP ${response.status}`;
    const details = raw?.error?.details ?? raw?.detail;
    const requestId =
      raw?.request_id ?? response.headers.get("x-request-id") ?? null;

    return new ApiClientError(
      response.status,
      code,
      message,
      details,
      requestId,
    );
  }

  private fastApiDetailMessage(detail: unknown): string | null {
    if (typeof detail === "string" && detail.trim()) return detail.trim();
    if (!Array.isArray(detail)) return null;

    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const msg = (item as { msg?: unknown }).msg;
        return typeof msg === "string" ? msg.trim() : null;
      })
      .filter((value): value is string => Boolean(value));

    return messages.length ? messages.join(" • ") : null;
  }
}

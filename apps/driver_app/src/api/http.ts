import { TokenStore } from "../auth/tokenStore";

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: unknown;
    request_id?: string | null;
  };
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
  }
}

interface Options extends RequestInit {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
}

export class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;

  constructor(
    readonly baseUrl: string,
    private readonly tokens: TokenStore,
    private readonly fetchImpl: typeof fetch = fetch,
  ) {}

  async request<T>(path: string, options: Options = {}): Promise<T> {
    const { auth = true, retryOnUnauthorized = true, headers, ...rest } = options;
    const h = new Headers(headers);
    h.set("Accept", "application/json");
    if (rest.body && typeof rest.body === "string") h.set("Content-Type", "application/json");

    if (auth) {
      const pair = await this.tokens.get();
      if (pair?.accessToken) h.set("Authorization", `Bearer ${pair.accessToken}`);
    }

    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {...rest, headers:h});

    if (response.status === 401 && auth && retryOnUnauthorized && await this.refresh()) {
      return this.request<T>(path, {...options, retryOnUnauthorized:false});
    }

    if (!response.ok) {
      let envelope: ApiErrorEnvelope = {
        error: {code:"http_error", message:`HTTP ${response.status}`},
      };
      try { envelope = await response.json() as ApiErrorEnvelope; } catch {}
      throw new ApiClientError(
        response.status,
        envelope.error.code,
        envelope.error.message,
        envelope.error.details,
        envelope.error.request_id,
      );
    }

    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  }

  resolveTransferUrl(url: string) {
    if (/^https?:\/\//i.test(url)) return url;
    return `${this.baseUrl}${url.startsWith("/") ? url : `/${url}`}`;
  }

  async refresh() {
    if (this.refreshPromise) return this.refreshPromise;
    this.refreshPromise = this.doRefresh();
    try { return await this.refreshPromise; }
    finally { this.refreshPromise = null; }
  }

  private async doRefresh() {
    const pair = await this.tokens.get();
    if (!pair) return false;

    const response = await this.fetchImpl(`${this.baseUrl}/api/v1/auth/refresh`, {
      method:"POST",
      headers:{"Content-Type":"application/json","Accept":"application/json"},
      body:JSON.stringify({refresh_token:pair.refreshToken}),
    });

    if (!response.ok) {
      await this.tokens.clear();
      return false;
    }

    const body = await response.json() as {
      access_token:string;
      refresh_token:string;
    };
    await this.tokens.set({
      accessToken:body.access_token,
      refreshToken:body.refresh_token,
    });
    return true;
  }
}

import * as SecureStore from "expo-secure-store";

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}
export interface TokenStore {
  get(): Promise<AuthTokens | null>;
  set(tokens: AuthTokens): Promise<void>;
  clear(): Promise<void>;
}

const ACCESS = "baytna_chef_access_token";
const REFRESH = "baytna_chef_refresh_token";

export class SecureTokenStore implements TokenStore {
  async get(): Promise<AuthTokens | null> {
    const [accessToken, refreshToken] = await Promise.all([
      SecureStore.getItemAsync(ACCESS),
      SecureStore.getItemAsync(REFRESH),
    ]);
    return accessToken && refreshToken ? { accessToken, refreshToken } : null;
  }

  async set(tokens: AuthTokens) {
    await Promise.all([
      SecureStore.setItemAsync(ACCESS, tokens.accessToken),
      SecureStore.setItemAsync(REFRESH, tokens.refreshToken),
    ]);
  }

  async clear() {
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS),
      SecureStore.deleteItemAsync(REFRESH),
    ]);
  }
}

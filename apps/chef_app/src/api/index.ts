import { config } from "../config/env";
import { SecureTokenStore } from "../auth/tokenStore";
import { ApiClient } from "./http";
import { ChefApi } from "./chef";

export const tokenStore = new SecureTokenStore();
export const http = new ApiClient(config.apiBaseUrl, tokenStore);
export const chefApi = new ChefApi(http, tokenStore);

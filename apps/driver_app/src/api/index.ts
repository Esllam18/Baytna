import { config } from "../config/env";
import { SecureTokenStore } from "../auth/tokenStore";
import { ApiClient } from "./http";
import { DriverApi } from "./driver";

export const tokenStore=new SecureTokenStore();
export const http=new ApiClient(config.apiBaseUrl,tokenStore);
export const driverApi=new DriverApi(http,tokenStore);

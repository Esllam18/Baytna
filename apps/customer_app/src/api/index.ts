import { config } from "../config/env"; import { SecureTokenStore } from "../auth/tokenStore"; import { ApiClient } from "./http"; import { CustomerApi } from "./customer";
export const tokenStore=new SecureTokenStore(); export const http=new ApiClient(config.apiBaseUrl,tokenStore); export const customerApi=new CustomerApi(http,tokenStore);

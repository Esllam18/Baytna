import { ApiErrorEnvelope } from "./types"; import { TokenStore } from "../auth/tokenStore";
export class ApiClientError extends Error { constructor(public status:number, public envelope:ApiErrorEnvelope){ super(envelope.error.message); } get code(){return this.envelope.error.code;} get requestId(){return this.envelope.error.request_id;} }
interface RequestOptions extends RequestInit { auth?: boolean; retryOnUnauthorized?: boolean; }
export class ApiClient {
  private refreshPromise: Promise<boolean> | null = null;
  constructor(private baseUrl:string, private tokenStore:TokenStore, private fetchImpl:typeof fetch = fetch) {}
  private url(path:string){ return `${this.baseUrl}${path.startsWith('/')?path:`/${path}`}`; }
  async request<T>(path:string, options:RequestOptions={}):Promise<T>{
    const {auth=true,retryOnUnauthorized=true,headers,...rest}=options; const h=new Headers(headers); h.set('Accept','application/json'); if(rest.body && typeof rest.body==='string' && !h.has('Content-Type')) h.set('Content-Type','application/json');
    if(auth){ const tokens=await this.tokenStore.get(); if(tokens?.accessToken) h.set('Authorization',`Bearer ${tokens.accessToken}`); }
    const response=await this.fetchImpl(this.url(path), {...rest, headers:h});
    if(response.status===401 && auth && retryOnUnauthorized && await this.refreshAccessToken()) return this.request<T>(path,{...options,retryOnUnauthorized:false});
    if(!response.ok){ let envelope:ApiErrorEnvelope; try{ envelope=await response.json() as ApiErrorEnvelope; }catch{ envelope={error:{code:'http_error',message:`Request failed with status ${response.status}`}};} throw new ApiClientError(response.status,envelope); }
    if(response.status===204) return undefined as T; return await response.json() as T;
  }
  resolveTransferUrl(path:string){ return /^https?:\/\//i.test(path)?path:this.url(path); }
  async refreshAccessToken(){ if(this.refreshPromise) return this.refreshPromise; this.refreshPromise=this.doRefresh(); try{return await this.refreshPromise;} finally{this.refreshPromise=null;} }
  private async doRefresh(){ const tokens=await this.tokenStore.get(); if(!tokens?.refreshToken) return false; const r=await this.fetchImpl(this.url('/api/v1/auth/refresh'),{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({refresh_token:tokens.refreshToken})}); if(!r.ok){await this.tokenStore.clear(); return false;} const body=await r.json() as {access_token:string;refresh_token:string}; await this.tokenStore.set({accessToken:body.access_token,refreshToken:body.refresh_token}); return true; }
}

import {config} from "../config";
import {tokenStore} from "../auth/tokenStore";

export class ApiError extends Error {
  constructor(readonly status:number,readonly code:string,message:string){super(message)}
}

export async function request<T>(
  path:string,
  options:RequestInit & {auth?:boolean;retry?:boolean}={}
):Promise<T>{
  const {auth=true,retry=true,...rest}=options;
  const headers=new Headers(rest.headers);
  headers.set("Accept","application/json");
  if(typeof rest.body==="string")headers.set("Content-Type","application/json");
  if(auth){
    const pair=tokenStore.get();
    if(pair)headers.set("Authorization",`Bearer ${pair.accessToken}`);
  }

  const res=await fetch(`${config.apiBaseUrl}${path}`,{...rest,headers});
  if(res.status===401&&auth&&retry&&await refresh()){
    return request<T>(path,{...options,retry:false});
  }
  if(!res.ok){
    let code="http_error",message=`HTTP ${res.status}`;
    try{
      const body=await res.json() as {error?:{code?:string;message?:string}};
      code=body.error?.code??code;message=body.error?.message??message;
    }catch{}
    throw new ApiError(res.status,code,message);
  }
  if(res.status===204)return undefined as T;
  return await res.json() as T;
}

let refreshing:Promise<boolean>|null=null;
async function refresh(){
  if(refreshing)return refreshing;
  refreshing=(async()=>{
    const pair=tokenStore.get();
    if(!pair)return false;
    const res=await fetch(`${config.apiBaseUrl}/api/v1/auth/refresh`,{
      method:"POST",
      headers:{"Content-Type":"application/json","Accept":"application/json"},
      body:JSON.stringify({refresh_token:pair.refreshToken}),
    });
    if(!res.ok){tokenStore.clear();return false}
    const body=await res.json() as {access_token:string;refresh_token:string};
    tokenStore.set({accessToken:body.access_token,refreshToken:body.refresh_token});
    return true;
  })();
  try{return await refreshing}finally{refreshing=null}
}

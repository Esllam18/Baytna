export interface Tokens {accessToken:string;refreshToken:string}
const KEY="baytna_admin_session";

export const tokenStore={
  get():Tokens|null{
    const raw=sessionStorage.getItem(KEY);
    if(!raw)return null;
    try{return JSON.parse(raw) as Tokens}catch{return null}
  },
  set(tokens:Tokens){sessionStorage.setItem(KEY,JSON.stringify(tokens))},
  clear(){sessionStorage.removeItem(KEY)},
};

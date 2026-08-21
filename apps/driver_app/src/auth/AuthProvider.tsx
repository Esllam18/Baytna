import React,{createContext,useContext,useEffect,useState} from "react";
import { driverApi, tokenStore } from "../api";
import { queryClient } from "../query/queryClient";

type Value={ready:boolean;authenticated:boolean;reload():Promise<void>;signOut():Promise<void>};
const Context=createContext<Value|null>(null);

export function AuthProvider({children}:{children:React.ReactNode}) {
  const [ready,setReady]=useState(false);
  const [authenticated,setAuthenticated]=useState(false);

  const reload=async()=>{
    const pair=await tokenStore.get();
    if(!pair){setAuthenticated(false);setReady(true);return;}
    try{await driverApi.profile();setAuthenticated(true);}
    catch{await tokenStore.clear();setAuthenticated(false);}
    finally{setReady(true);}
  };

  const signOut=async()=>{
    await driverApi.logout();
    queryClient.clear();
    setAuthenticated(false);
  };

  useEffect(()=>{void reload();},[]);
  return <Context.Provider value={{ready,authenticated,reload,signOut}}>{children}</Context.Provider>;
}

export function useAuth(){
  const value=useContext(Context);
  if(!value)throw new Error("AuthProvider missing");
  return value;
}

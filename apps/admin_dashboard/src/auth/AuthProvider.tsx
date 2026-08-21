import React,{createContext,useContext,useEffect,useState} from "react";
import {useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {tokenStore} from "./tokenStore";

type AuthValue={ready:boolean;authenticated:boolean;reload():Promise<void>;signOut():Promise<void>};
const Context=createContext<AuthValue|null>(null);

export function AuthProvider({children}:{children:React.ReactNode}){
  const [ready,setReady]=useState(false);
  const [authenticated,setAuthenticated]=useState(false);
  const qc=useQueryClient();

  const reload=async()=>{
    if(!tokenStore.get()){setAuthenticated(false);setReady(true);return}
    try{await adminApi.profile();setAuthenticated(true)}
    catch{tokenStore.clear();setAuthenticated(false)}
    finally{setReady(true)}
  };

  const signOut=async()=>{
    await adminApi.logout();
    qc.clear();
    setAuthenticated(false);
  };

  useEffect(()=>{void reload()},[]);
  return <Context.Provider value={{ready,authenticated,reload,signOut}}>{children}</Context.Provider>;
}

export function useAuth(){
  const v=useContext(Context);
  if(!v)throw new Error("AuthProvider missing");
  return v;
}

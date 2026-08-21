import React from "react";
import { Redirect } from "expo-router";
import { useAuth } from "../src/auth/AuthProvider";
import { Screen } from "../src/ui/Screen";
import { LoadingState } from "../src/ui/StateViews";

export default function Index(){
  const auth=useAuth();
  if(!auth.ready)return <Screen><LoadingState label="بنفتح تطبيق مندوب بيتنا..."/></Screen>;
  return <Redirect href={auth.authenticated?"/home":"/auth/login"}/>;
}

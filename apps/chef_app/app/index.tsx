import React from "react";
import { Redirect } from "expo-router";
import { LoadingState } from "../src/ui/StateViews";
import { Screen } from "../src/ui/Screen";
import { useAuth } from "../src/auth/AuthProvider";

export default function Index() {
  const auth=useAuth();
  if (!auth.ready) return <Screen><LoadingState label="بنفتح تطبيق شريك بيتنا..."/></Screen>;
  return <Redirect href={auth.authenticated?"/home":"/auth/login"}/>;
}

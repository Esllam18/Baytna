import React from "react";
import {NavLink,Outlet} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {useAuth} from "../auth/AuthProvider";

const nav=[
  ["/launch-command","🚦","Launch Command"],
  ["/post-launch","◈","Post-Launch"],
  ["/control-room","⚡","غرفة العمليات"],
  ["/pilot","◉","استقرار الطيار"],
  ["/economics","₤","اقتصاديات التوسع"],
  ["/finance-automation","↻","التسويات والاستيراد"],
  ["/vendor-accounting","✓","مراجعة الموردين"],
  ["/traffic-governance","⇄","Traffic Governance"],
  ["/","⌂","الرئيسية"],
  ["/orders","▤","الطلبات"],
  ["/chefs","👩‍🍳","الشيفات"],
  ["/drivers","🛵","المندوبون"],
  ["/support","💬","الدعم"],
  ["/finance","◫","المالية"],
  ["/audit","≣","سجل التدقيق"],
] as const;

export function AppShell(){
  const auth=useAuth();
  const profile=useQuery({queryKey:keys.profile,queryFn:()=>adminApi.profile()});
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">🏠</div><div><b>بيتنا</b><span>لوحة الإدارة</span></div></div>
      <nav>{nav.map(([href,icon,label])=><NavLink key={href} to={href} end={href==="/"} className={({isActive})=>isActive?"active":""}><span>{icon}</span>{label}</NavLink>)}</nav>
      <div className="sidebar-bottom">
        <div className="admin-id"><strong>Admin</strong><span>{profile.data?.phone??"..."}</span></div>
        <button className="ghost danger-text" onClick={()=>void auth.signOut()}>تسجيل الخروج</button>
      </div>
    </aside>
    <main className="content"><Outlet/></main>
  </div>;
}

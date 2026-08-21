import React,{useState} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,MetricCard,PageTitle,StatusBadge} from "../components/Ui";

const statuses=["","new","assigned","investigating","awaiting_customer","awaiting_internal","resolved","closed"];

export function SupportPage(){
  const [status,setStatus]=useState("");
  const summary=useQuery({queryKey:keys.support,queryFn:()=>adminApi.supportSummary(),refetchInterval:20_000});
  const tickets=useQuery({queryKey:keys.tickets(status),queryFn:()=>adminApi.tickets(status||undefined),refetchInterval:20_000});

  return <>
    <PageTitle title="الدعم والمساعدة" subtitle="تذاكر العملاء وأولوية المتابعة"/>
    <div className="metrics-grid compact">
      <MetricCard label="مفتوحة" value={summary.data?.total_open??0}/>
      <MetricCard label="جديدة" value={summary.data?.new??0} tone="orange"/>
      <MetricCard label="عاجلة" value={summary.data?.urgent_open??0} tone={summary.data?.urgent_open?"danger":undefined}/>
      <MetricCard label="غير معيّنة" value={summary.data?.unassigned_open??0}/>
    </div>
    <div className="toolbar"><select value={status} onChange={e=>setStatus(e.target.value)}>{statuses.map(x=><option key={x} value={x}>{x||"كل الحالات"}</option>)}</select><span>{tickets.data?.length??0} تذكرة</span></div>
    {tickets.isLoading?<Loading/>:tickets.isError?<ErrorBox/>:tickets.data?.length?
      <div className="ticket-list">{tickets.data.map(t=><Link to={`/support/${t.id}`} className={`ticket-card priority-${t.priority}`} key={t.id}>
        <div className="ticket-main"><strong>{t.subject}</strong><span>{t.category} • {new Date(t.created_at).toLocaleString("ar-EG")}</span><p>{t.description}</p></div>
        <div className="ticket-side"><StatusBadge value={t.status}/><span className={`priority p-${t.priority}`}>{t.priority}</span></div>
      </Link>)}</div>:<Empty title="مفيش تذاكر بالحالة دي"/>}
  </>;
}

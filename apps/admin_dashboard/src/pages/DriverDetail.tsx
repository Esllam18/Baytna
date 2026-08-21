import React from "react";
import {useParams} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,MetricCard,PageTitle,StatusBadge} from "../components/Ui";

export function DriverDetailPage(){
  const {driverId=""}=useParams();
  const q=useQuery({queryKey:keys.driver(driverId),queryFn:()=>adminApi.driver(driverId),enabled:Boolean(driverId)});
  if(q.isLoading)return <Loading/>;if(q.isError||!q.data)return <ErrorBox message="المندوب غير موجود."/>;
  const d=q.data;
  return <>
    <PageTitle title={`مندوب #${d.id.slice(0,8).toUpperCase()}`} subtitle="تفاصيل التشغيل" action={<StatusBadge value={d.status}/>}/>
    <div className="metrics-grid compact">
      <MetricCard label="التقييم" value={`★ ${d.rating.toFixed(1)}`}/>
      <MetricCard label="إجمالي المهام" value={d.total_missions}/>
      <MetricCard label="تم التوصيل" value={d.delivered_missions} tone="green"/>
      <MetricCard label="مهام بمشاكل" value={d.issue_missions} tone={d.issue_missions?"danger":undefined}/>
    </div>
    <section className="panel"><h2>المهمة الحالية</h2>
      {d.current_mission?<div className="json-card"><div className="kv"><span>المهمة</span><strong>{String(d.current_mission.id??"")}</strong></div><div className="kv"><span>الطلب</span><strong>{String(d.current_mission.order_id??"")}</strong></div><div className="kv"><span>الحالة</span><StatusBadge value={String(d.current_mission.status??"")}/></div>{d.current_mission.issue_code?<div className="kv"><span>مشكلة</span><strong className="danger-text">{String(d.current_mission.issue_code)}</strong></div>:null}</div>:<p className="muted">لا توجد مهمة نشطة.</p>}
    </section>
  </>;
}

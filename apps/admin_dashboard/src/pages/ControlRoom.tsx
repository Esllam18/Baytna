import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "../api/admin";
import type { OperationsIncident } from "../api/types";
import { keys } from "../query";
import {
  Empty,
  ErrorBox,
  Loading,
  MetricCard,
  Money,
  PageTitle,
  StatusBadge,
} from "../components/Ui";

const severityLabel: Record<string,string> = {
  critical:"حرج",
  high:"عالي",
  warning:"تحذير",
  info:"معلومة",
};

const categoryLabel: Record<string,string> = {
  chef_sla:"SLA الشيف",
  delivery_sla:"SLA التوصيل",
  support_sla:"SLA الدعم",
  payment:"المدفوعات",
  reliability:"Reliability",
  notifications:"الإشعارات",
};

export function ControlRoomPage() {
  const qc=useQueryClient();
  const [severity,setSeverity]=useState("");
  const [status,setStatus]=useState("active");

  const refresh=useMutation({
    mutationFn:()=>adminApi.refreshControlRoom(),
    onSuccess:async()=> {
      await Promise.all([
        qc.invalidateQueries({queryKey:keys.controlRoom}),
        qc.invalidateQueries({queryKey:keys.incidents}),
        qc.invalidateQueries({queryKey:keys.dailyBrief}),
      ]);
    },
  });

  const overview=useQuery({
    queryKey:keys.controlRoom,
    queryFn:()=>adminApi.controlRoomOverview(),
    refetchInterval:30_000,
  });
  const brief=useQuery({
    queryKey:keys.dailyBrief,
    queryFn:()=>adminApi.dailyBrief(),
    refetchInterval:60_000,
  });
  const incidents=useQuery({
    queryKey:[...keys.incidents,status,severity],
    queryFn:async()=>{
      if(status==="active"){
        const [open,ack]=await Promise.all([
          adminApi.incidents({status:"open",severity:severity||undefined}),
          adminApi.incidents({status:"acknowledged",severity:severity||undefined}),
        ]);
        return [...open,...ack].sort(sortIncident);
      }
      return adminApi.incidents({
        status:status||undefined,
        severity:severity||undefined,
      });
    },
    refetchInterval:30_000,
  });

  useEffect(()=>{
    void refresh.mutateAsync().catch(()=>undefined);
    const timer=window.setInterval(()=>{
      void refresh.mutateAsync().catch(()=>undefined);
    },60_000);
    return()=>window.clearInterval(timer);
  },[]);

  if(overview.isLoading)return <Loading label="بنجهز غرفة العمليات..."/>;
  if(overview.isError||!overview.data)return <ErrorBox message="تعذر تحميل غرفة العمليات."/>;
  const o=overview.data,k=o.kpis;

  return <>
    <PageTitle
      title="غرفة العمليات"
      subtitle={`آخر تحديث ${new Date(o.generated_at).toLocaleTimeString("ar-EG")} • Worker: ${o.worker_status}`}
      action={
        <button
          className="primary"
          disabled={refresh.isPending}
          onClick={()=>refresh.mutate()}
        >
          {refresh.isPending?"جاري الفحص...":"فحص الآن"}
        </button>
      }
    />

    <div className={`control-health health-${o.health}`}>
      <div>
        <span>الحالة التشغيلية</span>
        <strong>{o.health==="red"?"RED — تدخل فوري":o.health==="amber"?"AMBER — متابعة":"GREEN — مستقرة"}</strong>
      </div>
      <div className="health-counts">
        <b>{o.critical_incidents}</b><span>حرج</span>
        <b>{o.high_incidents}</b><span>عالي</span>
        <b>{o.unacknowledged_incidents}</b><span>غير مستلم</span>
      </div>
    </div>

    <div className="metrics-grid compact">
      <MetricCard label="طلبات 7 أيام" value={k.orders_created} note={`${k.delivered_orders} delivered`} tone="orange"/>
      <MetricCard label="نجاح التوصيل" value={`${k.delivery_success_rate_pct}%`} note="مؤشر تشغيلي منفصل" tone={k.delivery_success_rate_pct>=95?"green":undefined}/>
      <MetricCard label="الإلغاء" value={`${k.cancellation_rate_pct}%`} note="الهدف <5%" tone={k.launch_target_cancellation_met?"green":"danger"}/>
      <MetricCard label="Repeat" value={`${k.repeat_customer_rate_pct}%`} note="الهدف ≥40%" tone={k.launch_target_repeat_met?"green":"danger"}/>
      <MetricCard label="تقييم الشيف" value={k.reviews_count?k.average_chef_rating.toFixed(2):"—"} note="الهدف ≥4.7" tone={k.launch_target_rating_met?"green":undefined}/>
      <MetricCard label="GMV" value={<Money minor={k.gmv_minor}/>} note="طلبات delivered"/>
    </div>

    <div className="control-grid">
      <section className="panel">
        <div className="panel-head">
          <div><h2>الحوادث النشطة</h2><p>SLA + Reliability + Payments + Notifications</p></div>
          <div className="incident-filters">
            <select value={severity} onChange={e=>setSeverity(e.target.value)}>
              <option value="">كل الخطورة</option>
              <option value="critical">critical</option>
              <option value="high">high</option>
              <option value="warning">warning</option>
            </select>
            <select value={status} onChange={e=>setStatus(e.target.value)}>
              <option value="active">نشطة</option>
              <option value="open">غير مستلمة</option>
              <option value="acknowledged">مستلمة</option>
              <option value="resolved">محلولة</option>
              <option value="">الكل</option>
            </select>
          </div>
        </div>

        {incidents.isLoading?<Loading/>:incidents.isError?<ErrorBox/>:
          incidents.data?.length?
          <div className="incident-list">
            {incidents.data.map(i=><IncidentCard key={i.id} incident={i} onChanged={async()=>{
              await Promise.all([
                qc.invalidateQueries({queryKey:keys.controlRoom}),
                qc.invalidateQueries({queryKey:keys.incidents}),
                qc.invalidateQueries({queryKey:keys.dailyBrief}),
              ]);
            }}/>)}
          </div>
          :<Empty title="مفيش حوادث بالحالة دي" body="الفحص التلقائي مستمر كل دقيقة."/>}
      </section>

      <section className="panel">
        <h2>Daily Brief</h2>
        {brief.isLoading?<Loading/>:brief.isError||!brief.data?<ErrorBox/>:<>
          <div className="brief-grid">
            <SmallMetric label="طلبات اليوم" value={brief.data.opening_orders}/>
            <SmallMetric label="تم توصيلها" value={brief.data.delivered_orders}/>
            <SmallMetric label="مندوب متاح" value={brief.data.available_drivers}/>
            <SmallMetric label="مطبخ مفتوح" value={brief.data.open_chefs}/>
          </div>
          <h3 className="ops-subtitle">أولوية اليوم</h3>
          <div className="action-list">
            {brief.data.actions.length?brief.data.actions.map((a,index)=>
              a.route?<Link to={a.route} key={`${a.title}-${index}`} className={`action action-${a.priority}`}>
                <strong>{a.title}</strong><span>{a.detail}</span>
              </Link>:<div key={`${a.title}-${index}`} className={`action action-${a.priority}`}>
                <strong>{a.title}</strong><span>{a.detail}</span>
              </div>
            ):<div className="all-clear">لا توجد إجراءات عاجلة مسجلة.</div>}
          </div>
        </>}
      </section>
    </div>

    <section className="panel">
      <h2>Launch KPI Gates</h2>
      <div className="gate-grid">
        <Gate label="Rating ≥ 4.7" met={k.launch_target_rating_met} value={k.reviews_count?k.average_chef_rating.toFixed(2):"لا توجد عينة"}/>
        <Gate label="Repeat ≥ 40%" met={k.launch_target_repeat_met} value={`${k.repeat_customer_rate_pct}%`}/>
        <Gate label="On-time ≥ 95%" met={k.launch_target_on_time_met} value={k.on_time_delivery_rate_pct===null?`Coverage ${k.delivery_promise_coverage_pct}%`:`${k.on_time_delivery_rate_pct}% • Coverage ${k.delivery_promise_coverage_pct}%`}/>
        <Gate label="Cancellation < 5%" met={k.launch_target_cancellation_met} value={`${k.cancellation_rate_pct}%`}/>
      </div>
      <div className="ops-counters">
        <span>Chef SLA breaches <b>{k.chef_acceptance_sla_breaches}</b></span>
        <span>Support SLA breaches <b>{k.support_sla_breaches}</b></span>
        <span>Payment reconciliation <b>{k.payment_reconciliation_open}</b></span>
        <span>Notification DLQ <b>{k.notification_dead_letters}</b></span>
        <span>Outbox DLQ <b>{k.outbox_dead_letters}</b></span>
        <span>Job DLQ <b>{k.background_job_dead_letters}</b></span>
        <span>Promise coverage <b>{k.delivery_promise_coverage_pct}%</b></span>
        <span>Late deliveries <b>{k.late_deliveries}</b></span>
      </div>
    </section>
  </>;
}

function IncidentCard({incident,onChanged}:{incident:OperationsIncident;onChanged():Promise<void>}){
  const acknowledge=useMutation({mutationFn:()=>adminApi.acknowledgeIncident(incident.id),onSuccess:onChanged});
  const assign=useMutation({mutationFn:()=>adminApi.assignIncident(incident.id),onSuccess:onChanged});
  const escalate=useMutation({mutationFn:()=>adminApi.escalateIncident(incident.id,"Manual escalation from Control Room"),onSuccess:onChanged});
  const resolve=useMutation({
    mutationFn:async()=>{
      const note=window.prompt("اكتب سبب/إجراء الحل:");
      if(!note||note.trim().length<2)throw new Error("resolution_note_required");
      return adminApi.resolveIncident(incident.id,note.trim());
    },
    onSuccess:onChanged,
  });

  const route=incidentRoute(incident);
  return <div className={`incident severity-${incident.severity}`}>
    <div className="incident-head">
      <div>
        <span className={`severity-pill severity-${incident.severity}`}>{severityLabel[incident.severity]??incident.severity}</span>
        <span className="category-pill">{categoryLabel[incident.category]??incident.category}</span>
      </div>
      <StatusBadge value={incident.status}/>
    </div>
    <strong className="incident-title">{incident.title}</strong>
    <p>{incident.message}</p>
    <div className="incident-meta">
      <span>آخر رصد {new Date(incident.last_detected_at).toLocaleString("ar-EG")}</span>
      {incident.owner_admin_id?<span>Owner #{incident.owner_admin_id.slice(0,8)}</span>:<span>بدون Owner</span>}
    </div>
    <div className="incident-actions">
      {route?<Link className="secondary-button" to={route}>فتح المصدر</Link>:null}
      {incident.status==="open"?<button className="secondary-button" disabled={acknowledge.isPending} onClick={()=>acknowledge.mutate()}>استلام</button>:null}
      {!incident.owner_admin_id&&incident.status!=="resolved"?<button className="secondary-button" disabled={assign.isPending} onClick={()=>assign.mutate()}>تعيين لنفسي</button>:null}
      {incident.status!=="resolved"&&incident.severity!=="critical"?<button className="warning-button" disabled={escalate.isPending} onClick={()=>escalate.mutate()}>تصعيد</button>:null}
      {incident.status!=="resolved"?<button className="success-button" disabled={resolve.isPending} onClick={()=>resolve.mutate()}>حل</button>:null}
    </div>
  </div>;
}

function incidentRoute(i:OperationsIncident){
  if(i.source_type==="order"&&i.source_id)return `/orders/${i.source_id}`;
  if(i.source_type==="support_ticket"&&i.source_id)return `/support/${i.source_id}`;
  if(i.category==="payment")return "/finance";
  if(i.category==="reliability")return "/audit";
  return null;
}

function SmallMetric({label,value}:{label:string;value:number|string}){
  return <div className="brief-metric"><b>{value}</b><span>{label}</span></div>;
}

function Gate({label,met,value}:{label:string;met:boolean|null;value:string}){
  return <div className={`launch-gate ${met===true?"met":met===false?"not-met":"unknown"}`}>
    <span>{met===true?"✓":met===false?"!":"?"}</span><div><strong>{label}</strong><small>{value}</small></div>
  </div>;
}

function sortIncident(a:OperationsIncident,b:OperationsIncident){
  const rank:Record<string,number>={critical:0,high:1,warning:2,info:3};
  return (rank[a.severity]??9)-(rank[b.severity]??9)
    || new Date(b.last_detected_at).getTime()-new Date(a.last_detected_at).getTime();
}

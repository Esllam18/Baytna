import React,{useEffect,useMemo,useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Field,Loading,MetricCard,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";
import type {TrafficAdmissionEvent,TrafficZoneOverview} from "../api/types";

export function TrafficGovernancePage(){
  const qc=useQueryClient();
  const zones=useQuery({queryKey:keys.trafficZones,queryFn:()=>adminApi.trafficZones()});
  const [selected,setSelected]=useState("");
  useEffect(()=>{
    if(!selected&&zones.data?.length)setSelected(zones.data[0].zone_id);
  },[zones.data,selected]);

  const zone=useMemo(()=>zones.data?.find(x=>x.zone_id===selected)??null,[zones.data,selected]);
  const monitoring=useQuery({
    queryKey:keys.trafficMonitoring(selected),
    queryFn:()=>adminApi.trafficMonitoring(selected,30),
    enabled:Boolean(selected),
  });
  const forecasts=useQuery({
    queryKey:keys.trafficForecasts(selected),
    queryFn:()=>adminApi.trafficForecasts(selected,30),
    enabled:Boolean(selected),
  });
  const admissions=useQuery({
    queryKey:keys.trafficAdmissions(selected),
    queryFn:()=>adminApi.trafficAdmissions(selected,100),
    enabled:Boolean(selected),
  });

  const refreshAll=async()=>{
    await Promise.all([
      qc.invalidateQueries({queryKey:keys.trafficZones}),
      selected?qc.invalidateQueries({queryKey:keys.trafficMonitoring(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.trafficAdmissions(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.trafficForecasts(selected)}):Promise.resolve(),
    ]);
  };

  const refreshMonitoring=useMutation({
    mutationFn:()=>adminApi.refreshTrafficMonitoring(selected),
    onSuccess:refreshAll,
  });

  if(zones.isLoading)return <Loading label="بنجهز Traffic Governance..."/>;
  if(zones.isError)return <ErrorBox message="تعذر تحميل مناطق التوسع."/>;
  if(!zones.data?.length)return <Empty title="لا توجد مناطق توسع" body="أنشئ Expansion Zone من صفحة الاقتصاديات أولًا."/>;

  return <>
    <PageTitle
      title="Launch Traffic Governance"
      subtitle="Rollout audience • Zone caps • Chef capacity • Admission ledger • Expansion monitoring"
      action={<button className="secondary-button" onClick={()=>void refreshAll()}>تحديث</button>}
    />

    <div className="traffic-zone-tabs">
      {zones.data.map(z=><button key={z.zone_id} className={selected===z.zone_id?"active":""} onClick={()=>setSelected(z.zone_id)}>
        <strong>{z.area}</strong>
        <span>{z.rollout_stage} • {z.rollout_percent}%</span>
        <StatusBadge value={z.latest_monitoring?.health??z.zone_status}/>
      </button>)}
    </div>

    {zone?<>
      <TrafficHero zone={zone}/>
      <TrafficPolicyCard zone={zone} onDone={refreshAll}/>
      <section className="panel">
        <div className="zone-head">
          <div><h2>Expansion Monitoring</h2><p className="panel-note">Worker refreshes snapshots automatically. Manual refresh is evidence-safe and persisted.</p></div>
          <button className="primary" disabled={refreshMonitoring.isPending} onClick={()=>refreshMonitoring.mutate()}>Refresh snapshot</button>
        </div>
        {monitoring.isLoading?<Loading/>:monitoring.isError?<ErrorBox/>:monitoring.data?.length?
          <MonitoringHistory rows={monitoring.data}/>:
          <Empty title="لا توجد Monitoring Snapshots" body="اعمل Refresh snapshot أو انتظر Worker."/>}
      </section>

      <section className="panel">
        <h2>Capacity Forecast</h2>
        <p className="panel-note">Advisory one-hour forecast from durable monitoring history. Forecast risk never auto-resumes or increases traffic.</p>
        {forecasts.isLoading?<Loading/>:forecasts.isError?<ErrorBox/>:forecasts.data?.length?<div className="monitoring-list">{forecasts.data.map(f=><article className={`monitoring-row monitoring-${f.risk}`} key={f.id}>
          <div><StatusBadge value={f.risk}/><strong>{new Date(f.generated_at).toLocaleString("ar-EG")}</strong><small>{f.sample_count} samples</small></div>
          <div><span>Next hour</span><b>{f.projected_orders_next_hour}</b><small>{f.projected_hourly_utilization_pct}% projected</small></div>
          <div><span>Daily headroom</span><b>{f.daily_headroom_orders??"∞"}</b><small>{f.projected_minutes_to_daily_cap===null?"no ETA":`${f.projected_minutes_to_daily_cap} min`}</small></div>
          {f.reasons_json.length?<div className="blocker-list">{f.reasons_json.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">STABLE</span>}
        </article>)}</div>:<Empty title="لا توجد Capacity Forecasts" body="الـWorker ينشئ Forecast مع كل Monitoring snapshot."/>}
      </section>

      <section className="panel">
        <h2>Admission Ledger</h2>
        <p className="panel-note">كل Reject في منطقة Governed محفوظ حتى لو الـHTTP انتهى 409. Accepted records تُربط بالـOrder الحقيقي.</p>
        {admissions.isLoading?<Loading/>:admissions.isError?<ErrorBox/>:admissions.data?.length?
          <AdmissionTable rows={admissions.data}/>:
          <Empty title="لا توجد Admission Events"/>}
      </section>
    </>:null}
  </>;
}

function TrafficHero({zone}:{zone:TrafficZoneOverview}){
  const m=zone.latest_monitoring;
  return <div className={`traffic-hero traffic-${m?.health??"neutral"}`}>
    <div><span>ZONE</span><strong>{zone.area}</strong><small>{zone.zone_status} • {zone.rollout_stage} • {zone.rollout_percent}%</small></div>
    <div><span>Daily cap</span><strong>{zone.daily_order_cap??"∞"}</strong><small>{m?`${m.admitted_orders_today} used`:"No snapshot"}</small></div>
    <div><span>Hourly</span><strong>{zone.policy.hourly_order_cap??"∞"}</strong><small>{m?`${m.hourly_utilization_pct}%`:"—"}</small></div>
    <div><span>Chef/day</span><strong>{zone.policy.chef_daily_order_cap??"∞"}</strong><small>{m?`${m.top_chef_utilization_pct}% top chef`:"—"}</small></div>
  </div>;
}

function TrafficPolicyCard({zone,onDone}:{zone:TrafficZoneOverview;onDone():Promise<void>}){
  const [daily,setDaily]=useState(zone.daily_order_cap?.toString()??"");
  const [hourly,setHourly]=useState(zone.policy.hourly_order_cap?.toString()??"");
  const [chef,setChef]=useState(zone.policy.chef_daily_order_cap?.toString()??"");
  const [enabled,setEnabled]=useState(zone.policy.is_enabled);
  const [bucket,setBucket]=useState(zone.policy.enforce_rollout_bucket);
  const [warning,setWarning]=useState(String(zone.policy.warning_utilization_pct));
  const [critical,setCritical]=useState(String(zone.policy.critical_utilization_pct));
  const [rejectPct,setRejectPct]=useState(String(zone.policy.rejection_spike_pct));
  const [rejectAttempts,setRejectAttempts]=useState(String(zone.policy.rejection_spike_min_attempts));
  const [autoPause,setAutoPause]=useState(zone.policy.slo_auto_pause_enabled);
  const [redThreshold,setRedThreshold]=useState(String(zone.policy.slo_consecutive_red_snapshots));
  const [note,setNote]=useState(zone.policy.note??"");

  useEffect(()=>{
    setDaily(zone.daily_order_cap?.toString()??"");
    setHourly(zone.policy.hourly_order_cap?.toString()??"");
    setChef(zone.policy.chef_daily_order_cap?.toString()??"");
    setEnabled(zone.policy.is_enabled);
    setBucket(zone.policy.enforce_rollout_bucket);
    setWarning(String(zone.policy.warning_utilization_pct));
    setCritical(String(zone.policy.critical_utilization_pct));
    setRejectPct(String(zone.policy.rejection_spike_pct));
    setRejectAttempts(String(zone.policy.rejection_spike_min_attempts));
    setAutoPause(zone.policy.slo_auto_pause_enabled);
    setRedThreshold(String(zone.policy.slo_consecutive_red_snapshots));
    setNote(zone.policy.note??"");
  },[zone]);

  const caps=useMutation({
    mutationFn:()=>adminApi.updateTrafficCaps(zone.zone_id,{
      daily_order_cap:daily?Number(daily):null,
      hourly_order_cap:hourly?Number(hourly):null,
      chef_daily_order_cap:chef?Number(chef):null,
    }),
    onSuccess:onDone,
  });
  const policy=useMutation({
    mutationFn:()=>adminApi.updateTrafficPolicy(zone.zone_id,{
      is_enabled:enabled,
      hourly_order_cap:hourly?Number(hourly):null,
      chef_daily_order_cap:chef?Number(chef):null,
      enforce_rollout_bucket:bucket,
      warning_utilization_pct:Number(warning),
      critical_utilization_pct:Number(critical),
      rejection_spike_pct:Number(rejectPct),
      rejection_spike_min_attempts:Number(rejectAttempts),
      slo_auto_pause_enabled:autoPause,
      slo_consecutive_red_snapshots:Number(redThreshold),
      note:note.trim()||null,
    }),
    onSuccess:onDone,
  });

  return <section className="panel">
    <h2>Traffic Policy & Capacity Caps</h2>
    <p className="panel-note">Daily cap على الـZone. Hourly cap على intake. Chef/day cap يحمي مطبخ الشيف. Rollout bucket ثابت لكل Customer داخل المنطقة.</p>
    <div className="traffic-policy-grid">
      <Field label="Zone daily orders" type="number" min="1" value={daily} onChange={e=>setDaily(e.target.value)}/>
      <Field label="Zone hourly orders" type="number" min="1" value={hourly} onChange={e=>setHourly(e.target.value)}/>
      <Field label="Chef orders / day" type="number" min="1" value={chef} onChange={e=>setChef(e.target.value)}/>
      <Field label="Warning utilization %" type="number" min="1" max="100" value={warning} onChange={e=>setWarning(e.target.value)}/>
      <Field label="Critical utilization %" type="number" min="1" max="100" value={critical} onChange={e=>setCritical(e.target.value)}/>
      <Field label="Rejection spike %" type="number" min="1" max="100" value={rejectPct} onChange={e=>setRejectPct(e.target.value)}/>
      <Field label="Spike min attempts" type="number" min="1" value={rejectAttempts} onChange={e=>setRejectAttempts(e.target.value)}/>
      <Field label="RED snapshots before auto-pause" type="number" min="2" max="20" value={redThreshold} onChange={e=>setRedThreshold(e.target.value)}/>
    </div>
    <div className="traffic-toggles">
      <label><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/> Admission policy enabled</label>
      <label><input type="checkbox" checked={bucket} onChange={e=>setBucket(e.target.checked)}/> Enforce rollout customer bucket</label>
      <label><input type="checkbox" checked={autoPause} onChange={e=>setAutoPause(e.target.checked)}/> SLO auto-pause on consecutive RED</label>
    </div>
    <TextArea label="Operations note" value={note} onChange={e=>setNote(e.target.value)}/>
    {(caps.isError||policy.isError)?<p className="form-error">تعذر حفظ Traffic Policy. راجع الحدود والنسب.</p>:null}
    <div className="zone-actions">
      <button className="secondary-button" disabled={caps.isPending} onClick={()=>caps.mutate()}>Save caps</button>
      <button className="primary" disabled={policy.isPending} onClick={()=>policy.mutate()}>Save policy</button>
    </div>
  </section>;
}

function MonitoringHistory({rows}:{rows:NonNullable<TrafficZoneOverview["latest_monitoring"]>[] | any[]}){
  return <div className="monitoring-list">{rows.map((m:any)=><article key={m.id} className={`monitoring-row monitoring-${m.health}`}>
    <div><StatusBadge value={m.health}/><strong>{new Date(m.observed_at).toLocaleString("ar-EG")}</strong><small>{m.generated_by}</small></div>
    <div><span>Daily</span><b>{m.admitted_orders_today}/{m.zone_daily_cap??"∞"}</b><small>{m.daily_utilization_pct}%</small></div>
    <div><span>Hourly</span><b>{m.admitted_orders_last_hour}/{m.hourly_cap??"∞"}</b><small>{m.hourly_utilization_pct}%</small></div>
    <div><span>Rejects</span><b>{m.admission_rejections_last_hour}/{m.admission_attempts_last_hour}</b><small>{m.rejection_rate_pct}%</small></div>
    <div><span>Supply</span><b>{m.open_chefs} chefs • {m.available_drivers} drivers</b><small>top chef {m.top_chef_utilization_pct}%</small></div>
    {m.blockers_json.length?<div className="blocker-list">{m.blockers_json.map((x:string)=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">GREEN</span>}
  </article>)}</div>;
}

function AdmissionTable({rows}:{rows:TrafficAdmissionEvent[]}){
  return <div className="table-wrap"><table className="data-table"><thead><tr>
    <th>Time</th><th>Decision</th><th>Reason</th><th>Order</th><th>Bucket</th><th>Daily</th><th>Hourly</th><th>Chef</th>
  </tr></thead><tbody>{rows.map(x=><tr key={x.id}>
    <td>{new Date(x.created_at).toLocaleString("ar-EG")}</td>
    <td><StatusBadge value={x.decision}/></td>
    <td>{x.reason}</td>
    <td>{x.order_id?`#${x.order_id.slice(0,8)}`:"—"}</td>
    <td>{x.rollout_bucket===null?"—":`${x.rollout_bucket} / ${x.rollout_percent}`}</td>
    <td>{x.daily_usage_before}/{x.daily_cap??"∞"}</td>
    <td>{x.hourly_usage_before}/{x.hourly_cap??"∞"}</td>
    <td>{x.chef_usage_before}/{x.chef_daily_cap??"∞"}</td>
  </tr>)}</tbody></table></div>;
}

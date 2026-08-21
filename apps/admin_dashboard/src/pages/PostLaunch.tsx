import React from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,MetricCard,PageTitle,StatusBadge} from "../components/Ui";

export function PostLaunchPage(){
  const qc=useQueryClient();
  const summary=useQuery({queryKey:keys.postLaunchSummary,queryFn:()=>adminApi.postLaunchSummary()});
  const zones=useQuery({queryKey:keys.trafficZones,queryFn:()=>adminApi.trafficZones()});
  const refresh=useMutation({
    mutationFn:async()=>{
      for(const zone of zones.data??[])await adminApi.refreshPostLaunchReview(zone.zone_id);
    },
    onSuccess:async()=>{
      await Promise.all([
        qc.invalidateQueries({queryKey:keys.postLaunchSummary}),
        qc.invalidateQueries({queryKey:keys.postLaunchReviews}),
      ]);
    },
  });

  if(summary.isLoading||zones.isLoading)return <Loading label="بنجهز Post-Launch Stabilization..."/>;
  if(summary.isError||zones.isError)return <ErrorBox message="تعذر تحميل Expansion Review."/>;
  const data=summary.data;
  return <>
    <PageTitle title="Post-Launch Stabilization" subtitle="SLO auto-pause • Capacity forecast • Daily close cadence • Evidence retention • Expansion review" action={<button className="primary" disabled={refresh.isPending} onClick={()=>refresh.mutate()}>Refresh reviews</button>}/>
    <div className="metric-grid">
      <MetricCard label="Zones reviewed" value={data?.zones_reviewed??0}/>
      <MetricCard label="Healthy" value={data?.healthy??0} tone="green"/>
      <MetricCard label="Watch" value={data?.watch??0} tone="orange"/>
      <MetricCard label="Blocked" value={data?.blocked??0} tone="danger"/>
    </div>
    <section className="panel">
      <h2>Expansion Review</h2>
      <p className="panel-note">Review is advisory only. It never resumes traffic, raises a cap, or advances rollout. Recovery still uses the guarded Resume path.</p>
      {data?.reviews.length?<div className="table-wrap"><table className="data-table"><thead><tr>
        <th>Zone</th><th>Status</th><th>Recommendation</th><th>Monitoring</th><th>Auto-pauses</th><th>Daily closes</th><th>Forecast</th><th>Blockers</th>
      </tr></thead><tbody>{data.reviews.map(r=>{
        const zone=zones.data?.find(z=>z.zone_id===r.zone_id);
        return <tr key={r.id}>
          <td><strong>{zone?.area??r.zone_id.slice(0,8)}</strong><br/><small>{r.window_start} → {r.window_end}</small></td>
          <td><StatusBadge value={r.status}/></td>
          <td><StatusBadge value={r.recommendation}/></td>
          <td>{r.monitoring_snapshots} snapshots<br/><small>{r.red_snapshots} red • {r.amber_snapshots} amber</small></td>
          <td>{r.auto_pause_events}</td>
          <td>{r.closed_closes}/{r.required_closes}<br/><small>{r.blocked_closes} blocked • {r.overdue_closes} overdue</small></td>
          <td><StatusBadge value={r.latest_forecast_risk??"n/a"}/></td>
          <td>{r.blockers_json.length?<div className="blocker-list">{r.blockers_json.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">CLEAN</span>}</td>
        </tr>;
      })}</tbody></table></div>:<Empty title="لا توجد Expansion Reviews" body="اعمل Refresh reviews أو انتظر Worker maintenance."/>}
    </section>
    <section className="panel">
      <h2>Sprint 50 safety model</h2>
      <div className="launch-grid">
        <article className="launch-card"><span>AUTO-PAUSE</span><strong>Actual RED evidence only</strong><p>Capacity forecast is advisory. Consecutive persisted RED snapshots are required before system Pause.</p></article>
        <article className="launch-card"><span>DAILY CLOSE</span><strong>Same canonical ledger</strong><p>Worker prepares due days; an Admin still closes with existing completeness and maker-checker rules.</p></article>
        <article className="launch-card"><span>EVIDENCE</span><strong>Final packs are permanent</strong><p>Only superseded expired incomplete working packs may be pruned.</p></article>
      </div>
    </section>
  </>;
}

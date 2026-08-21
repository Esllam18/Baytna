import React,{useEffect,useMemo,useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Field,Loading,MetricCard,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";
import type {LaunchCommandOverview,LaunchCommandSession} from "../api/types";

export function LaunchCommandPage(){
  const qc=useQueryClient();
  const profile=useQuery({queryKey:keys.profile,queryFn:()=>adminApi.profile()});
  const sessions=useQuery({queryKey:keys.launchSessions,queryFn:()=>adminApi.launchSessions()});
  const programs=useQuery({queryKey:keys.pilotPrograms,queryFn:()=>adminApi.pilotPrograms()});
  const zones=useQuery({queryKey:keys.trafficZones,queryFn:()=>adminApi.trafficZones()});
  const [selected,setSelected]=useState("");

  useEffect(()=>{
    if(!selected&&sessions.data?.length)setSelected(sessions.data[0].id);
  },[sessions.data,selected]);

  const refresh=async()=>Promise.all([
    qc.invalidateQueries({queryKey:keys.launchSessions}),
    selected?qc.invalidateQueries({queryKey:keys.launchOverview(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchRunbook(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchEvents(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchOverrides(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchFinancialCloses(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchRollbackDrills(selected)}):Promise.resolve(),
    selected?qc.invalidateQueries({queryKey:keys.launchEvidencePacks(selected)}):Promise.resolve(),
  ]);

  if(sessions.isLoading||programs.isLoading||zones.isLoading||profile.isLoading)return <Loading label="بنجهز Launch Command Center..."/>;
  if(sessions.isError||programs.isError||zones.isError||profile.isError)return <ErrorBox message="تعذر تحميل Launch Command Center."/>;
  return <>
    <PageTitle
      title="Pilot Launch Command Center"
      subtitle="Canary runbook • Emergency traffic overrides • Daily financial close • Rollback drills • Evidence pack"
      action={<button className="secondary-button" onClick={()=>void refresh()}>تحديث</button>}
    />
    <CreateSession
      programs={programs.data??[]}
      zones={zones.data??[]}
      currentAdminId={profile.data?.id??""}
      onCreated={async(id)=>{setSelected(id);await refresh();}}
    />

    {sessions.data?.length?<div className="launch-session-tabs">
      {sessions.data.map(s=><button key={s.id} className={selected===s.id?"active":""} onClick={()=>setSelected(s.id)}>
        <strong>{s.launch_date}</strong>
        <span>#{s.id.slice(0,8)}</span>
        <StatusBadge value={s.status}/>
      </button>)}
    </div>:<Empty title="لا توجد Launch Sessions" body="أنشئ جلسة تشغيل للـCanary قبل إطلاق المنطقة."/>}

    {selected?<SessionCommand sessionId={selected} currentAdminId={profile.data?.id??""} onDone={refresh}/>:null}
  </>;
}

function CreateSession({programs,zones,currentAdminId,onCreated}:{programs:any[];zones:any[];currentAdminId:string;onCreated(id:string):Promise<void>}){
  const [program,setProgram]=useState(programs[0]?.id??"");
  const matchingZones=useMemo(()=>zones.filter(z=>!program||true),[zones,program]);
  const [zone,setZone]=useState(matchingZones[0]?.zone_id??"");
  const [launchDate,setLaunchDate]=useState(new Date().toISOString().slice(0,10));
  const [financeAdmin,setFinanceAdmin]=useState("");
  const [opsAdmin,setOpsAdmin]=useState("");
  const [notes,setNotes]=useState("");

  useEffect(()=>{if(!program&&programs.length)setProgram(programs[0].id)},[programs,program]);
  useEffect(()=>{if(!zone&&matchingZones.length)setZone(matchingZones[0].zone_id)},[matchingZones,zone]);

  const create=useMutation({
    mutationFn:()=>adminApi.createLaunchSession({
      pilot_program_id:program,
      zone_id:zone,
      launch_date:launchDate,
      incident_commander_admin_id:currentAdminId,
      finance_admin_id:financeAdmin.trim()||null,
      operations_admin_id:opsAdmin.trim()||null,
      notes:notes.trim()||null,
    }),
    onSuccess:async(row)=>{await onCreated(row.id);setNotes("");},
  });

  return <section className="panel launch-create">
    <h2>New Launch Command Session</h2>
    <div className="launch-form-grid">
      <label className="field"><span>Pilot Program</span><select value={program} onChange={e=>setProgram(e.target.value)}>
        {programs.map(p=><option key={p.id} value={p.id}>{p.name} • {p.area??"—"}</option>)}
      </select></label>
      <label className="field"><span>Expansion Zone</span><select value={zone} onChange={e=>setZone(e.target.value)}>
        {matchingZones.map(z=><option key={z.zone_id} value={z.zone_id}>{z.area} • {z.rollout_stage} {z.rollout_percent}%</option>)}
      </select></label>
      <Field label="Launch date" type="date" value={launchDate} onChange={e=>setLaunchDate(e.target.value)}/>
      <Field label="Finance Admin UUID" value={financeAdmin} onChange={e=>setFinanceAdmin(e.target.value)} placeholder="independent finance admin"/>
      <Field label="Operations Admin UUID" value={opsAdmin} onChange={e=>setOpsAdmin(e.target.value)} placeholder="operations owner"/>
    </div>
    <TextArea label="Command notes" value={notes} onChange={e=>setNotes(e.target.value)}/>
    {create.isError?<p className="form-error">تعذر إنشاء Session. تأكد أن الـZone مصدرها نفس Pilot Program ومفيش Session مفتوحة.</p>:null}
    <button className="primary" disabled={!program||!zone||!currentAdminId||create.isPending} onClick={()=>create.mutate()}>Create Command Session</button>
  </section>;
}

function SessionCommand({sessionId,currentAdminId,onDone}:{sessionId:string;currentAdminId:string;onDone():Promise<unknown>}){
  const overview=useQuery({queryKey:keys.launchOverview(sessionId),queryFn:()=>adminApi.launchOverview(sessionId)});
  const runbook=useQuery({queryKey:keys.launchRunbook(sessionId),queryFn:()=>adminApi.launchRunbook(sessionId)});
  const events=useQuery({queryKey:keys.launchEvents(sessionId),queryFn:()=>adminApi.launchEvents(sessionId,100)});
  const overrides=useQuery({queryKey:keys.launchOverrides(sessionId),queryFn:()=>adminApi.launchOverrides(sessionId)});
  const closes=useQuery({queryKey:keys.launchFinancialCloses(sessionId),queryFn:()=>adminApi.financialCloses(sessionId)});
  const drills=useQuery({queryKey:keys.launchRollbackDrills(sessionId),queryFn:()=>adminApi.rollbackDrills(sessionId)});
  const packs=useQuery({queryKey:keys.launchEvidencePacks(sessionId),queryFn:()=>adminApi.launchEvidencePacks(sessionId)});
  const action=useMutation({
    mutationFn:(kind:string)=>{
      if(kind==="start")return adminApi.startLaunchSession(sessionId);
      if(kind==="pause")return adminApi.pauseLaunchSession(sessionId);
      if(kind==="resume")return adminApi.resumeLaunchSession(sessionId);
      if(kind==="abort")return adminApi.abortLaunchSession(sessionId);
      return adminApi.completeLaunchSession(sessionId);
    },
    onSuccess:onDone,
  });
  const evidence=useMutation({mutationFn:()=>adminApi.generateLaunchEvidencePack(sessionId),onSuccess:onDone});

  if(overview.isLoading)return <Loading/>;
  if(overview.isError||!overview.data)return <ErrorBox message="تعذر تحميل Session."/>;
  const o=overview.data;
  return <>
    <CommandHero overview={o}/>
    <section className="panel">
      <div className="zone-head">
        <div><h2>Command Actions</h2><p className="panel-note">Start يسمح للـcontrolled rollout. Pause يوقف orchestration فقط؛ emergency traffic control موجود تحت.</p></div>
        <div className="zone-actions">
          {o.session.status==="planned"?<button className="primary" onClick={()=>action.mutate("start")}>Start</button>:null}
          {o.session.status==="active"?<button className="warning-button" onClick={()=>action.mutate("pause")}>Pause session</button>:null}
          {o.session.status==="paused"?<button className="primary" onClick={()=>action.mutate("resume")}>Resume session</button>:null}
          {["planned","active","paused"].includes(o.session.status)?<button className="danger-button" onClick={()=>action.mutate("abort")}>Abort</button>:null}
          {["active","paused"].includes(o.session.status)?<button className="success-button" onClick={()=>action.mutate("complete")}>Complete</button>:null}
          <button className="secondary-button" disabled={evidence.isPending} onClick={()=>evidence.mutate()}>Generate Evidence Pack</button>
        </div>
      </div>
      {action.isError?<p className="form-error">Action مرفوضة بواسطة Launch Gate. راجع Evidence Pack والـRunbook.</p>:null}
      {evidence.data?<EvidenceBanner pack={evidence.data}/>:null}
    </section>

    <RunbookPanel sessionId={sessionId} rows={runbook.data??[]} loading={runbook.isLoading} onDone={onDone}/>
    <TrafficOverridePanel sessionId={sessionId} rows={overrides.data??[]} status={o.session.status} onDone={onDone}/>
    <FinancialClosePanel sessionId={sessionId} launchDate={o.session.launch_date} rows={closes.data??[]} currentAdminId={currentAdminId} onDone={onDone}/>
    <RollbackPanel sessionId={sessionId} rows={drills.data??[]} status={o.session.status} onDone={onDone}/>
    <EvidenceHistory rows={packs.data??[]}/>
    <EventTimeline rows={events.data??[]}/>
  </>;
}

function CommandHero({overview:o}:{overview:LaunchCommandOverview}){
  return <div className="command-hero">
    <div><span>SESSION</span><strong>{o.session.status}</strong><small>{o.session.launch_date}</small></div>
    <div><span>ROLLOUT</span><strong>{o.rollout_stage}</strong><small>{o.rollout_percent}% • {o.zone_status}</small></div>
    <div><span>RUNBOOK</span><strong>{o.runbook_passed}/{o.runbook_total}</strong><small>{o.runbook_blocking} blocking</small></div>
    <div><span>OVERRIDES</span><strong>{o.active_overrides}</strong><small>active emergency controls</small></div>
    <div><span>FINANCE CLOSE</span><strong>{o.latest_financial_close?.status??"missing"}</strong><small>{o.latest_financial_close?`${o.latest_financial_close.revenue_coverage_pct}% revenue`:"—"}</small></div>
    <div><span>EVIDENCE</span><strong>{o.latest_evidence_pack?.status??"missing"}</strong><small>{o.latest_evidence_pack?.blockers_json.length??0} blockers</small></div>
  </div>;
}

function RunbookPanel({sessionId,rows,loading,onDone}:{sessionId:string;rows:any[];loading:boolean;onDone():Promise<unknown>}){
  const [evidence,setEvidence]=useState<Record<string,string>>({});
  const [notes,setNotes]=useState<Record<string,string>>({});
  const update=useMutation({
    mutationFn:(x:{key:string;status:string})=>adminApi.updateLaunchRunbook(sessionId,x.key,{
      status:x.status,
      evidence_reference:evidence[x.key]?.trim()||null,
      note:notes[x.key]?.trim()||null,
    }),
    onSuccess:onDone,
  });
  return <section className="panel">
    <h2>Canary Launch Runbook</h2>
    <p className="panel-note">كل Required step لازم Passed ومعاها Evidence Reference قبل Complete.</p>
    {loading?<Loading/>:<div className="runbook-list">{rows.map(step=><article key={step.id} className={`runbook-step runbook-${step.status}`}>
      <div className="runbook-seq">{step.sequence}</div>
      <div className="runbook-main"><strong>{step.title}</strong><small>{step.category} • {step.step_key}</small>
        {step.evidence_reference?<code>{step.evidence_reference}</code>:null}
      </div>
      <StatusBadge value={step.status}/>
      {step.status!=="passed"?<div className="runbook-actions">
        <input placeholder="evidence reference" value={evidence[step.step_key]??""} onChange={e=>setEvidence({...evidence,[step.step_key]:e.target.value})}/>
        <input placeholder="note" value={notes[step.step_key]??""} onChange={e=>setNotes({...notes,[step.step_key]:e.target.value})}/>
        <button className="success-button" disabled={!evidence[step.step_key]?.trim()} onClick={()=>update.mutate({key:step.step_key,status:"passed"})}>Pass</button>
        <button className="warning-button" onClick={()=>update.mutate({key:step.step_key,status:"failed"})}>Fail</button>
      </div>:<button className="ghost" onClick={()=>update.mutate({key:step.step_key,status:"pending"})}>Reset</button>}
    </article>)}</div>}
  </section>;
}

function TrafficOverridePanel({sessionId,rows,status,onDone}:{sessionId:string;rows:any[];status:string;onDone():Promise<unknown>}){
  const [type,setType]=useState("daily_order_cap");
  const [value,setValue]=useState("5");
  const [duration,setDuration]=useState("30");
  const [reason,setReason]=useState("");
  const create=useMutation({
    mutationFn:()=>adminApi.createLaunchOverride(sessionId,{
      override_type:type,
      value:type==="admission_enabled"?false:Number(value),
      duration_minutes:Number(duration),
      reason,
    }),
    onSuccess:async()=>{setReason("");await onDone();},
  });
  const revert=useMutation({mutationFn:(id:string)=>adminApi.revertLaunchOverride(id),onSuccess:onDone});
  return <section className="panel">
    <h2>Emergency Traffic Overrides</h2>
    <p className="panel-note">Override مؤقت وFail-Safe: يسمح فقط بتقليل الـcaps أو تعطيل admission. الـWorker يرجعه تلقائيًا عند انتهاء المدة.</p>
    <div className="launch-form-grid">
      <label className="field"><span>Override type</span><select value={type} onChange={e=>setType(e.target.value)}>
        <option value="daily_order_cap">Daily order cap</option>
        <option value="hourly_order_cap">Hourly order cap</option>
        <option value="chef_daily_order_cap">Chef/day cap</option>
        <option value="admission_enabled">Emergency admission STOP</option>
      </select></label>
      {type!=="admission_enabled"?<Field label="New lower cap" type="number" min="1" value={value} onChange={e=>setValue(e.target.value)}/>:null}
      <Field label="Duration minutes" type="number" min="1" value={duration} onChange={e=>setDuration(e.target.value)}/>
      <Field label="Reason" value={reason} onChange={e=>setReason(e.target.value)}/>
    </div>
    {create.isError?<p className="form-error">Override مرفوض: لا يمكن زيادة traffic أو تجاوز max duration.</p>:null}
    <button className="warning-button" disabled={status!=="active"||reason.trim().length<3||create.isPending} onClick={()=>create.mutate()}>Activate temporary override</button>
    <div className="override-list">{rows.map(x=><article key={x.id}>
      <div><strong>{x.override_type}</strong><small>{JSON.stringify(x.override_value_json)} • expires {new Date(x.expires_at).toLocaleString("ar-EG")}</small></div>
      <StatusBadge value={x.status}/>
      <span>{x.reason}</span>
      {x.status==="active"?<button className="secondary-button" onClick={()=>revert.mutate(x.id)}>Revert now</button>:null}
    </article>)}</div>
  </section>;
}

function FinancialClosePanel({sessionId,launchDate,rows,currentAdminId,onDone}:{sessionId:string;launchDate:string;rows:any[];currentAdminId:string;onDone():Promise<unknown>}){
  const [date,setDate]=useState(launchDate);
  const [note,setNote]=useState("");
  const prepare=useMutation({mutationFn:()=>adminApi.prepareFinancialClose(sessionId,date,note.trim()||null),onSuccess:onDone});
  const close=useMutation({mutationFn:(id:string)=>adminApi.closeFinancialDay(id,note.trim()||"Independent finance close."),onSuccess:onDone});
  const reopen=useMutation({mutationFn:(id:string)=>adminApi.reopenFinancialDay(id,note.trim()||"Reopened for new evidence."),onSuccess:onDone});
  return <section className="panel">
    <h2>Daily Financial Close</h2>
    <div className="launch-form-grid">
      <Field label="Close date" type="date" value={date} onChange={e=>setDate(e.target.value)}/>
      <Field label="Finance note" value={note} onChange={e=>setNote(e.target.value)}/>
    </div>
    <button className="primary" disabled={prepare.isPending} onClick={()=>prepare.mutate()}>Prepare / Recalculate</button>
    {(prepare.isError||close.isError||reopen.isError)?<p className="form-error">Financial close blocked. راجع coverage، provider imports، settlements وmaker-checker.</p>:null}
    <div className="financial-close-list">{rows.map(x=><article key={x.id} className={`close-card close-${x.status}`}>
      <div className="zone-head"><div><strong>{x.close_date}</strong><small>Prepared by {x.prepared_by_admin_id.slice(0,8)}</small></div><StatusBadge value={x.status}/></div>
      <div className="auto-kvs">
        <span>Delivered <b>{x.delivered_orders}</b></span>
        <span>Net <b><Money minor={x.net_collected_minor}/></b></span>
        <span>Verified costs <b><Money minor={x.verified_cost_minor}/></b></span>
        <span>Operating <b><Money minor={x.operational_profit_minor}/></b></span>
        <span>Revenue <b>{x.revenue_coverage_pct}%</b></span>
        <span>Cost <b>{x.cost_coverage_pct}%</b></span>
      </div>
      {x.blockers_json.length?<div className="blocker-list">{x.blockers_json.map((b:string)=><span key={b}>{b.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">READY TO CLOSE</span>}
      <div className="zone-actions">
        {x.status==="ready"?<button className="success-button" onClick={()=>close.mutate(x.id)}>Close</button>:null}
        {x.status==="closed"?<button className="warning-button" onClick={()=>reopen.mutate(x.id)}>Reopen</button>:null}
      </div>
    </article>)}</div>
  </section>;
}

function RollbackPanel({sessionId,rows,status,onDone}:{sessionId:string;rows:any[];status:string;onDone():Promise<unknown>}){
  const [mode,setMode]=useState("tabletop");
  const [target,setTarget]=useState("300");
  const [evidence,setEvidence]=useState("");
  const [note,setNote]=useState("");
  const start=useMutation({mutationFn:()=>adminApi.startRollbackDrill(sessionId,{mode,target_recovery_seconds:Number(target),note:note.trim()||null}),onSuccess:onDone});
  const complete=useMutation({mutationFn:(id:string)=>adminApi.completeRollbackDrill(id,{passed:true,evidence_reference:evidence,note:note.trim()||null}),onSuccess:async()=>{setEvidence("");await onDone();}});
  return <section className="panel">
    <h2>Rollback Drill</h2>
    <p className="panel-note">Live controlled mode يوقف admission أثناء drill ويرجعه عند Complete أو auto-recovery timeout.</p>
    <div className="launch-form-grid">
      <label className="field"><span>Mode</span><select value={mode} onChange={e=>setMode(e.target.value)}><option value="tabletop">Tabletop</option><option value="live_controlled">Live controlled</option></select></label>
      <Field label="Recovery target seconds" type="number" min="1" value={target} onChange={e=>setTarget(e.target.value)}/>
      <Field label="Evidence reference" value={evidence} onChange={e=>setEvidence(e.target.value)}/>
      <Field label="Note" value={note} onChange={e=>setNote(e.target.value)}/>
    </div>
    <button className="warning-button" disabled={status!=="active"||start.isPending} onClick={()=>start.mutate()}>Start rollback drill</button>
    {(start.isError||complete.isError)?<p className="form-error">Rollback action blocked. في production لازم verifier مستقل.</p>:null}
    <div className="drill-list">{rows.map(x=><article key={x.id}>
      <div><strong>{x.mode}</strong><small>{new Date(x.started_at).toLocaleString("ar-EG")}</small></div>
      <StatusBadge value={x.status}/>
      <span>Target {x.target_recovery_seconds}s • Recovery {x.recovery_seconds??"—"}s</span>
      {x.status==="running"?<button className="success-button" disabled={evidence.trim().length<3} onClick={()=>complete.mutate(x.id)}>Verify & complete</button>:null}
    </article>)}</div>
  </section>;
}

function EvidenceBanner({pack}:{pack:any}){
  return <div className={`evidence-banner evidence-${pack.status}`}>
    <div><strong>Evidence Pack: {pack.status}</strong><small>{pack.release_version} • {pack.migration_head} • {pack.checksum_sha256.slice(0,12)}…</small></div>
    {pack.blockers_json.length?<div className="blocker-list">{pack.blockers_json.map((x:string)=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">COMMAND EVIDENCE COMPLETE</span>}
  </div>;
}

function EvidenceHistory({rows}:{rows:any[]}){
  return <section className="panel">
    <h2>Evidence Pack History</h2>
    {rows.length?<div className="evidence-history">{rows.map(x=><EvidenceBanner key={x.id} pack={x}/>)}</div>:<Empty title="No evidence packs yet"/>}
  </section>;
}

function EventTimeline({rows}:{rows:any[]}){
  return <section className="panel">
    <h2>Command Timeline</h2>
    {rows.length?<div className="command-timeline">{rows.map(x=><article key={x.id}>
      <div className={`timeline-dot severity-${x.severity}`}></div>
      <div><strong>{x.title}</strong><small>{x.event_type} • {new Date(x.created_at).toLocaleString("ar-EG")}</small></div>
      <StatusBadge value={x.severity}/>
    </article>)}</div>:<Empty title="No command events"/>}
  </section>;
}

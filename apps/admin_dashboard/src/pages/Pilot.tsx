import React, {useEffect,useMemo,useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import type {PilotProgram,PilotQaEvidence} from "../api/types";
import {keys} from "../query";
import {Empty,ErrorBox,Field,Loading,MetricCard,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";

const REQUIRED_EVIDENCE=[
  ["pilot_qa_exit","QA Exit"],
  ["operations_signoff","Operations Sign-off"],
] as const;

export function PilotPage(){
  const qc=useQueryClient();
  const programs=useQuery({queryKey:keys.pilotPrograms,queryFn:()=>adminApi.pilotPrograms()});
  const [selected,setSelected]=useState("");
  const [showCreate,setShowCreate]=useState(false);
  const [name,setName]=useState("Baytna 6 October Pilot");
  const [area,setArea]=useState("6 أكتوبر");
  const [startDate,setStartDate]=useState("");
  const [endDate,setEndDate]=useState("");
  const [notes,setNotes]=useState("");

  useEffect(()=>{
    if(selected||!programs.data?.length)return;
    const active=programs.data.find(x=>x.status==="active");
    setSelected((active??programs.data[0]).id);
  },[programs.data,selected]);

  const program=useMemo(()=>programs.data?.find(x=>x.id===selected)??null,[programs.data,selected]);
  const stability=useQuery({queryKey:keys.pilotStability(selected),queryFn:()=>adminApi.pilotStability(selected),enabled:Boolean(selected)});
  const cohorts=useQuery({queryKey:keys.pilotCohorts(selected),queryFn:()=>adminApi.pilotCohorts(selected,8),enabled:Boolean(selected)});
  const evidence=useQuery({queryKey:keys.pilotEvidence(selected),queryFn:()=>adminApi.pilotEvidence(selected),enabled:Boolean(selected)});
  const post=useQuery({queryKey:keys.pilotPost(selected),queryFn:()=>adminApi.pilotPostReport(selected),enabled:Boolean(selected)});

  const invalidate=async()=>{
    await Promise.all([
      qc.invalidateQueries({queryKey:keys.pilotPrograms}),
      selected?qc.invalidateQueries({queryKey:keys.pilotStability(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.pilotCohorts(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.pilotEvidence(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.pilotPost(selected)}):Promise.resolve(),
    ]);
  };

  const create=useMutation({
    mutationFn:()=>adminApi.createPilotProgram({
      name:name.trim(),area:area.trim()||null,start_date:startDate,end_date:endDate||null,
      required_stability_weeks:8,rating_target:4.7,repeat_customer_target_pct:40,
      on_time_target_pct:95,cancellation_max_pct:5,notes:notes.trim()||null,
    }),
    onSuccess:async p=>{setSelected(p.id);setShowCreate(false);await invalidate()},
  });
  const activate=useMutation({mutationFn:(id:string)=>adminApi.activatePilotProgram(id),onSuccess:invalidate});
  const complete=useMutation({mutationFn:(id:string)=>adminApi.completePilotProgram(id),onSuccess:invalidate});
  const refresh=useMutation({mutationFn:(id:string)=>adminApi.refreshPilotProgram(id),onSuccess:invalidate});
  const evidenceMutation=useMutation({
    mutationFn:({type,status,reference,notes}:{type:string;status:string;reference:string|null;notes:string|null})=>adminApi.upsertPilotEvidence(selected,type,{status,reference,notes}),
    onSuccess:invalidate,
  });

  if(programs.isLoading)return <Loading label="بنجهز لوحة الطيار..."/>;
  if(programs.isError)return <ErrorBox message="تعذر تحميل برامج الطيار."/>;

  return <>
    <PageTitle
      title="Pilot Stability"
      subtitle="Cohorts • 8-week gate • QA/sign-off evidence • Backend profitability via Economics"
      action={<button className="primary" onClick={()=>setShowCreate(x=>!x)}>{showCreate?"إغلاق":"+ برنامج طيار"}</button>}
    />

    {showCreate?<section className="panel pilot-create">
      <h2>برنامج طيار جديد</h2>
      <div className="pilot-form-grid">
        <Field label="الاسم" value={name} onChange={e=>setName(e.target.value)}/>
        <Field label="المنطقة" value={area} onChange={e=>setArea(e.target.value)}/>
        <Field label="تاريخ البداية" type="date" value={startDate} onChange={e=>setStartDate(e.target.value)}/>
        <Field label="تاريخ النهاية — اختياري" type="date" value={endDate} onChange={e=>setEndDate(e.target.value)}/>
      </div>
      <TextArea label="ملاحظات" value={notes} onChange={e=>setNotes(e.target.value)}/>
      {create.isError?<p className="form-error">تعذر إنشاء برنامج الطيار. راجع التواريخ.</p>:null}
      <button className="primary" disabled={!name.trim()||!startDate||create.isPending} onClick={()=>create.mutate()}>{create.isPending?"جاري الإنشاء...":"إنشاء"}</button>
    </section>:null}

    {programs.data?.length?<div className="pilot-program-tabs">
      {programs.data.map(p=><button key={p.id} className={p.id===selected?"active":""} onClick={()=>setSelected(p.id)}>
        <strong>{p.name}</strong><span>{p.area??"كل المناطق"}</span><StatusBadge value={p.status}/>
      </button>)}
    </div>:<Empty title="لسه مفيش برنامج طيار" body="أنشئ البرنامج الأول وحدد تاريخ البداية."/>}

    {program?<>
      <section className="panel pilot-program-head">
        <div>
          <h2>{program.name}</h2>
          <p>{program.start_date} → {program.end_date??"مفتوح"} • {program.area??"كل المناطق"}</p>
          <div className="pilot-targets"><span>Rating ≥ {program.rating_target}</span><span>Repeat ≥ {program.repeat_customer_target_pct}%</span><span>On-time ≥ {program.on_time_target_pct}%</span><span>Cancel &lt; {program.cancellation_max_pct}%</span><span>{program.required_stability_weeks} أسابيع متتالية</span></div>
        </div>
        <div className="pilot-actions">
          <button className="secondary-button" disabled={refresh.isPending} onClick={()=>refresh.mutate(program.id)}>Refresh snapshots</button>
          {program.status==="planned"?<button className="primary" disabled={activate.isPending} onClick={()=>activate.mutate(program.id)}>Activate</button>:null}
          {program.status==="active"?<button className="warning-button" disabled={complete.isPending} onClick={()=>{if(window.confirm("إنهاء برنامج الطيار الآن؟"))complete.mutate(program.id)}}>Complete pilot</button>:null}
        </div>
      </section>

      {stability.isLoading?<Loading label="بنحسب استقرار الأسابيع..."/>:stability.isError||!stability.data?<ErrorBox/>:<>
        <div className={`stability-banner ${stability.data.stability_gate_met?"pass":"blocked"}`}>
          <div><span>8-WEEK STABILITY GATE</span><strong>{stability.data.stability_gate_met?"PASS":"NOT YET"}</strong></div>
          <div className="stability-count"><b>{stability.data.current_consecutive_passed_weeks}</b><span>/ {stability.data.required_weeks} أسابيع متتالية</span></div>
        </div>
        <div className="metrics-grid compact">
          <MetricCard label="Full weeks" value={stability.data.complete_full_weeks}/>
          <MetricCard label="Evaluable" value={stability.data.evaluable_weeks}/>
          <MetricCard label="Passed" value={stability.data.passed_weeks} tone="green"/>
          <MetricCard label="Max streak" value={stability.data.max_consecutive_passed_weeks} tone="orange"/>
        </div>

        <section className="panel">
          <h2>Weekly Stability</h2>
          <div className="table-wrap"><table className="data-table pilot-week-table"><thead><tr><th>Week</th><th>Dates</th><th>Orders</th><th>Rating</th><th>Repeat</th><th>On-time</th><th>Coverage</th><th>Cancel</th><th>Result</th></tr></thead><tbody>
          {stability.data.weeks.map(w=><tr key={w.id}>
            <td>W{w.week_index}</td><td>{w.week_start}<br/>{w.week_end}</td><td>{w.orders_created}<small>{w.delivered_orders} delivered</small></td>
            <td className={gateClass(w.rating_met)}>{w.average_chef_rating??"—"}</td>
            <td className={gateClass(w.repeat_met)}>{w.repeat_customer_rate_pct}%</td>
            <td className={gateClass(w.on_time_met)}>{w.on_time_delivery_rate_pct===null?"—":`${w.on_time_delivery_rate_pct}%`}</td>
            <td>{w.delivery_promise_coverage_pct}%</td>
            <td className={gateClass(w.cancellation_met)}>{w.cancellation_rate_pct}%</td>
            <td><WeekResult value={w.week_passed} evaluable={w.week_evaluable} complete={w.is_complete}/></td>
          </tr>)}
          </tbody></table></div>
        </section>
      </>}

      <div className="pilot-two-col">
        <section className="panel">
          <h2>Customer Cohorts</h2>
          {cohorts.isLoading?<Loading/>:cohorts.isError||!cohorts.data?<ErrorBox/>:cohorts.data.cohorts.length?<div className="table-wrap"><table className="data-table cohort-table"><thead><tr><th>Cohort</th><th>Size</th>{Array.from({length:8},(_,i)=><th key={i}>W{i}</th>)}</tr></thead><tbody>
            {cohorts.data.cohorts.map(c=><tr key={c.cohort_week}><td>W{c.cohort_week}<small>{c.cohort_start}</small></td><td>{c.cohort_size}</td>{Array.from({length:8},(_,i)=>{const cell=c.retention.find(x=>x.week_offset===i);return <td key={i}>{cell?`${cell.retention_pct}%`:"—"}</td>})}</tr>)}
          </tbody></table></div>:<Empty title="لا توجد cohorts مكتسبة بعد"/>}
        </section>

        <section className="panel">
          <h2>QA & Scale Evidence</h2>
          <div className="evidence-list">
            {REQUIRED_EVIDENCE.map(([type,label])=><EvidenceCard key={type} type={type} label={label} row={evidence.data?.find(x=>x.evidence_type===type)??null} busy={evidenceMutation.isPending} onSet={(status)=>{
              if(status==="passed"){
                const reference=window.prompt(`مرجع الدليل لـ ${label}:`);
                if(!reference?.trim())return;
                const notes=window.prompt("ملاحظات — اختياري:")||null;
                evidenceMutation.mutate({type,status,reference:reference.trim(),notes});
              }else{
                const notes=window.prompt("سبب الفشل/الملاحظة:")||null;
                evidenceMutation.mutate({type,status,reference:null,notes});
              }
            }}/>) }
          </div>
          <p className="profit-note">الربحية التشغيلية في Sprint 46 بقت محسوبة من Backend Cost Ledger بعد اكتمال Revenue/Cost Coverage والتحقق من القيود.</p>
        </section>
      </div>

      <section className="panel">
        <h2>Post-Pilot Analytics & Scale Decision</h2>
        {post.isLoading?<Loading/>:post.isError||!post.data?<ErrorBox/>:<>
          <div className={`scale-banner ${post.data.scale_ready?"ready":"blocked"}`}><div><span>SCALE READINESS</span><strong>{post.data.scale_ready?"READY TO REVIEW FOR SCALE":"BLOCKED"}</strong></div><div>{post.data.scale_ready?"الاستقرار + الأدلة مكتملة":"فيه شروط لسه ناقصة"}</div></div>
          <div className="metrics-grid compact">
            <MetricCard label="Orders" value={post.data.orders_created}/><MetricCard label="Delivered" value={post.data.delivered_orders}/>
            <MetricCard label="GMV" value={<Money minor={post.data.gmv_minor}/>} tone="orange"/><MetricCard label="Net collected" value={<Money minor={post.data.net_collected_minor}/>} tone="green"/>
            <MetricCard label="Repeat" value={`${post.data.repeat_customer_rate_pct}%`}/><MetricCard label="On-time" value={post.data.on_time_delivery_rate_pct===null?"—":`${post.data.on_time_delivery_rate_pct}%`}/>
            <MetricCard label="Promise coverage" value={`${post.data.delivery_promise_coverage_pct}%`}/><MetricCard label="Cancellation" value={`${post.data.cancellation_rate_pct}%`}/>
            <MetricCard label="W1 cohort retention" value={post.data.weighted_w1_retention_pct===null?"—":`${post.data.weighted_w1_retention_pct}%`}/><MetricCard label="W4 cohort retention" value={post.data.weighted_w4_retention_pct===null?"—":`${post.data.weighted_w4_retention_pct}%`}/>
            <MetricCard label="Support /100 orders" value={post.data.support_tickets_per_100_orders}/><MetricCard label="Refund rate" value={`${post.data.refund_rate_pct}%`}/>
            <MetricCard label="Critical incidents" value={post.data.active_critical_incidents} tone={post.data.active_critical_incidents?"danger":"green"}/><MetricCard label="Open reconciliation" value={post.data.open_payment_reconciliation_issues} tone={post.data.open_payment_reconciliation_issues?"danger":"green"}/><MetricCard label="Backend profitability" value={post.data.operational_profit_evidence_status} tone={post.data.operational_profit_evidence_status==="backend_passed"?"green":"danger"}/>
          </div>
          {post.data.scale_blockers.length?<div className="pilot-blockers"><strong>Blockers</strong>{post.data.scale_blockers.map(x=><span key={x}>{humanBlocker(x)}</span>)}</div>:null}
        </>}
      </section>
    </>:null}
  </>;
}

function WeekResult({value,evaluable,complete}:{value:boolean|null;evaluable:boolean;complete:boolean}){
  if(!complete)return <span className="week-result pending">IN PROGRESS</span>;
  if(!evaluable)return <span className="week-result pending">NOT EVALUABLE</span>;
  return <span className={`week-result ${value?"pass":"fail"}`}>{value?"PASS":"FAIL"}</span>;
}
function gateClass(value:boolean|null){return value===true?"gate-cell pass":value===false?"gate-cell fail":"gate-cell"}
function EvidenceCard({type,label,row,busy,onSet}:{type:string;label:string;row:PilotQaEvidence|null;busy:boolean;onSet(status:string):void}){
  return <div className="evidence-card"><div><strong>{label}</strong><span>{type}</span>{row?.reference?<small>{row.reference}</small>:null}</div><StatusBadge value={row?.status??"missing"}/><div className="evidence-actions"><button disabled={busy} className="success-button" onClick={()=>onSet("passed")}>Pass</button><button disabled={busy} className="danger-button" onClick={()=>onSet("failed")}>Fail</button></div></div>;
}
function humanBlocker(value:string){return value.replaceAll("_"," ");}

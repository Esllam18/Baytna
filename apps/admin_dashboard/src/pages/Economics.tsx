import React,{useEffect,useMemo,useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import type {EconomicsCostEntry,ExpansionZoneDetail} from "../api/types";
import {keys} from "../query";
import {Empty,ErrorBox,Field,Loading,MetricCard,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";

const COST_TYPES=[
  ["chef_payout","Chef payout"],
  ["delivery_partner","Delivery partner"],
  ["payment_processing","Payment processing"],
  ["packaging","Packaging"],
  ["refund_fee","Refund fee"],
  ["customer_recovery","Customer recovery"],
  ["other_variable","Other variable"],
  ["fixed_operations","Fixed operations"],
  ["communications_provider","Communications provider"],
  ["cloud_storage","Cloud storage"],
  ["cloud_infrastructure","Cloud infrastructure"],
  ["provider_adjustment","Provider adjustment"],
] as const;

export function EconomicsPage(){
  const qc=useQueryClient();
  const programs=useQuery({queryKey:keys.pilotPrograms,queryFn:()=>adminApi.pilotPrograms()});
  const [selected,setSelected]=useState("");
  const [showCost,setShowCost]=useState(false);
  const [showZone,setShowZone]=useState(false);

  useEffect(()=>{
    if(selected||!programs.data?.length)return;
    const completed=programs.data.find(x=>x.status==="completed");
    setSelected((completed??programs.data[0]).id);
  },[programs.data,selected]);

  const program=useMemo(()=>programs.data?.find(x=>x.id===selected)??null,[programs.data,selected]);
  const report=useQuery({
    queryKey:keys.economics(selected),
    queryFn:()=>adminApi.economicsReport(selected),
    enabled:Boolean(selected),
  });
  const costs=useQuery({
    queryKey:keys.economicsCosts(selected),
    queryFn:()=>adminApi.economicsCosts({programId:selected}),
    enabled:Boolean(selected),
  });
  const zones=useQuery({
    queryKey:keys.expansionZones,
    queryFn:()=>adminApi.expansionZones(),
  });

  const refresh=async()=>{
    await Promise.all([
      selected?qc.invalidateQueries({queryKey:keys.economics(selected)}):Promise.resolve(),
      selected?qc.invalidateQueries({queryKey:keys.economicsCosts(selected)}):Promise.resolve(),
      qc.invalidateQueries({queryKey:keys.expansionZones}),
      selected?qc.invalidateQueries({queryKey:keys.pilotPost(selected)}):Promise.resolve(),
    ]);
  };

  if(programs.isLoading)return <Loading label="بنجهز الاقتصاد التشغيلي..."/>;
  if(programs.isError)return <ErrorBox message="تعذر تحميل برامج الطيار."/>;

  return <>
    <PageTitle
      title="Operational Economics"
      subtitle="Cost ledger • Contribution margin • Backend profitability gate • Expansion zones"
      action={<div className="economics-actions"><button className="secondary-button" onClick={()=>setShowCost(x=>!x)}>+ Cost</button><button className="primary" onClick={()=>setShowZone(x=>!x)}>+ Expansion zone</button></div>}
    />

    {programs.data?.length?<div className="economics-program-tabs">
      {programs.data.map(p=><button key={p.id} className={p.id===selected?"active":""} onClick={()=>setSelected(p.id)}>
        <strong>{p.name}</strong><span>{p.area??"كل المناطق"}</span><StatusBadge value={p.status}/>
      </button>)}
    </div>:<Empty title="لا يوجد برنامج طيار" body="أنشئ برنامج الطيار أولًا."/>}

    {showCost&&program?<CostForm programId={program.id} area={program.area} onDone={async()=>{setShowCost(false);await refresh()}}/>:null}
    {showZone&&program?<ZoneForm programId={program.id} onDone={async()=>{setShowZone(false);await refresh()}}/>:null}

    {selected&&(report.isLoading?<Loading label="بنحسب اقتصاديات الطيار..."/>:report.isError||!report.data?<ErrorBox message="تعذر حساب الاقتصاديات."/>:<>
      <div className={`economics-banner ${report.data.economics_evaluable?(report.data.operational_profit_positive?"positive":"negative"):"blocked"}`}>
        <div>
          <span>BACKEND PROFITABILITY</span>
          <strong>{!report.data.economics_evaluable?"NOT EVALUABLE":report.data.operational_profit_positive?"POSITIVE":"NEGATIVE"}</strong>
        </div>
        <div><b>{report.data.cost_coverage_pct}%</b><span>Cost coverage</span></div>
        <div><b>{report.data.revenue_coverage_pct}%</b><span>Revenue coverage</span></div>
      </div>

      <div className="metrics-grid compact">
        <MetricCard label="Net collected" value={<Money minor={report.data.net_collected_minor}/>} tone="orange"/>
        <MetricCard label="Variable costs" value={<Money minor={report.data.variable_cost_minor}/>}/>
        <MetricCard label="Contribution" value={<Money minor={report.data.contribution_minor}/>} tone={report.data.contribution_minor>0?"green":"danger"}/>
        <MetricCard label="Contribution margin" value={report.data.contribution_margin_pct===null?"—":`${report.data.contribution_margin_pct}%`} tone={report.data.contribution_margin_pct!==null&&report.data.contribution_margin_pct>=15?"green":undefined}/>
        <MetricCard label="Fixed operations" value={<Money minor={report.data.fixed_cost_minor}/>}/>
        <MetricCard label="Operational profit" value={<Money minor={report.data.operational_profit_minor}/>} tone={report.data.operational_profit_minor>0?"green":"danger"}/>
      </div>

      <div className="economics-grid">
        <section className="panel">
          <h2>Cost completeness</h2>
          <div className="econ-kv"><span>Delivered orders</span><b>{report.data.delivered_orders}</b></div>
          <div className="econ-kv"><span>Fully costed</span><b>{report.data.fully_costed_delivered_orders}</b></div>
          <div className="econ-kv"><span>Required per order</span><b>{report.data.required_order_cost_types.join(", ")}</b></div>
          <div className="econ-kv"><span>Unverified entries</span><b>{report.data.unverified_cost_entries}</b></div>
          <div className="econ-kv"><span>Contribution / delivered order</span><b>{report.data.contribution_per_delivered_order_minor===null?"—":<Money minor={report.data.contribution_per_delivered_order_minor}/>}</b></div>
          {report.data.blockers.length?<div className="blocker-list">{report.data.blockers.map(x=><span key={x}>{human(x)}</span>)}</div>:<div className="all-clear">Economics source-of-truth complete.</div>}
        </section>

        <section className="panel">
          <h2>Cost breakdown</h2>
          {report.data.cost_breakdown.length?<div className="cost-breakdown">{report.data.cost_breakdown.map(x=><div key={x.cost_type}><span>{x.cost_type}</span><b><Money minor={x.amount_minor}/></b></div>)}</div>:<Empty title="لا توجد تكاليف verified بعد"/>}
        </section>
      </div>
    </>)}

    <section className="panel">
      <h2>Cost Ledger</h2>
      {costs.isLoading?<Loading/>:costs.isError?<ErrorBox/>:costs.data?.length?<div className="table-wrap"><table className="data-table"><thead><tr><th>Date</th><th>Type</th><th>Order</th><th>Amount</th><th>Source</th><th>Verified</th></tr></thead><tbody>
        {costs.data.map(c=><CostRow key={c.id} row={c} onDone={refresh}/>)}
      </tbody></table></div>:<Empty title="لا توجد Cost Entries" body="لا يتم افتراض التكاليف المفقودة بصفر."/>}
    </section>

    <section className="panel">
      <h2>Expansion Readiness</h2>
      <p className="panel-note">التوسع لا يعتمد على GMV فقط؛ لازم stability + backend profitability + contribution margin + QA/sign-off.</p>
      {zones.isLoading?<Loading/>:zones.isError?<ErrorBox/>:zones.data?.length?<div className="zone-grid">
        {zones.data.map(z=><ZoneCard key={z.zone.id} detail={z} onDone={refresh}/>)}
      </div>:<Empty title="لا توجد مناطق توسع" body="أضف منطقة مرشحة واربطها ببرنامج الطيار المصدر."/>}
    </section>
  </>;
}

function CostForm({programId,area,onDone}:{programId:string;area:string|null;onDone():Promise<void>}){
  const [orderId,setOrderId]=useState("");
  const [date,setDate]=useState(new Date().toISOString().slice(0,10));
  const [type,setType]=useState("chef_payout");
  const [amount,setAmount]=useState("");
  const [reference,setReference]=useState("");
  const [note,setNote]=useState("");
  const create=useMutation({
    mutationFn:()=>adminApi.createEconomicsCost({
      pilot_program_id:programId,
      order_id:orderId.trim()||null,
      area,
      incurred_on:date,
      cost_type:type,
      amount_minor:Math.round(Number(amount)*100),
      currency:"EGP",
      source:"manual",
      external_reference:reference.trim()||null,
      note:note.trim()||null,
    }),
    onSuccess:onDone,
  });
  return <section className="panel economics-form">
    <h2>إضافة تكلفة فعلية</h2>
    <div className="pilot-form-grid">
      <Field label="Order ID — اختياري للتكلفة الثابتة" value={orderId} onChange={e=>setOrderId(e.target.value)}/>
      <Field label="Date" type="date" value={date} onChange={e=>setDate(e.target.value)}/>
      <label className="field"><span>Cost Type</span><select value={type} onChange={e=>setType(e.target.value)}>{COST_TYPES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
      <Field label="Amount EGP" type="number" value={amount} onChange={e=>setAmount(e.target.value)}/>
      <Field label="External reference" value={reference} onChange={e=>setReference(e.target.value)}/>
    </div>
    <TextArea label="Note" value={note} onChange={e=>setNote(e.target.value)}/>
    {create.isError?<p className="form-error">تعذر إضافة التكلفة. راجع نوع التكلفة والطلب والتاريخ.</p>:null}
    <button className="primary" disabled={!date||Number(amount)<=0||create.isPending} onClick={()=>create.mutate()}>حفظ التكلفة</button>
  </section>;
}

function CostRow({row,onDone}:{row:EconomicsCostEntry;onDone():Promise<void>}){
  const verify=useMutation({mutationFn:()=>adminApi.verifyEconomicsCost(row.id),onSuccess:onDone});
  return <tr>
    <td>{row.incurred_on}</td><td>{row.cost_type}<small>{row.cost_scope}</small></td>
    <td>{row.order_id?`#${row.order_id.slice(0,8)}`:"—"}</td>
    <td><Money minor={row.amount_minor}/></td><td>{row.source}</td>
    <td>{row.is_verified?<span className="gate-pass">VERIFIED</span>:<button className="secondary-button" disabled={verify.isPending} onClick={()=>verify.mutate()}>Verify</button>}</td>
  </tr>;
}

function ZoneForm({programId,onDone}:{programId:string;onDone():Promise<void>}){
  const [area,setArea]=useState("");
  const [orders,setOrders]=useState("100");
  const [margin,setMargin]=useState("15");
  const [notes,setNotes]=useState("");
  const create=useMutation({
    mutationFn:()=>adminApi.createExpansionZone({
      area:area.trim(),source_program_id:programId,
      min_delivered_orders:Number(orders)||null,
      min_contribution_margin_pct:Number(margin),
      min_operational_profit_minor:1,
      notes:notes.trim()||null,
    }),
    onSuccess:onDone,
  });
  return <section className="panel economics-form">
    <h2>منطقة توسع مرشحة</h2>
    <div className="pilot-form-grid">
      <Field label="المنطقة" value={area} onChange={e=>setArea(e.target.value)} placeholder="مثال: الشيخ زايد"/>
      <Field label="Minimum delivered orders" type="number" value={orders} onChange={e=>setOrders(e.target.value)}/>
      <Field label="Min contribution margin %" type="number" value={margin} onChange={e=>setMargin(e.target.value)}/>
    </div>
    <TextArea label="Notes" value={notes} onChange={e=>setNotes(e.target.value)}/>
    {create.isError?<p className="form-error">تعذر إنشاء منطقة التوسع.</p>:null}
    <button className="primary" disabled={area.trim().length<2||create.isPending} onClick={()=>create.mutate()}>إنشاء المرشح</button>
  </section>;
}

function ZoneCard({detail,onDone}:{detail:ExpansionZoneDetail;onDone():Promise<void>}){
  const qc=useQueryClient();
  const z=detail.zone,a=detail.latest_assessment;
  const budget=useQuery({
    queryKey:keys.zoneBudget(z.id),
    queryFn:()=>adminApi.zoneBudgetSummary(z.id),
  });
  const [budgetCategory,setBudgetCategory]=useState("operations");
  const [budgetAmount,setBudgetAmount]=useState("");
  const [rolloutCap,setRolloutCap]=useState(z.daily_order_cap?String(z.daily_order_cap):"");

  const refresh=async()=>{
    await qc.invalidateQueries({queryKey:keys.zoneBudget(z.id)});
    await onDone();
  };

  const assess=useMutation({mutationFn:()=>adminApi.assessExpansionZone(z.id),onSuccess:refresh});
  const approve=useMutation({mutationFn:()=>adminApi.approveExpansionZone(z.id),onSuccess:refresh});
  const upsertBudget=useMutation({
    mutationFn:()=>adminApi.upsertZoneBudget(z.id,{
      category:budgetCategory,
      allocated_minor:Math.round(Number(budgetAmount)*100),
      note:"Sprint 47 launch budget",
    }),
    onSuccess:async()=>{setBudgetAmount("");await refresh()},
  });
  const startRollout=useMutation({
    mutationFn:()=>adminApi.startZoneRollout(z.id,rolloutCap?Number(rolloutCap):null),
    onSuccess:refresh,
  });
  const advanceRollout=useMutation({
    mutationFn:()=>adminApi.advanceZoneRollout(z.id,rolloutCap?Number(rolloutCap):null),
    onSuccess:refresh,
  });
  const pauseRollout=useMutation({mutationFn:()=>adminApi.pauseZoneRollout(z.id),onSuccess:refresh});
  const resumeRollout=useMutation({mutationFn:()=>adminApi.resumeZoneRollout(z.id),onSuccess:refresh});

  return <article className={`zone-card zone-${a?.decision??"unknown"}`}>
    <div className="zone-head">
      <div>
        <h3>{z.area}</h3>
        <small>Source pilot #{z.source_program_id.slice(0,8)}</small>
      </div>
      <StatusBadge value={z.status}/>
    </div>

    <div className="zone-targets">
      <span>Orders ≥ {z.min_delivered_orders}</span>
      <span>Contribution ≥ {z.min_contribution_margin_pct}%</span>
      <span>Profit ≥ {z.min_operational_profit_minor/100} EGP</span>
    </div>

    {a?<div className="zone-assessment">
      <strong>{a.decision==="ready"?"READY TO SCALE":"BLOCKED"}</strong>
      <span>Contribution {a.contribution_margin_pct===null?"—":`${a.contribution_margin_pct}%`}</span>
      <span>Profit <Money minor={a.operational_profit_minor}/></span>
      <span>Cost coverage {a.cost_coverage_pct}%</span>
      {a.blockers_json.length?<div className="blocker-list">{a.blockers_json.map(x=><span key={x}>{human(x)}</span>)}</div>:null}
    </div>:<p>لم يتم التقييم بعد.</p>}

    <div className="budget-panel">
      <div className="zone-head">
        <div><strong>Launch Budget</strong><small>Required before rollout</small></div>
        {budget.data?<span className={budget.data.budget_ready?"gate-pass":"gate-fail"}>{budget.data.budget_ready?"READY":"INCOMPLETE"}</span>:null}
      </div>
      {budget.isLoading?<Loading/>:budget.isError?<ErrorBox/>:budget.data?<>
        <div className="budget-summary">
          <span>Allocated <b><Money minor={budget.data.allocated_minor}/></b></span>
          <span>Committed <b><Money minor={budget.data.committed_minor}/></b></span>
          <span>Spent <b><Money minor={budget.data.spent_minor}/></b></span>
          <span>Remaining <b><Money minor={budget.data.remaining_minor}/></b></span>
        </div>
        {budget.data.missing_categories.length?<div className="blocker-list">{budget.data.missing_categories.map(x=><span key={x}>missing {x}</span>)}</div>:null}
        {budget.data.budgets.length?<div className="budget-list">{budget.data.budgets.map(b=><div className="budget-line" key={b.id}>
          <span>{b.category}</span><b><Money minor={b.allocated_minor}/></b><small>remaining <Money minor={b.remaining_minor}/></small>
        </div>)}</div>:null}
      </>:null}

      <div className="pilot-form-grid">
        <label className="field"><span>Budget category</span><select value={budgetCategory} onChange={e=>setBudgetCategory(e.target.value)}>
          {["operations","chef_onboarding","delivery_supply","contingency","marketing","support","technology"].map(x=><option key={x} value={x}>{x}</option>)}
        </select></label>
        <Field label="Allocation EGP" type="number" value={budgetAmount} onChange={e=>setBudgetAmount(e.target.value)}/>
      </div>
      <button className="secondary-button" disabled={Number(budgetAmount)<=0||upsertBudget.isPending} onClick={()=>upsertBudget.mutate()}>
        Save budget
      </button>
    </div>

    <div className="budget-panel">
      <div className="zone-head">
        <div><strong>Controlled Rollout</strong><small>{z.rollout_stage} • {z.rollout_percent}%</small></div>
        <StatusBadge value={z.rollout_stage}/>
      </div>
      <div className="rollout-meter"><span style={{width:`${z.rollout_percent}%`}}/></div>
      <div className="pilot-form-grid">
        <Field label="Daily order cap" type="number" value={rolloutCap} onChange={e=>setRolloutCap(e.target.value)} placeholder="Default policy"/>
      </div>
    </div>

    <div className="zone-actions">
      <button className="secondary-button" disabled={assess.isPending} onClick={()=>assess.mutate()}>Assess</button>
      {z.status==="ready"?<button className="success-button" disabled={approve.isPending} onClick={()=>approve.mutate()}>Approve</button>:null}
      {z.status==="approved"?<button className="primary" disabled={startRollout.isPending} onClick={()=>startRollout.mutate()}>Start Canary</button>:null}
      {z.status==="live"&&["canary","limited"].includes(z.rollout_stage)?<button className="primary" disabled={advanceRollout.isPending} onClick={()=>advanceRollout.mutate()}>Advance Rollout</button>:null}
      {z.status==="live"?<button className="warning-button" disabled={pauseRollout.isPending} onClick={()=>pauseRollout.mutate()}>Pause Rollout</button>:null}
      {z.status==="paused"?<button className="success-button" disabled={resumeRollout.isPending} onClick={()=>resumeRollout.mutate()}>Resume Rollout</button>:null}
    </div>

    {(startRollout.isError||advanceRollout.isError||resumeRollout.isError)?
      <p className="form-error">Rollout blocked: راجع readiness، budget، payment reconciliation، وsettlement blockers.</p>:null}
  </article>;
}

function human(value:string){return value.replaceAll("_"," ");}

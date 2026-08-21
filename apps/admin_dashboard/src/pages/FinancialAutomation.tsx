import React, {useMemo, useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {
  Empty,ErrorBox,Field,Loading,Money,PageTitle,StatusBadge,TextArea,
} from "../components/Ui";
import type {ProviderCostImportBatch,SettlementBatch} from "../api/types";

const genericExample={
  provider:"courier_partner",
  pilot_program_id:null,
  area:"6 October",
  period_start:"2026-08-01",
  period_end:"2026-08-07",
  source_currency:"EGP",
  fx_rate_to_egp:null,
  fx_reference:null,
  external_reference:"courier-week-2026-08-01",
  lines:[
    {
      line_key:"delivery-001",
      order_id:null,
      incurred_on:"2026-08-01",
      cost_type:"delivery_partner",
      source_amount_minor:3000,
      external_reference:"invoice-line-001",
      description:"Courier settlement",
      raw_json:{},
    },
  ],
};

const settlementExample={
  provider:"paymob",
  pilot_program_id:null,
  period_start:"2026-08-01",
  period_end:"2026-08-07",
  currency:"EGP",
  external_reference:"paymob-settlement-2026-08-w1",
  lines:[
    {
      provider_transaction_id:"99001",
      settlement_reference:"settlement-001",
      gross_amount_minor:30000,
      fee_minor:750,
      refund_minor:0,
      net_settlement_minor:29250,
      is_settled:true,
      settled_at:"2026-08-08T12:00:00Z",
      raw_json:{},
    },
  ],
};

export function FinancialAutomationPage(){
  const qc=useQueryClient();
  const programs=useQuery({queryKey:keys.pilotPrograms,queryFn:()=>adminApi.pilotPrograms()});
  const imports=useQuery({queryKey:keys.providerImports,queryFn:()=>adminApi.providerCostImports()});
  const settlements=useQuery({queryKey:keys.settlementBatches,queryFn:()=>adminApi.settlementBatches()});
  const [importJson,setImportJson]=useState(JSON.stringify(genericExample,null,2));
  const [settlementJson,setSettlementJson]=useState(JSON.stringify(settlementExample,null,2));
  const [twilioProgram,setTwilioProgram]=useState("");
  const [twilioStart,setTwilioStart]=useState(new Date().toISOString().slice(0,10));
  const [twilioEnd,setTwilioEnd]=useState(new Date().toISOString().slice(0,10));
  const [twilioFx,setTwilioFx]=useState("");
  const [twilioFxRef,setTwilioFxRef]=useState("");
  const [twilioReference,setTwilioReference]=useState(`twilio-${Date.now()}`);
  const [formError,setFormError]=useState("");

  const refresh=async()=>{
    await Promise.all([
      qc.invalidateQueries({queryKey:keys.providerImports}),
      qc.invalidateQueries({queryKey:keys.settlementBatches}),
    ]);
  };

  const createImport=useMutation({
    mutationFn:async()=>{
      setFormError("");
      let payload:unknown;
      try{payload=JSON.parse(importJson)}catch{throw new Error("invalid_json")}
      return adminApi.createProviderCostImport(payload);
    },
    onSuccess:refresh,
    onError:()=>setFormError("JSON الاستيراد غير صالح أو فشل التحقق من الدفعة."),
  });

  const createSettlement=useMutation({
    mutationFn:async()=>{
      setFormError("");
      let payload:unknown;
      try{payload=JSON.parse(settlementJson)}catch{throw new Error("invalid_json")}
      return adminApi.createSettlementBatch(payload);
    },
    onSuccess:refresh,
    onError:()=>setFormError("تعذر إنشاء دفعة التسوية. راجع المعاملات والمبالغ."),
  });

  const syncTwilio=useMutation({
    mutationFn:()=>adminApi.syncTwilioUsage({
      pilot_program_id:twilioProgram||null,
      area:null,
      period_start:twilioStart,
      period_end:twilioEnd,
      category:"totalprice",
      fx_rate_to_egp:twilioFx?Number(twilioFx):null,
      fx_reference:twilioFxRef.trim()||null,
      external_reference:twilioReference.trim(),
    }),
    onSuccess:refresh,
    onError:()=>setFormError("تعذر جلب Twilio Usage. يلزم credentials وسعر صرف موثق للعملات غير EGP."),
  });

  return <>
    <PageTitle
      title="Financial Automation"
      subtitle="Provider Cost Imports • Settlements • Reconciliation"
      action={<button className="secondary-button" onClick={()=>void refresh()}>تحديث</button>}
    />

    <div className="finance-auto-grid">
      <section className="panel">
        <h2>Provider Cost Import</h2>
        <p className="panel-note">الصق payload مُطبع من مزود/ملف محاسبي. الدفعة لا تدخل الربحية إلا بعد Validate ثم Apply.</p>
        <TextArea label="Normalized JSON" value={importJson} onChange={e=>setImportJson(e.target.value)} rows={13}/>
        <button className="primary" disabled={createImport.isPending} onClick={()=>createImport.mutate()}>
          Create import batch
        </button>
      </section>

      <section className="panel">
        <h2>Twilio Usage Sync</h2>
        <p className="panel-note">يجلب Usage Records. عند العملة الأجنبية لازم FX rate + مرجع موثق، ومفيش سعر صرف متخمن داخل النظام.</p>
        <label className="field"><span>Pilot Program</span><select value={twilioProgram} onChange={e=>setTwilioProgram(e.target.value)}>
          <option value="">Unscoped</option>
          {programs.data?.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
        </select></label>
        <div className="pilot-form-grid">
          <Field label="Start" type="date" value={twilioStart} onChange={e=>setTwilioStart(e.target.value)}/>
          <Field label="End" type="date" value={twilioEnd} onChange={e=>setTwilioEnd(e.target.value)}/>
          <Field label="FX → EGP" type="number" step="0.0001" value={twilioFx} onChange={e=>setTwilioFx(e.target.value)}/>
          <Field label="FX reference" value={twilioFxRef} onChange={e=>setTwilioFxRef(e.target.value)}/>
          <Field label="External reference" value={twilioReference} onChange={e=>setTwilioReference(e.target.value)}/>
        </div>
        <button className="primary" disabled={syncTwilio.isPending||!twilioReference.trim()} onClick={()=>syncTwilio.mutate()}>
          Sync Twilio TotalPrice
        </button>
      </section>
    </div>

    {formError?<p className="form-error">{formError}</p>:null}

    <section className="panel">
      <h2>Import Batches</h2>
      {imports.isLoading?<Loading/>:imports.isError?<ErrorBox/>:imports.data?.length?
        <div className="import-card-list">{imports.data.map(x=><ImportCard key={x.id} row={x} onDone={refresh}/>)}</div>:
        <Empty title="لا توجد Provider Imports"/>}
    </section>

    <section className="panel">
      <h2>Paymob Settlement Import</h2>
      <p className="panel-note">Normalized settlement evidence. Paymob fee costs لا تتطبق إلا لو كل سطور الدفعة اتطابقت مع transaction ledger.</p>
      <TextArea label="Settlement JSON" value={settlementJson} onChange={e=>setSettlementJson(e.target.value)} rows={13}/>
      <button className="primary" disabled={createSettlement.isPending} onClick={()=>createSettlement.mutate()}>
        Create settlement batch
      </button>
    </section>

    <section className="panel">
      <h2>Settlement Reconciliation</h2>
      {settlements.isLoading?<Loading/>:settlements.isError?<ErrorBox/>:settlements.data?.length?
        <div className="settlement-grid">{settlements.data.map(x=><SettlementCard key={x.id} row={x} onDone={refresh}/>)}</div>:
        <Empty title="لا توجد Settlement Batches"/>}
    </section>
  </>;
}

function ImportCard({row,onDone}:{row:ProviderCostImportBatch;onDone():Promise<void>}){
  const validate=useMutation({mutationFn:()=>adminApi.validateProviderCostImport(row.id),onSuccess:onDone});
  const apply=useMutation({mutationFn:()=>adminApi.applyProviderCostImport(row.id),onSuccess:onDone});
  return <article className="import-card">
    <div className="zone-head"><div><strong>{row.provider}</strong><small>{row.external_reference}</small></div><StatusBadge value={row.status}/></div>
    <div className="auto-kvs">
      <span>Rows <b>{row.rows_count}</b></span>
      <span>EGP <b><Money minor={row.total_egp_minor}/></b></span>
      <span>Applied <b>{row.applied_cost_entries}</b></span>
    </div>
    {row.validation_errors_json.length?<div className="blocker-list">{row.validation_errors_json.map((x,i)=><span key={i}>{JSON.stringify(x)}</span>)}</div>:null}
    <div className="zone-actions">
      {row.status==="draft"||row.status==="failed"?<button className="secondary-button" disabled={validate.isPending} onClick={()=>validate.mutate()}>Validate</button>:null}
      {row.status==="validated"?<button className="success-button" disabled={apply.isPending} onClick={()=>apply.mutate()}>Apply verified costs</button>:null}
    </div>
  </article>;
}

function SettlementCard({row,onDone}:{row:SettlementBatch;onDone():Promise<void>}){
  const reconcile=useMutation({mutationFn:()=>adminApi.reconcileSettlementBatch(row.id),onSuccess:onDone});
  return <article className={`zone-card zone-${row.status==="reconciled"?"ready":row.status==="blocked"?"blocked":"unknown"}`}>
    <div className="zone-head"><div><strong>{row.provider}</strong><small>{row.external_reference}</small></div><StatusBadge value={row.status}/></div>
    <div className="auto-kvs">
      <span>Gross <b><Money minor={row.gross_minor}/></b></span>
      <span>Fees <b><Money minor={row.fees_minor}/></b></span>
      <span>Net <b><Money minor={row.net_settlement_minor}/></b></span>
      <span>Matched <b>{row.matched_lines}/{row.rows_count}</b></span>
    </div>
    {row.blockers_json.length?<div className="blocker-list">{row.blockers_json.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:null}
    {row.status!=="reconciled"?<button className="primary" disabled={reconcile.isPending} onClick={()=>reconcile.mutate()}>Reconcile now</button>:null}
  </article>;
}

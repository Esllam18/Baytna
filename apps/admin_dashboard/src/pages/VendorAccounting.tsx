import React,{useState} from "react";
import {useMutation,useQuery,useQueryClient} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,MetricCard,Money,PageTitle,StatusBadge,TextArea} from "../components/Ui";
import type {ImportReviewItem,SettlementOperationsItem} from "../api/types";

export function VendorAccountingPage(){
  const qc=useQueryClient();
  const summary=useQuery({queryKey:keys.vendorAccounting,queryFn:()=>adminApi.vendorAccountingSummary()});
  const imports=useQuery({queryKey:keys.importReviewQueue,queryFn:()=>adminApi.importReviewQueue()});
  const settlements=useQuery({queryKey:keys.settlementOperations,queryFn:()=>adminApi.settlementOperationsQueue()});
  const refresh=async()=>Promise.all([
    qc.invalidateQueries({queryKey:keys.vendorAccounting}),
    qc.invalidateQueries({queryKey:keys.importReviewQueue}),
    qc.invalidateQueries({queryKey:keys.settlementOperations}),
    qc.invalidateQueries({queryKey:keys.providerImports}),
    qc.invalidateQueries({queryKey:keys.settlementBatches}),
  ]);

  return <>
    <PageTitle
      title="Vendor Accounting Operations"
      subtitle="Maker-checker import review • Settlement close/lock • Risk flags • Accounting queues"
      action={<button className="secondary-button" onClick={()=>void refresh()}>تحديث</button>}
    />

    {summary.isLoading?<Loading/>:summary.isError||!summary.data?<ErrorBox/>:<div className="metrics-grid compact">
      <MetricCard label="Imports pending" value={summary.data.imports_pending_review}/>
      <MetricCard label="High-risk open" value={summary.data.imports_high_risk_open} tone={summary.data.imports_high_risk_open?"danger":undefined}/>
      <MetricCard label="Imports approved" value={summary.data.imports_approved} tone="green"/>
      <MetricCard label="Settlement review" value={summary.data.settlements_in_review}/>
      <MetricCard label="Settlement closed" value={summary.data.settlements_closed} tone="green"/>
      <MetricCard label="Settlement blocked" value={summary.data.settlements_blocked} tone={summary.data.settlements_blocked?"danger":undefined}/>
    </div>}

    <section className="panel">
      <h2>Provider Import Review Queue</h2>
      <p className="panel-note">Validate يثبت صحة الـshape. Review يثبت الاعتماد المحاسبي. Pilot/Production يطلب reviewer مختلف عن creator قبل Apply.</p>
      {imports.isLoading?<Loading/>:imports.isError?<ErrorBox/>:imports.data?.length?
        <div className="accounting-queue">{imports.data.map(x=><ImportReviewCard key={x.id} row={x} onDone={refresh}/>)}</div>:
        <Empty title="لا توجد Import Reviews"/>}
    </section>

    <section className="panel">
      <h2>Settlement Operations Queue</h2>
      <p className="panel-note">Reconciled ليست Closed. الإغلاق المحاسبي يتأكد أن كل السطور matched ومفيش Payment Reconciliation Issue مفتوح.</p>
      {settlements.isLoading?<Loading/>:settlements.isError?<ErrorBox/>:settlements.data?.length?
        <div className="accounting-queue">{settlements.data.map(x=><SettlementOpsCard key={x.id} row={x} onDone={refresh}/>)}</div>:
        <Empty title="لا توجد Settlement Operations"/>}
    </section>
  </>;
}

function ImportReviewCard({row,onDone}:{row:ImportReviewItem;onDone():Promise<unknown>}){
  const [note,setNote]=useState("");
  const approve=useMutation({mutationFn:()=>adminApi.approveImportReview(row.id,note.trim()),onSuccess:onDone});
  const reject=useMutation({mutationFn:()=>adminApi.rejectImportReview(row.id,note.trim()),onSuccess:onDone});
  return <article className={`accounting-card review-${row.review_status}`}>
    <div className="zone-head"><div><strong>{row.provider}</strong><small>{row.external_reference}</small></div><div><StatusBadge value={row.status}/> <StatusBadge value={row.review_status}/></div></div>
    <div className="auto-kvs">
      <span>Rows <b>{row.rows_count}</b></span>
      <span>Total <b><Money minor={row.total_egp_minor}/></b></span>
      <span>Currency <b>{row.source_currency}</b></span>
      <span>Area <b>{row.area??"Unscoped"}</b></span>
    </div>
    {row.risk_flags_json.length?<div className="risk-flags">{row.risk_flags_json.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:<span className="gate-pass">NO RISK FLAGS</span>}
    {row.validation_errors_json.length?<div className="blocker-list"><span>{JSON.stringify(row.validation_errors_json)}</span></div>:null}
    {row.review_note?<p className="review-note">{row.review_note}</p>:null}
    {row.status==="validated"&&row.review_status!=="approved"?<>
      <TextArea label="Review note" value={note} onChange={e=>setNote(e.target.value)} placeholder="سبب الاعتماد أو الرفض"/>
      {(approve.isError||reject.isError)?<p className="form-error">تعذر تنفيذ قرار المراجعة. قد يكون maker-checker مطلوبًا.</p>:null}
      <div className="zone-actions">
        <button className="success-button" disabled={note.trim().length<2||approve.isPending} onClick={()=>approve.mutate()}>Approve</button>
        <button className="warning-button" disabled={note.trim().length<2||reject.isPending} onClick={()=>reject.mutate()}>Reject</button>
      </div>
    </>:null}
  </article>;
}

function SettlementOpsCard({row,onDone}:{row:SettlementOperationsItem;onDone():Promise<unknown>}){
  const [note,setNote]=useState("");
  const close=useMutation({mutationFn:()=>adminApi.closeSettlementOperation(row.id,note.trim()),onSuccess:onDone});
  const reopen=useMutation({mutationFn:()=>adminApi.reopenSettlementOperation(row.id,note.trim()),onSuccess:onDone});
  return <article className={`accounting-card settlement-${row.operations_status}`}>
    <div className="zone-head"><div><strong>{row.provider}</strong><small>{row.external_reference}</small></div><div><StatusBadge value={row.status}/> <StatusBadge value={row.operations_status}/></div></div>
    <div className="auto-kvs">
      <span>Matched <b>{row.matched_lines}/{row.rows_count}</b></span>
      <span>Fees <b><Money minor={row.fees_minor}/></b></span>
      <span>Net <b><Money minor={row.net_settlement_minor}/></b></span>
      <span>Mismatches <b>{row.mismatched_lines}</b></span>
    </div>
    {row.blockers_json.length?<div className="blocker-list">{row.blockers_json.map(x=><span key={x}>{x.replaceAll("_"," ")}</span>)}</div>:null}
    {row.close_note?<p className="review-note">{row.close_note}</p>:null}
    {(row.status==="reconciled"||row.operations_status==="closed")?<TextArea label="Operations note" value={note} onChange={e=>setNote(e.target.value)} placeholder="Settlement close/reopen evidence"/>:null}
    {(close.isError||reopen.isError)?<p className="form-error">تعذر تغيير حالة التسوية. راجع reconciliation وmaker-checker.</p>:null}
    <div className="zone-actions">
      {row.status==="reconciled"&&row.operations_status!=="closed"?<button className="success-button" disabled={note.trim().length<2||close.isPending} onClick={()=>close.mutate()}>Close settlement</button>:null}
      {row.operations_status==="closed"?<button className="warning-button" disabled={note.trim().length<2||reopen.isPending} onClick={()=>reopen.mutate()}>Reopen</button>:null}
    </div>
  </article>;
}

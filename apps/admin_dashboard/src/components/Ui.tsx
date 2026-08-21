import React from "react";

export function PageTitle({title,subtitle,action}:{title:string;subtitle?:string;action?:React.ReactNode}){
  return <div className="page-title">
    <div><h1>{title}</h1>{subtitle?<p>{subtitle}</p>:null}</div>
    {action?<div>{action}</div>:null}
  </div>;
}

export function MetricCard({label,value,note,tone}:{label:string;value:React.ReactNode;note?:string;tone?:"orange"|"green"|"blue"|"danger"}){
  return <div className={`metric-card ${tone??""}`}>
    <span>{label}</span><strong>{value}</strong>{note?<small>{note}</small>:null}
  </div>;
}

export function Loading({label="جاري التحميل..."}:{label?:string}){
  return <div className="state"><div className="spinner"/><p>{label}</p></div>;
}
export function ErrorBox({message="تعذر تحميل البيانات."}:{message?:string}){
  return <div className="state error-state"><strong>⚠</strong><p>{message}</p></div>;
}
export function Empty({title,body}:{title:string;body?:string}){
  return <div className="state"><strong className="empty-icon">○</strong><h3>{title}</h3>{body?<p>{body}</p>:null}</div>;
}

export function StatusBadge({value}:{value:string|null|undefined}){
  const safe=value??"—";
  const good=["delivered","succeeded","active","available","resolved","closed","ready","passed","completed"].includes(safe);
  const bad=["cancelled","failed","rejected","suspended","expired"].includes(safe);
  return <span className={`badge ${good?"good":bad?"bad":"warn"}`}>{safe}</span>;
}

export function Money({minor}:{minor:number}) {
  return <>{(minor/100).toLocaleString("ar-EG",{maximumFractionDigits:2})} ج.م</>;
}

export function Field({label,...props}:React.InputHTMLAttributes<HTMLInputElement>&{label:string}){
  return <label className="field"><span>{label}</span><input {...props}/></label>;
}
export function TextArea({label,...props}:React.TextareaHTMLAttributes<HTMLTextAreaElement>&{label:string}){
  return <label className="field"><span>{label}</span><textarea {...props}/></label>;
}

import React,{useState} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,PageTitle,StatusBadge} from "../components/Ui";

export function DriversPage(){
  const [status,setStatus]=useState("");
  const q=useQuery({queryKey:keys.drivers(status),queryFn:()=>adminApi.drivers(status||undefined)});
  return <>
    <PageTitle title="المندوبون" subtitle="التوفر والمهام ومشاكل التوصيل"/>
    <div className="toolbar"><select value={status} onChange={e=>setStatus(e.target.value)}><option value="">كل الحالات</option><option value="offline">offline</option><option value="available">available</option><option value="on_mission">on_mission</option></select><span>{q.data?.length??0} مندوب</span></div>
    {q.isLoading?<Loading/>:q.isError?<ErrorBox/>:q.data?.length?
      <div className="cards-grid">{q.data.map(d=><Link to={`/drivers/${d.id}`} className="entity-card" key={d.id}>
        <div className="entity-icon">🛵</div><div className="entity-main"><strong>مندوب #{d.id.slice(0,8)}</strong><span>★ {d.rating.toFixed(1)}</span><div className="entity-badges"><StatusBadge value={d.status}/></div></div>
        <div className="entity-stats"><b>{d.delivered_missions}</b><span>تم توصيلها • {d.issue_missions} مشاكل</span></div>
      </Link>)}</div>:<Empty title="مفيش مندوبين"/>}
  </>;
}

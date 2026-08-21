import React,{useState} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,PageTitle,StatusBadge} from "../components/Ui";

export function ChefsPage(){
  const [status,setStatus]=useState("");
  const q=useQuery({queryKey:keys.chefs(status),queryFn:()=>adminApi.chefs(status||undefined)});
  return <>
    <PageTitle title="الشيفات" subtitle="الحالة، التحقق، الطلبات والأداء"/>
    <div className="toolbar">
      <select value={status} onChange={e=>setStatus(e.target.value)}>
        <option value="">كل الحالات</option><option value="active">active</option><option value="paused">paused</option><option value="suspended">suspended</option><option value="rejected">rejected</option>
      </select><span>{q.data?.length??0} شيف</span>
    </div>
    {q.isLoading?<Loading/>:q.isError?<ErrorBox/>:q.data?.length?
      <div className="cards-grid">{q.data.map(c=><Link to={`/chefs/${c.id}`} className="entity-card" key={c.id}>
        <div className="entity-icon">👩‍🍳</div><div className="entity-main"><strong>{c.display_name}</strong><span>{c.specialty} • {c.area}</span>
        <div className="entity-badges"><StatusBadge value={c.status}/>{c.is_verified?<span className="badge good">موثّق</span>:<span className="badge warn">غير موثّق</span>}</div></div>
        <div className="entity-stats"><b>★ {c.rating.toFixed(1)}</b><span>{c.delivered_orders}/{c.total_orders} تم توصيلها</span></div>
      </Link>)}</div>:<Empty title="مفيش شيفات"/>}
  </>;
}

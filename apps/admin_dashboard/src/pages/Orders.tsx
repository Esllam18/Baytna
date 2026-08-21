import React,{useState} from "react";
import {Link} from "react-router-dom";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,Money,PageTitle,StatusBadge} from "../components/Ui";

const FILTERS=["","pending_payment","confirmed","accepted_by_chef","preparing","ready_for_pickup","assigned_to_driver","picked_up","out_for_delivery","delivered","cancelled"];

export function OrdersPage(){
  const [status,setStatus]=useState("");
  const q=useQuery({queryKey:keys.orders(status),queryFn:()=>adminApi.orders({status:status||undefined})});
  return <>
    <PageTitle title="الطلبات" subtitle="كل الطلبات وحالتها المالية والتشغيلية"/>
    <div className="toolbar">
      <select value={status} onChange={e=>setStatus(e.target.value)}>{FILTERS.map(x=><option key={x} value={x}>{x||"كل الحالات"}</option>)}</select>
      <span>{q.data?.length??0} نتيجة</span>
    </div>
    {q.isLoading?<Loading/>:q.isError?<ErrorBox/>:q.data?.length?
      <div className="table-wrap"><table><thead><tr><th>الطلب</th><th>العميل</th><th>الشيف</th><th>الحالة</th><th>الدفع</th><th>التوصيل</th><th>الإجمالي</th><th>التاريخ</th></tr></thead>
      <tbody>{q.data.map(o=><tr key={o.id}>
        <td><Link to={`/orders/${o.id}`} className="id-link">#{o.id.slice(0,8).toUpperCase()}</Link></td>
        <td><strong>{o.customer_name||"عميل"}</strong><small>{o.customer_phone_masked}</small></td>
        <td>{o.chef_name}</td>
        <td><StatusBadge value={o.status}/></td>
        <td><StatusBadge value={o.payment_status}/></td>
        <td><StatusBadge value={o.delivery_status}/></td>
        <td><Money minor={o.total_minor}/></td>
        <td>{new Date(o.created_at).toLocaleString("ar-EG")}</td>
      </tr>)}</tbody></table></div>:<Empty title="مفيش طلبات بالحالة دي"/>}
  </>;
}

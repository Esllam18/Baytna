import React,{useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,MetricCard,Money,PageTitle} from "../components/Ui";

export function FinancePage(){
  const [days,setDays]=useState(30);
  const finance=useQuery({queryKey:[...keys.finance,days],queryFn:()=>adminApi.finance()});
  const daily=useQuery({queryKey:[...keys.daily,days],queryFn:()=>adminApi.daily(days)});
  const funnel=useQuery({queryKey:[...keys.funnel,days],queryFn:()=>adminApi.funnel(days)});
  const retention=useQuery({queryKey:keys.retention,queryFn:()=>adminApi.retention(90)});

  if(finance.isLoading)return <Loading label="بنجهز التقارير المالية..."/>;
  if(finance.isError||!finance.data)return <ErrorBox/>;
  const f=finance.data;

  const funnelItems=funnel.data?[
    ["تم الإنشاء",funnel.data.orders_created],["تأكيد",funnel.data.reached_confirmed],["قبول الشيف",funnel.data.reached_accepted_by_chef],
    ["جاهز",funnel.data.reached_ready_for_pickup],["مندوب",funnel.data.reached_assigned_to_driver],["تم الاستلام",funnel.data.reached_picked_up],
    ["في الطريق",funnel.data.reached_out_for_delivery],["تم التوصيل",funnel.data.reached_delivered],
  ]:[];

  return <>
    <PageTitle title="المالية والتحليلات" subtitle="التحصيل والاستردادات ومسار الطلب"/>
    <div className="toolbar"><select value={days} onChange={e=>setDays(Number(e.target.value))}><option value={7}>7 أيام</option><option value={30}>30 يوم</option><option value={90}>90 يوم</option></select></div>
    <div className="metrics-grid">
      <MetricCard label="المبالغ المحصلة" value={<Money minor={f.captured_minor}/>} tone="green"/>
      <MetricCard label="الاستردادات" value={<Money minor={f.refunded_minor}/>} tone={f.refunded_minor?"danger":undefined}/>
      <MetricCard label="صافي التحصيل" value={<Money minor={f.net_collected_minor}/>} tone="blue"/>
      <MetricCard label="دفعات ناجحة" value={f.successful_payments_count}/>
      <MetricCard label="دفعات معلقة" value={f.pending_payments_count}/>
      <MetricCard label="دفعات فاشلة" value={f.failed_payments_count} tone={f.failed_payments_count?"danger":undefined}/>
    </div>

    <div className="detail-grid">
      <section className="panel"><h2>تكلفة الخصومات</h2>
        <div className="kv"><span>Coupons</span><strong><Money minor={f.coupon_discount_minor}/></strong></div>
        <div className="kv"><span>Loyalty</span><strong><Money minor={f.loyalty_discount_minor}/></strong></div>
        <div className="kv"><span>Subscriptions</span><strong><Money minor={f.subscription_discount_minor}/></strong></div>
      </section>
      <section className="panel"><h2>Retention — 90 يوم</h2>
        <div className="kv"><span>عملاء فريدون</span><strong>{retention.data?.unique_customers??0}</strong></div>
        <div className="kv"><span>عملاء متكررون</span><strong>{retention.data?.repeat_customers??0}</strong></div>
        <div className="kv"><span>معدل التكرار</span><strong>{retention.data?.repeat_customer_rate_pct??0}%</strong></div>
        <div className="kv"><span>طلبات/عميل</span><strong>{retention.data?.average_delivered_orders_per_customer??0}</strong></div>
      </section>
    </div>

    <section className="panel"><h2>Funnel الطلب</h2><div className="funnel">{funnelItems.map(([label,value],i)=><div className="funnel-row" key={String(label)}><span>{label}</span><div><i style={{width:`${funnelItems[0]?.[1]?Number(value)/Number(funnelItems[0][1])*100:0}%`}}/></div><strong>{value}</strong></div>)}</div></section>
    <section className="panel"><h2>الحركة اليومية</h2><div className="table-wrap"><table><thead><tr><th>اليوم</th><th>طلبات</th><th>تم توصيلها</th><th>GMV</th><th>تحصيل</th><th>استرداد</th></tr></thead><tbody>
      {daily.data?.map(d=><tr key={d.day}><td>{d.day}</td><td>{d.orders_created}</td><td>{d.delivered_orders}</td><td><Money minor={d.gmv_minor}/></td><td><Money minor={d.captured_minor}/></td><td><Money minor={d.refunds_minor}/></td></tr>)}
    </tbody></table></div></section>
  </>;
}

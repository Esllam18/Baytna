import React from "react";
import {useQuery} from "@tanstack/react-query";
import {Link} from "react-router-dom";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {ErrorBox,Loading,MetricCard,Money,PageTitle} from "../components/Ui";

export function DashboardPage(){
  const overview=useQuery({queryKey:keys.overview,queryFn:()=>adminApi.overview(),refetchInterval:30_000});
  const support=useQuery({queryKey:keys.support,queryFn:()=>adminApi.supportSummary(),refetchInterval:30_000});
  const daily=useQuery({queryKey:keys.daily,queryFn:()=>adminApi.daily(14)});
  const finance=useQuery({queryKey:keys.finance,queryFn:()=>adminApi.finance()});

  if(overview.isLoading)return <Loading label="بنجهز لوحة العمليات..."/>;
  if(overview.isError||!overview.data)return <ErrorBox/>;

  const o=overview.data;
  const maxOrders=Math.max(1,...(daily.data??[]).map(x=>x.orders_created));

  return <>
    <PageTitle title="لوحة العمليات" subtitle={`الفترة ${o.date_from} → ${o.date_to}`} action={<Link className="button-link" to="/orders">عرض كل الطلبات</Link>}/>
    <div className="metrics-grid">
      <MetricCard label="كل الطلبات" value={o.orders_total} note={`${o.active_orders} نشطة`} tone="orange"/>
      <MetricCard label="تم التوصيل" value={o.delivered_orders} note={`${o.delivery_success_rate_pct}% نجاح`} tone="green"/>
      <MetricCard label="صافي التحصيل" value={<Money minor={o.net_collected_minor}/>} note={`GMV ${(o.gmv_minor/100).toLocaleString("ar-EG")} ج.م`} tone="blue"/>
      <MetricCard label="الدعم المفتوح" value={o.open_support_tickets} note={`${support.data?.urgent_open??0} عاجل`} tone={o.open_support_tickets?"danger":undefined}/>
      <MetricCard label="الشيفات النشطين" value={o.active_chefs} note={`${o.verified_chefs} موثّق`}/>
      <MetricCard label="المندوبون" value={o.available_drivers+o.on_mission_drivers} note={`${o.available_drivers} متاح • ${o.on_mission_drivers} في مهمة`}/>
    </div>

    <div className="dashboard-grid">
      <section className="panel">
        <div className="panel-head"><div><h2>الطلبات — آخر 14 يوم</h2><p>إنشاء مقابل توصيل</p></div></div>
        {daily.isLoading?<Loading/>:daily.isError?<ErrorBox/>:
          <div className="bars">{daily.data?.map(d=><div className="bar-item" key={d.day} title={`${d.day}: ${d.orders_created} طلب`}>
            <div className="bar-track"><div className="bar-created" style={{height:`${Math.max(5,d.orders_created/maxOrders*100)}%`}}/><div className="bar-delivered" style={{height:`${Math.max(0,d.delivered_orders/maxOrders*100)}%`}}/></div>
            <span>{new Date(d.day).getDate()}</span>
          </div>)}</div>}
      </section>

      <section className="panel">
        <div className="panel-head"><div><h2>حالة التشغيل</h2><p>أهم الحاجات اللي تحتاج متابعة</p></div></div>
        <div className="ops-list">
          <Link to="/support"><strong>{support.data?.unassigned_open??0}</strong><span>تذاكر دعم غير معيّنة</span></Link>
          <Link to="/support"><strong>{support.data?.urgent_open??0}</strong><span>تذاكر عاجلة</span></Link>
          <Link to="/orders"><strong>{o.cancelled_orders}</strong><span>طلبات ملغية / منتهية</span></Link>
          <Link to="/finance"><strong>{finance.data?.failed_payments_count??0}</strong><span>مدفوعات فاشلة</span></Link>
        </div>
      </section>
    </div>
  </>;
}

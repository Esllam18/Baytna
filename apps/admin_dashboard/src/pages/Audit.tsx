import React from "react";
import {useQuery} from "@tanstack/react-query";
import {adminApi} from "../api/admin";
import {keys} from "../query";
import {Empty,ErrorBox,Loading,PageTitle} from "../components/Ui";

export function AuditPage(){
  const q=useQuery({queryKey:keys.audit,queryFn:()=>adminApi.audit(150)});
  return <>
    <PageTitle title="سجل التدقيق" subtitle="أثر العمليات الإدارية والتغييرات الحساسة"/>
    {q.isLoading?<Loading/>:q.isError?<ErrorBox/>:q.data?.length?
      <div className="table-wrap"><table><thead><tr><th>الوقت</th><th>الإجراء</th><th>الكيان</th><th>المعرف</th><th>المسؤول</th><th>Request ID</th></tr></thead><tbody>
        {q.data.map(x=><tr key={x.id}><td>{new Date(x.created_at).toLocaleString("ar-EG")}</td><td><code>{x.action}</code></td><td>{x.entity_type??"—"}</td><td className="mono">{x.entity_id??"—"}</td><td className="mono">{x.actor_user_id?.slice(0,8)??"system"}</td><td className="mono">{x.request_id??"—"}</td></tr>)}
      </tbody></table></div>:<Empty title="مفيش سجلات تدقيق"/>}
  </>;
}

import {request,ApiError} from "./http";
import {tokenStore} from "../auth/tokenStore";
import type {
  AdminProfile,AuditItem,ChefDetail,ChefListItem,DailyMetric,DashboardOverview,
  DriverDetail,DriverListItem,FinanceSummary,Funnel,OrderDetail,OrderListItem,
  Refund,Retention,SupportSummary,SupportTicket,ControlRoomOverview,DailyBrief,
  LaunchKpis,OperationsIncident,PilotProgram,PilotStabilityReport,PilotCohortReport,
  PilotQaEvidence,PilotPostPilotReport,PilotWeeklySnapshot,EconomicsCostEntry,
  EconomicsReport,ExpansionZone,ExpansionZoneDetail,ExpansionAssessment,
  ProviderCostImportBatch,ProviderCostImportDetail,SettlementBatch,SettlementBatchDetail,
  ZoneBudget,ZoneBudgetSummary,RolloutResponse,
  TrafficZoneOverview,TrafficPolicy,TrafficMonitoringSnapshot,TrafficAdmissionEvent,CapacityForecast,
  ImportReviewItem,SettlementOperationsItem,VendorAccountingSummary,
  LaunchCommandSession,LaunchCommandOverview,LaunchRunbookStep,LaunchCommandEvent,
  LaunchTrafficOverride,DailyFinancialClose,LaunchRollbackDrill,LaunchEvidencePack,ExpansionReview,PostLaunchSummary,
  VerifyOtpResponse,
} from "./types";

function qs(values:Record<string,string|number|boolean|null|undefined>){
  const q=new URLSearchParams();
  for(const [k,v] of Object.entries(values))if(v!==undefined&&v!==null&&v!=="")q.set(k,String(v));
  const s=q.toString();return s?`?${s}`:"";
}

export const adminApi={
  sendOtp(phone:string){return request<{sent:boolean;development_otp?:string}>("/api/v1/auth/send-otp",{method:"POST",auth:false,body:JSON.stringify({phone})})},
  async verifyOtp(phone:string,code:string){
    const r=await request<VerifyOtpResponse>("/api/v1/auth/verify-otp",{method:"POST",auth:false,body:JSON.stringify({phone,code})});
    if(r.user.role!=="admin"){tokenStore.clear();throw new ApiError(403,"admin_role_required","هذا الحساب ليس حساب إدارة.")}
    tokenStore.set({accessToken:r.access_token,refreshToken:r.refresh_token});return r;
  },
  async logout(){
    const pair=tokenStore.get();
    try{if(pair)await request("/api/v1/auth/logout",{method:"POST",auth:false,body:JSON.stringify({refresh_token:pair.refreshToken})})}
    finally{tokenStore.clear()}
  },
  profile(){return request<AdminProfile>("/api/v1/admin/profile")},
  overview(dateFrom?:string,dateTo?:string){return request<DashboardOverview>(`/api/v1/admin/dashboard/overview${qs({date_from:dateFrom,date_to:dateTo})}`)},
  orders(filters:{status?:string;dateFrom?:string;dateTo?:string;limit?:number;offset?:number}={}) {
    return request<OrderListItem[]>(`/api/v1/admin/orders${qs({status:filters.status,date_from:filters.dateFrom,date_to:filters.dateTo,limit:filters.limit??100,offset:filters.offset??0})}`);
  },
  order(id:string){return request<OrderDetail>(`/api/v1/admin/orders/${id}`)},
  addOrderNote(id:string,note:string){return request(`/api/v1/admin/orders/${id}/notes`,{method:"POST",body:JSON.stringify({note})})},
  refunds(id:string){return request<Refund[]>(`/api/v1/admin/orders/${id}/refunds`)},
  createRefund(id:string,amountMinor:number,reason:string){
    return request<Refund>(`/api/v1/admin/orders/${id}/refunds`,{method:"POST",body:JSON.stringify({amount_minor:amountMinor,reason,idempotency_key:`admin-ui-${id}-${Date.now()}`})});
  },
  chefs(status?:string){return request<ChefListItem[]>(`/api/v1/admin/chefs${qs({status,limit:100})}`)},
  chef(id:string){return request<ChefDetail>(`/api/v1/admin/chefs/${id}`)},
  updateChefStatus(id:string,status:string,reason:string|null){return request<ChefDetail>(`/api/v1/admin/chefs/${id}/status`,{method:"PATCH",body:JSON.stringify({status,reason})})},
  drivers(status?:string){return request<DriverListItem[]>(`/api/v1/admin/drivers${qs({status,limit:100})}`)},
  driver(id:string){return request<DriverDetail>(`/api/v1/admin/drivers/${id}`)},
  supportSummary(){return request<SupportSummary>("/api/v1/admin/support/workload-summary")},
  tickets(status?:string){return request<SupportTicket[]>(`/api/v1/admin/support/tickets${qs({status})}`)},
  ticket(id:string){return request<SupportTicket>(`/api/v1/admin/support/tickets/${id}`)},
  assignTicket(id:string,adminId:string|null){return request<SupportTicket>(`/api/v1/admin/support/tickets/${id}/assign`,{method:"POST",body:JSON.stringify({admin_id:adminId})})},
  messageTicket(id:string,body:string,isInternal:boolean){return request<SupportTicket>(`/api/v1/admin/support/tickets/${id}/messages`,{method:"POST",body:JSON.stringify({body,is_internal:isInternal,attachment_ids:[]})})},
  updateTicketStatus(id:string,status:string,resolutionCode?:string,resolutionNote?:string){return request<SupportTicket>(`/api/v1/admin/support/tickets/${id}/status`,{method:"PATCH",body:JSON.stringify({status,resolution_code:resolutionCode||null,resolution_note:resolutionNote||null})})},
  finance(dateFrom?:string,dateTo?:string){return request<FinanceSummary>(`/api/v1/admin/finance/summary${qs({date_from:dateFrom,date_to:dateTo})}`)},
  daily(days=30){return request<DailyMetric[]>(`/api/v1/admin/analytics/daily?days=${days}`)},
  funnel(days=30){return request<Funnel>(`/api/v1/admin/analytics/funnel?days=${days}`)},
  retention(days=90){return request<Retention>(`/api/v1/admin/analytics/retention?days=${days}`)},

  refreshControlRoom(){return request<{detected:number;created:number;updated:number;auto_resolved:number;active_incidents:number}>("/api/v1/admin/control-room/incidents/refresh",{method:"POST"})},
  controlRoomOverview(){return request<ControlRoomOverview>("/api/v1/admin/control-room/overview")},
  controlRoomKpis(days=7){return request<LaunchKpis>(`/api/v1/admin/control-room/kpis?days=${days}`)},
  dailyBrief(){return request<DailyBrief>("/api/v1/admin/control-room/daily-brief")},
  incidents(filters:{status?:string;severity?:string;category?:string}={}){return request<OperationsIncident[]>(`/api/v1/admin/control-room/incidents${qs(filters)}`)},
  acknowledgeIncident(id:string){return request<OperationsIncident>(`/api/v1/admin/control-room/incidents/${id}/acknowledge`,{method:"POST"})},
  assignIncident(id:string,adminId?:string|null){return request<OperationsIncident>(`/api/v1/admin/control-room/incidents/${id}/assign`,{method:"POST",body:JSON.stringify({admin_id:adminId??null})})},
  escalateIncident(id:string,note?:string){return request<OperationsIncident>(`/api/v1/admin/control-room/incidents/${id}/escalate`,{method:"POST",body:JSON.stringify({note:note||null})})},
  resolveIncident(id:string,note:string){return request<OperationsIncident>(`/api/v1/admin/control-room/incidents/${id}/resolve`,{method:"POST",body:JSON.stringify({note})})},


  pilotPrograms(){return request<PilotProgram[]>("/api/v1/admin/pilot/programs")},
  createPilotProgram(payload:{name:string;area:string|null;start_date:string;end_date:string|null;required_stability_weeks:number;rating_target:number;repeat_customer_target_pct:number;on_time_target_pct:number;cancellation_max_pct:number;notes:string|null}){return request<PilotProgram>("/api/v1/admin/pilot/programs",{method:"POST",body:JSON.stringify(payload)})},
  pilotProgram(id:string){return request<PilotProgram>(`/api/v1/admin/pilot/programs/${id}`)},
  activatePilotProgram(id:string){return request<PilotProgram>(`/api/v1/admin/pilot/programs/${id}/activate`,{method:"POST"})},
  completePilotProgram(id:string){return request<PilotProgram>(`/api/v1/admin/pilot/programs/${id}/complete`,{method:"POST"})},
  refreshPilotProgram(id:string){return request<PilotWeeklySnapshot[]>(`/api/v1/admin/pilot/programs/${id}/refresh`,{method:"POST"})},
  pilotStability(id:string){return request<PilotStabilityReport>(`/api/v1/admin/pilot/programs/${id}/stability`)},
  pilotCohorts(id:string,weeks=8){return request<PilotCohortReport>(`/api/v1/admin/pilot/programs/${id}/cohorts?weeks=${weeks}`)},
  pilotEvidence(id:string){return request<PilotQaEvidence[]>(`/api/v1/admin/pilot/programs/${id}/evidence`)},
  upsertPilotEvidence(id:string,type:string,payload:{status:string;reference:string|null;notes:string|null;observed_at?:string|null}){return request<PilotQaEvidence>(`/api/v1/admin/pilot/programs/${id}/evidence/${encodeURIComponent(type)}`,{method:"PUT",body:JSON.stringify(payload)})},
  pilotPostReport(id:string){return request<PilotPostPilotReport>(`/api/v1/admin/pilot/programs/${id}/post-pilot`)},


  economicsCosts(filters:{programId?:string;orderId?:string;verified?:boolean}={}){return request<EconomicsCostEntry[]>(`/api/v1/admin/economics/costs${qs({program_id:filters.programId,order_id:filters.orderId,verified:filters.verified})}`)},
  createEconomicsCost(payload:{pilot_program_id:string|null;order_id:string|null;area:string|null;incurred_on:string;cost_type:string;amount_minor:number;currency:"EGP";source:"manual"|"provider"|"import";external_reference:string|null;note:string|null}){return request<EconomicsCostEntry>("/api/v1/admin/economics/costs",{method:"POST",body:JSON.stringify(payload)})},
  verifyEconomicsCost(id:string){return request<EconomicsCostEntry>(`/api/v1/admin/economics/costs/${id}/verify`,{method:"POST"})},
  economicsReport(programId:string){return request<EconomicsReport>(`/api/v1/admin/economics/programs/${programId}/report`)},
  expansionZones(){return request<ExpansionZoneDetail[]>("/api/v1/admin/economics/zones")},
  createExpansionZone(payload:{area:string;source_program_id:string;min_delivered_orders:number|null;min_contribution_margin_pct:number|null;min_operational_profit_minor:number;notes:string|null}){return request<ExpansionZone>("/api/v1/admin/economics/zones",{method:"POST",body:JSON.stringify(payload)})},
  assessExpansionZone(id:string){return request<ExpansionAssessment>(`/api/v1/admin/economics/zones/${id}/assess`,{method:"POST"})},
  approveExpansionZone(id:string){return request<ExpansionZone>(`/api/v1/admin/economics/zones/${id}/approve`,{method:"POST"})},
  launchExpansionZone(id:string){return request<ExpansionZone>(`/api/v1/admin/economics/zones/${id}/launch`,{method:"POST"})},
  pauseExpansionZone(id:string){return request<ExpansionZone>(`/api/v1/admin/economics/zones/${id}/pause`,{method:"POST"})},


  providerCostImports(filters:{provider?:string;status?:string}={}){return request<ProviderCostImportBatch[]>(`/api/v1/admin/economics/imports${qs(filters)}`)},
  providerCostImport(id:string){return request<ProviderCostImportDetail>(`/api/v1/admin/economics/imports/${id}`)},
  createProviderCostImport(payload:unknown){return request<ProviderCostImportDetail>("/api/v1/admin/economics/imports",{method:"POST",body:JSON.stringify(payload)})},
  validateProviderCostImport(id:string){return request<ProviderCostImportDetail>(`/api/v1/admin/economics/imports/${id}/validate`,{method:"POST"})},
  applyProviderCostImport(id:string){return request<ProviderCostImportDetail>(`/api/v1/admin/economics/imports/${id}/apply`,{method:"POST"})},
  syncTwilioUsage(payload:unknown){return request<ProviderCostImportDetail>("/api/v1/admin/economics/providers/twilio/sync",{method:"POST",body:JSON.stringify(payload)})},
  settlementBatches(status?:string){return request<SettlementBatch[]>(`/api/v1/admin/economics/settlements${qs({status})}`)},
  settlementBatch(id:string){return request<SettlementBatchDetail>(`/api/v1/admin/economics/settlements/${id}`)},
  createSettlementBatch(payload:unknown){return request<SettlementBatchDetail>("/api/v1/admin/economics/settlements",{method:"POST",body:JSON.stringify(payload)})},
  reconcileSettlementBatch(id:string){return request<SettlementBatchDetail>(`/api/v1/admin/economics/settlements/${id}/reconcile`,{method:"POST"})},
  zoneBudgetSummary(zoneId:string){return request<ZoneBudgetSummary>(`/api/v1/admin/economics/zones/${zoneId}/budgets`)},
  upsertZoneBudget(zoneId:string,payload:{category:string;allocated_minor:number;note:string|null}){return request<ZoneBudget>(`/api/v1/admin/economics/zones/${zoneId}/budgets`,{method:"PUT",body:JSON.stringify(payload)})},
  moveZoneBudget(id:string,payload:{action:"commit"|"release"|"spend";amount_minor:number;note:string|null}){return request<ZoneBudget>(`/api/v1/admin/economics/budgets/${id}/movement`,{method:"POST",body:JSON.stringify(payload)})},
  startZoneRollout(zoneId:string,dailyOrderCap?:number|null){return request<RolloutResponse>(`/api/v1/admin/economics/zones/${zoneId}/rollout/start`,{method:"POST",body:JSON.stringify({daily_order_cap:dailyOrderCap??null})})},
  advanceZoneRollout(zoneId:string,dailyOrderCap?:number|null){return request<RolloutResponse>(`/api/v1/admin/economics/zones/${zoneId}/rollout/advance`,{method:"POST",body:JSON.stringify({daily_order_cap:dailyOrderCap??null})})},
  pauseZoneRollout(zoneId:string){return request<RolloutResponse>(`/api/v1/admin/economics/zones/${zoneId}/rollout/pause`,{method:"POST"})},
  resumeZoneRollout(zoneId:string){return request<RolloutResponse>(`/api/v1/admin/economics/zones/${zoneId}/rollout/resume`,{method:"POST"})},


  trafficZones(){return request<TrafficZoneOverview[]>("/api/v1/admin/traffic/zones")},
  trafficPolicy(zoneId:string){return request<TrafficPolicy>(`/api/v1/admin/traffic/zones/${zoneId}/policy`)},
  updateTrafficPolicy(zoneId:string,payload:{is_enabled:boolean;hourly_order_cap:number|null;chef_daily_order_cap:number|null;enforce_rollout_bucket:boolean;warning_utilization_pct:number;critical_utilization_pct:number;rejection_spike_pct:number;rejection_spike_min_attempts:number;slo_auto_pause_enabled:boolean;slo_consecutive_red_snapshots:number;note:string|null}){return request<TrafficPolicy>(`/api/v1/admin/traffic/zones/${zoneId}/policy`,{method:"PUT",body:JSON.stringify(payload)})},
  updateTrafficCaps(zoneId:string,payload:{daily_order_cap?:number|null;hourly_order_cap?:number|null;chef_daily_order_cap?:number|null}){return request<{zone_id:string;daily_order_cap:number|null;hourly_order_cap:number|null;chef_daily_order_cap:number|null}>(`/api/v1/admin/traffic/zones/${zoneId}/caps`,{method:"PATCH",body:JSON.stringify(payload)})},
  refreshTrafficMonitoring(zoneId:string){return request<TrafficMonitoringSnapshot>(`/api/v1/admin/traffic/zones/${zoneId}/monitoring/refresh`,{method:"POST"})},
  trafficMonitoring(zoneId:string,limit=50){return request<TrafficMonitoringSnapshot[]>(`/api/v1/admin/traffic/zones/${zoneId}/monitoring?limit=${limit}`)},
  trafficForecasts(zoneId:string,limit=50){return request<CapacityForecast[]>(`/api/v1/admin/traffic/zones/${zoneId}/capacity-forecasts?limit=${limit}`)},
  trafficAdmissions(zoneId:string,limit=100){return request<TrafficAdmissionEvent[]>(`/api/v1/admin/traffic/zones/${zoneId}/admissions?limit=${limit}`)},

  vendorAccountingSummary(){return request<VendorAccountingSummary>("/api/v1/admin/vendor-accounting/summary")},
  importReviewQueue(reviewStatus?:string){return request<ImportReviewItem[]>(`/api/v1/admin/vendor-accounting/import-reviews${qs({review_status:reviewStatus,limit:500})}`)},
  assignImportReview(id:string,adminId:string|null){return request<ImportReviewItem>(`/api/v1/admin/vendor-accounting/imports/${id}/assign`,{method:"POST",body:JSON.stringify({admin_id:adminId})})},
  approveImportReview(id:string,note:string){return request<ImportReviewItem>(`/api/v1/admin/vendor-accounting/imports/${id}/approve`,{method:"POST",body:JSON.stringify({note})})},
  rejectImportReview(id:string,note:string){return request<ImportReviewItem>(`/api/v1/admin/vendor-accounting/imports/${id}/reject`,{method:"POST",body:JSON.stringify({note})})},
  settlementOperationsQueue(operationsStatus?:string){return request<SettlementOperationsItem[]>(`/api/v1/admin/vendor-accounting/settlements${qs({operations_status:operationsStatus,limit:500})}`)},
  assignSettlementOperation(id:string,adminId:string|null){return request<SettlementOperationsItem>(`/api/v1/admin/vendor-accounting/settlements/${id}/assign`,{method:"POST",body:JSON.stringify({admin_id:adminId})})},
  closeSettlementOperation(id:string,note:string){return request<SettlementOperationsItem>(`/api/v1/admin/vendor-accounting/settlements/${id}/close`,{method:"POST",body:JSON.stringify({note})})},
  reopenSettlementOperation(id:string,note:string){return request<SettlementOperationsItem>(`/api/v1/admin/vendor-accounting/settlements/${id}/reopen`,{method:"POST",body:JSON.stringify({note})})},


  launchSessions(limit=100){return request<LaunchCommandSession[]>(`/api/v1/admin/launch-command/sessions?limit=${limit}`)},
  createLaunchSession(payload:{pilot_program_id:string;zone_id:string;launch_date:string;incident_commander_admin_id:string;finance_admin_id:string|null;operations_admin_id:string|null;notes:string|null}){return request<LaunchCommandSession>("/api/v1/admin/launch-command/sessions",{method:"POST",body:JSON.stringify(payload)})},
  launchOverview(id:string){return request<LaunchCommandOverview>(`/api/v1/admin/launch-command/sessions/${id}`)},
  startLaunchSession(id:string){return request<LaunchCommandSession>(`/api/v1/admin/launch-command/sessions/${id}/start`,{method:"POST"})},
  pauseLaunchSession(id:string){return request<LaunchCommandSession>(`/api/v1/admin/launch-command/sessions/${id}/pause`,{method:"POST"})},
  resumeLaunchSession(id:string){return request<LaunchCommandSession>(`/api/v1/admin/launch-command/sessions/${id}/resume`,{method:"POST"})},
  abortLaunchSession(id:string){return request<LaunchCommandSession>(`/api/v1/admin/launch-command/sessions/${id}/abort`,{method:"POST"})},
  completeLaunchSession(id:string){return request<LaunchCommandSession>(`/api/v1/admin/launch-command/sessions/${id}/complete`,{method:"POST"})},
  launchRunbook(id:string){return request<LaunchRunbookStep[]>(`/api/v1/admin/launch-command/sessions/${id}/runbook`)},
  updateLaunchRunbook(id:string,stepKey:string,payload:{status:string;evidence_reference:string|null;note:string|null}){return request<LaunchRunbookStep>(`/api/v1/admin/launch-command/sessions/${id}/runbook/${stepKey}`,{method:"POST",body:JSON.stringify(payload)})},
  launchEvents(id:string,limit=200){return request<LaunchCommandEvent[]>(`/api/v1/admin/launch-command/sessions/${id}/events?limit=${limit}`)},
  launchOverrides(id:string){return request<LaunchTrafficOverride[]>(`/api/v1/admin/launch-command/sessions/${id}/traffic-overrides`)},
  createLaunchOverride(id:string,payload:{override_type:string;value:number|boolean;duration_minutes:number;reason:string}){return request<LaunchTrafficOverride>(`/api/v1/admin/launch-command/sessions/${id}/traffic-overrides`,{method:"POST",body:JSON.stringify(payload)})},
  revertLaunchOverride(id:string){return request<LaunchTrafficOverride>(`/api/v1/admin/launch-command/traffic-overrides/${id}/revert`,{method:"POST"})},
  financialCloses(id:string){return request<DailyFinancialClose[]>(`/api/v1/admin/launch-command/sessions/${id}/financial-closes`)},
  prepareFinancialClose(id:string,closeDate:string,note:string|null){return request<DailyFinancialClose>(`/api/v1/admin/launch-command/sessions/${id}/financial-closes/prepare`,{method:"POST",body:JSON.stringify({close_date:closeDate,note})})},
  closeFinancialDay(id:string,note:string){return request<DailyFinancialClose>(`/api/v1/admin/launch-command/financial-closes/${id}/close`,{method:"POST",body:JSON.stringify({note})})},
  reopenFinancialDay(id:string,note:string){return request<DailyFinancialClose>(`/api/v1/admin/launch-command/financial-closes/${id}/reopen`,{method:"POST",body:JSON.stringify({note})})},
  rollbackDrills(id:string){return request<LaunchRollbackDrill[]>(`/api/v1/admin/launch-command/sessions/${id}/rollback-drills`)},
  startRollbackDrill(id:string,payload:{mode:string;target_recovery_seconds:number|null;note:string|null}){return request<LaunchRollbackDrill>(`/api/v1/admin/launch-command/sessions/${id}/rollback-drills`,{method:"POST",body:JSON.stringify(payload)})},
  completeRollbackDrill(id:string,payload:{passed:boolean;evidence_reference:string;note:string|null}){return request<LaunchRollbackDrill>(`/api/v1/admin/launch-command/rollback-drills/${id}/complete`,{method:"POST",body:JSON.stringify(payload)})},
  launchEvidencePacks(id:string){return request<LaunchEvidencePack[]>(`/api/v1/admin/launch-command/sessions/${id}/evidence-packs`)},
  generateLaunchEvidencePack(id:string){return request<LaunchEvidencePack>(`/api/v1/admin/launch-command/sessions/${id}/evidence-packs`,{method:"POST"})},

  postLaunchReviews(zoneId?:string,limit=200){return request<ExpansionReview[]>(`/api/v1/admin/post-launch/reviews${qs({zone_id:zoneId,limit})}`)},
  refreshPostLaunchReview(zoneId:string){return request<ExpansionReview>(`/api/v1/admin/post-launch/zones/${zoneId}/review`,{method:"POST"})},
  postLaunchSummary(){return request<PostLaunchSummary>("/api/v1/admin/post-launch/summary")},

  audit(limit=100){return request<AuditItem[]>(`/api/v1/admin/audit?limit=${limit}`)},
};

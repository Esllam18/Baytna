export interface VerifyOtpResponse {
  access_token:string;
  refresh_token:string;
  token_type:string;
  user:{id:string;phone:string;role:string};
}

export interface AdminProfile {
  id:string;
  phone:string;
  role:string;
  is_active:boolean;
}

export interface DashboardOverview {
  date_from:string; date_to:string;
  orders_total:number; active_orders:number; delivered_orders:number; cancelled_orders:number;
  gmv_minor:number; captured_payments_minor:number; refunds_minor:number; net_collected_minor:number;
  average_order_value_minor:number; open_support_tickets:number;
  active_chefs:number; verified_chefs:number; available_drivers:number; on_mission_drivers:number;
  delivery_success_rate_pct:number;
}

export interface OrderListItem {
  id:string; customer_id:string; customer_name:string|null; customer_phone_masked:string;
  chef_id:string; chef_name:string; service_date:string; status:string;
  subtotal_minor:number; discount_minor:number; total_minor:number; currency:string;
  payment_status:string|null; delivery_status:string|null;
  promised_delivery_window_start_at:string|null; promised_delivery_window_end_at:string|null;
  promised_delivery_timezone:string|null; created_at:string;
}
export interface OrderNote {id:string;order_id:string;admin_user_id:string|null;note:string;created_at:string}
export interface OrderDetail {
  order:OrderListItem;
  items:Record<string,unknown>[];
  pricing_adjustments:Record<string,unknown>[];
  payment:Record<string,unknown>|null;
  refunds:Record<string,unknown>[];
  delivery:Record<string,unknown>|null;
  delivery_address:Record<string,unknown>|null;
  timeline:Record<string,unknown>[];
  support_tickets:Record<string,unknown>[];
  notes:OrderNote[];
}

export interface ChefListItem {
  id:string; display_name:string; specialty:string; area:string; status:string; rating:number;
  is_verified:boolean; is_open_today:boolean; total_orders:number; delivered_orders:number; created_at:string;
}
export interface ChefDetail extends ChefListItem {
  active_orders:number; dishes_count:number; reviews_count:number; avg_food_quality:number; open_support_tickets:number;
}

export interface DriverListItem {
  id:string; status:string; rating:number; active_mission_id:string|null;
  delivered_missions:number; issue_missions:number; created_at:string;
}
export interface DriverDetail extends DriverListItem {
  total_missions:number; current_mission:Record<string,unknown>|null;
}

export interface SupportSummary {
  total_open:number; new:number; assigned:number; investigating:number;
  awaiting_customer:number; awaiting_internal:number; urgent_open:number; unassigned_open:number;
}
export interface SupportMessage {
  id:string; sender_role:string; body:string; is_internal:boolean; created_at:string;
  attachments:{media_asset_id:string;mime_type:string;filename:string|null}[];
}
export interface SupportTicket {
  id:string; customer_id:string; order_id:string|null; assigned_admin_id:string|null;
  category:string; subject:string; description:string; priority:string; status:string;
  resolution_code:string|null; resolution_note:string|null; created_at:string; updated_at:string;
  resolved_at:string|null; closed_at:string|null; messages:SupportMessage[];
}

export interface FinanceSummary {
  date_from:string; date_to:string;
  successful_payments_count:number; captured_minor:number; refunds_count:number; refunded_minor:number;
  net_collected_minor:number; pending_payments_count:number; failed_payments_count:number;
  coupon_discount_minor:number; loyalty_discount_minor:number; subscription_discount_minor:number;
}
export interface DailyMetric {
  day:string; orders_created:number; delivered_orders:number; cancelled_orders:number;
  gmv_minor:number; captured_minor:number; refunds_minor:number;
}
export interface Funnel {
  orders_created:number; reached_confirmed:number; reached_accepted_by_chef:number;
  reached_ready_for_pickup:number; reached_assigned_to_driver:number; reached_picked_up:number;
  reached_out_for_delivery:number; reached_delivered:number;
}
export interface Retention {
  delivered_orders:number; unique_customers:number; repeat_customers:number;
  repeat_customer_rate_pct:number; average_delivered_orders_per_customer:number;
}
export interface Refund {
  id:string;order_id:string;payment_id:string;amount_minor:number;reason:string;status:string;
  provider_reference:string|null;provider_status:string|null;provider_error:string|null;
  created_at:string;completed_at:string|null;failed_at:string|null;
}
export interface AuditItem {
  id:number; actor_user_id:string|null; action:string; entity_type:string|null;
  entity_id:string|null; request_id:string|null; metadata_json:Record<string,unknown>; created_at:string;
}


export interface OperationsIncident {
  id:string;
  fingerprint:string;
  category:"chef_sla"|"delivery_sla"|"support_sla"|"payment"|"reliability"|"notifications"|string;
  severity:"info"|"warning"|"high"|"critical"|string;
  status:"open"|"acknowledged"|"resolved"|string;
  source_type:string;
  source_id:string|null;
  title:string;
  message:string;
  details_json:Record<string,unknown>;
  owner_admin_id:string|null;
  detected_at:string;
  last_detected_at:string;
  acknowledged_at:string|null;
  acknowledged_by_admin_id:string|null;
  resolved_at:string|null;
  resolved_by_admin_id:string|null;
  resolution_note:string|null;
  created_at:string;
  updated_at:string;
}

export interface LaunchKpis {
  days:number;
  orders_created:number;
  delivered_orders:number;
  cancelled_orders:number;
  cancellation_rate_pct:number;
  delivery_success_rate_pct:number;
  gmv_minor:number;
  repeat_customer_rate_pct:number;
  average_chef_rating:number;
  reviews_count:number;
  chef_acceptance_sla_breaches:number;
  support_sla_breaches:number;
  payment_reconciliation_open:number;
  notification_dead_letters:number;
  outbox_dead_letters:number;
  background_job_dead_letters:number;
  stale_workers:number;
  launch_target_rating_met:boolean;
  launch_target_repeat_met:boolean;
  on_time_delivery_rate_pct:number|null;
  on_time_measurable_deliveries:number;
  late_deliveries:number;
  delivery_promise_coverage_pct:number;
  launch_target_on_time_met:boolean|null;
  launch_target_cancellation_met:boolean;
}

export interface ControlRoomOverview {
  generated_at:string;
  health:"green"|"amber"|"red"|string;
  active_incidents:number;
  critical_incidents:number;
  high_incidents:number;
  unacknowledged_incidents:number;
  urgent_support_open:number;
  open_payment_reconciliation:number;
  worker_status:string;
  kpis:LaunchKpis;
  top_incidents:OperationsIncident[];
}

export interface DailyActionItem {
  priority:string;
  title:string;
  detail:string;
  route:string|null;
}

export interface DailyBrief {
  day:string;
  generated_at:string;
  health:string;
  opening_orders:number;
  delivered_orders:number;
  cancelled_orders:number;
  gmv_minor:number;
  active_incidents:number;
  critical_incidents:number;
  urgent_support_open:number;
  available_drivers:number;
  open_chefs:number;
  actions:DailyActionItem[];
}

export interface PilotProgram {
  id:string;
  name:string;
  area:string|null;
  start_date:string;
  end_date:string|null;
  status:"planned"|"active"|"completed"|"archived"|string;
  required_stability_weeks:number;
  rating_target:number;
  repeat_customer_target_pct:number;
  on_time_target_pct:number;
  cancellation_max_pct:number;
  notes:string|null;
  created_by_admin_id:string|null;
  activated_at:string|null;
  completed_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface PilotWeeklySnapshot {
  id:string;
  program_id:string;
  week_index:number;
  week_start:string;
  week_end:string;
  is_full_week:boolean;
  is_complete:boolean;
  orders_created:number;
  delivered_orders:number;
  cancelled_orders:number;
  cancellation_rate_pct:number;
  unique_customers:number;
  repeat_customers:number;
  repeat_customer_rate_pct:number;
  average_chef_rating:number|null;
  reviews_count:number;
  on_time_delivery_rate_pct:number|null;
  on_time_measurable_deliveries:number;
  late_deliveries:number;
  delivery_promise_coverage_pct:number;
  gmv_minor:number;
  captured_minor:number;
  refunded_minor:number;
  net_collected_minor:number;
  support_tickets:number;
  refund_count:number;
  refund_rate_pct:number;
  rating_met:boolean|null;
  repeat_met:boolean|null;
  on_time_met:boolean|null;
  cancellation_met:boolean|null;
  week_evaluable:boolean;
  week_passed:boolean|null;
  generated_at:string;
}

export interface PilotStabilityReport {
  program:PilotProgram;
  required_weeks:number;
  complete_full_weeks:number;
  evaluable_weeks:number;
  passed_weeks:number;
  current_consecutive_passed_weeks:number;
  max_consecutive_passed_weeks:number;
  stability_gate_met:boolean;
  blockers:string[];
  weeks:PilotWeeklySnapshot[];
}

export interface CohortRetentionCell {
  week_offset:number;
  active_customers:number;
  retention_pct:number;
}
export interface PilotCohortRow {
  cohort_week:number;
  cohort_start:string;
  cohort_end:string;
  cohort_size:number;
  retention:CohortRetentionCell[];
}
export interface PilotCohortReport {
  program_id:string;
  max_weeks:number;
  acquired_customers:number;
  cohorts:PilotCohortRow[];
}

export interface PilotQaEvidence {
  id:string;
  program_id:string;
  evidence_type:string;
  status:"pending"|"passed"|"failed"|"not_applicable"|string;
  reference:string|null;
  notes:string|null;
  observed_at:string|null;
  verified_by_admin_id:string|null;
  created_at:string;
  updated_at:string;
}

export interface PilotPostPilotReport {
  program:PilotProgram;
  generated_at:string;
  duration_days:number;
  orders_created:number;
  delivered_orders:number;
  cancelled_orders:number;
  cancellation_rate_pct:number;
  gmv_minor:number;
  captured_minor:number;
  refunded_minor:number;
  net_collected_minor:number;
  average_order_value_minor:number;
  unique_delivered_customers:number;
  repeat_customer_rate_pct:number;
  average_chef_rating:number|null;
  reviews_count:number;
  on_time_delivery_rate_pct:number|null;
  delivery_promise_coverage_pct:number;
  support_tickets:number;
  support_tickets_per_100_orders:number;
  refunds_count:number;
  refund_rate_pct:number;
  active_critical_incidents:number;
  open_payment_reconciliation_issues:number;
  acquired_customer_cohorts:number;
  weighted_w1_retention_pct:number|null;
  weighted_w4_retention_pct:number|null;
  stability_gate_met:boolean;
  current_consecutive_passed_weeks:number;
  required_stability_weeks:number;
  profitability_calculated_from_backend:boolean;
  operational_profit_evidence_status:string;
  qa_exit_evidence_status:string;
  operations_signoff_status:string;
  scale_ready:boolean;
  scale_blockers:string[];
}


export interface EconomicsCostEntry {
  id:string;
  pilot_program_id:string|null;
  order_id:string|null;
  area:string|null;
  incurred_on:string;
  cost_type:string;
  cost_scope:"variable"|"fixed"|string;
  amount_minor:number;
  currency:string;
  source:string;
  external_reference:string|null;
  note:string|null;
  is_verified:boolean;
  verified_by_admin_id:string|null;
  verified_at:string|null;
  created_by_admin_id:string|null;
  created_at:string;
  updated_at:string;
}

export interface EconomicsReport {
  program_id:string;
  area:string|null;
  period_start:string;
  period_end:string;
  delivered_orders:number;
  delivered_gmv_minor:number;
  succeeded_payment_orders:number;
  captured_minor:number;
  refunded_minor:number;
  net_collected_minor:number;
  revenue_coverage_pct:number;
  variable_cost_minor:number;
  fixed_cost_minor:number;
  contribution_minor:number;
  contribution_margin_pct:number|null;
  contribution_per_delivered_order_minor:number|null;
  operational_profit_minor:number;
  operational_profit_margin_pct:number|null;
  required_order_cost_types:string[];
  fully_costed_delivered_orders:number;
  cost_coverage_pct:number;
  unverified_cost_entries:number;
  cost_breakdown:{cost_type:string;amount_minor:number}[];
  economics_evaluable:boolean;
  operational_profit_positive:boolean|null;
  blockers:string[];
  generated_at:string;
}

export interface ExpansionZone {
  id:string;
  area:string;
  source_program_id:string;
  status:string;
  min_delivered_orders:number;
  min_contribution_margin_pct:number;
  min_operational_profit_minor:number;
  notes:string|null;
  created_by_admin_id:string|null;
  approved_by_admin_id:string|null;
  approved_at:string|null;
  launched_at:string|null;
  paused_at:string|null;
  rollout_stage:string;
  rollout_percent:number;
  daily_order_cap:number|null;
  rollout_started_at:string|null;
  rollout_completed_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface ExpansionAssessment {
  id:string;
  zone_id:string;
  program_id:string;
  period_start:string;
  period_end:string;
  delivered_orders:number;
  net_collected_minor:number;
  variable_cost_minor:number;
  contribution_minor:number;
  contribution_margin_pct:number|null;
  fixed_cost_minor:number;
  operational_profit_minor:number;
  cost_coverage_pct:number;
  revenue_coverage_pct:number;
  unverified_cost_entries:number;
  economics_evaluable:boolean;
  stability_gate_met:boolean;
  post_pilot_scale_ready:boolean;
  decision:"ready"|"blocked"|string;
  blockers_json:string[];
  generated_at:string;
  generated_by_admin_id:string|null;
}

export interface ExpansionZoneDetail {
  zone:ExpansionZone;
  latest_assessment:ExpansionAssessment|null;
}


export interface ProviderCostImportBatch {
  id:string;
  provider:string;
  pilot_program_id:string|null;
  area:string|null;
  period_start:string;
  period_end:string;
  source_currency:string;
  fx_rate_to_egp:number|null;
  fx_reference:string|null;
  external_reference:string;
  checksum_sha256:string;
  status:string;
  rows_count:number;
  total_source_minor:number;
  total_egp_minor:number;
  applied_cost_entries:number;
  validation_errors_json:unknown[];
  review_status:string;
  assigned_reviewer_id:string|null;
  reviewed_by_admin_id:string|null;
  review_note:string|null;
  risk_flags_json:string[];
  reviewed_at:string|null;
  created_by_admin_id:string|null;
  validated_by_admin_id:string|null;
  applied_by_admin_id:string|null;
  validated_at:string|null;
  applied_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface ProviderCostImportLine {
  id:string;
  batch_id:string;
  line_key:string;
  order_id:string|null;
  incurred_on:string;
  cost_type:string;
  source_amount_minor:number;
  source_currency:string;
  egp_amount_minor:number;
  external_reference:string|null;
  description:string|null;
  raw_json:Record<string,unknown>;
  applied_cost_entry_id:string|null;
  created_at:string;
}

export interface ProviderCostImportDetail {
  batch:ProviderCostImportBatch;
  lines:ProviderCostImportLine[];
}

export interface SettlementBatch {
  id:string;
  provider:string;
  pilot_program_id:string|null;
  period_start:string;
  period_end:string;
  currency:string;
  external_reference:string;
  checksum_sha256:string;
  status:string;
  rows_count:number;
  matched_lines:number;
  mismatched_lines:number;
  gross_minor:number;
  fees_minor:number;
  refunds_minor:number;
  net_settlement_minor:number;
  blockers_json:string[];
  operations_status:string;
  assigned_admin_id:string|null;
  closed_by_admin_id:string|null;
  close_note:string|null;
  closed_at:string|null;
  created_by_admin_id:string|null;
  reconciled_by_admin_id:string|null;
  reconciled_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface SettlementLine {
  id:string;
  batch_id:string;
  provider_transaction_id:string;
  settlement_reference:string|null;
  gross_amount_minor:number;
  fee_minor:number;
  refund_minor:number;
  net_settlement_minor:number;
  currency:string;
  is_settled:boolean;
  settled_at:string|null;
  matched_payment_id:string|null;
  reconciliation_status:string;
  issues_json:string[];
  applied_cost_entry_id:string|null;
  raw_json:Record<string,unknown>;
  created_at:string;
}

export interface SettlementBatchDetail {
  batch:SettlementBatch;
  lines:SettlementLine[];
}

export interface ZoneBudget {
  id:string;
  zone_id:string;
  category:string;
  allocated_minor:number;
  committed_minor:number;
  spent_minor:number;
  currency:string;
  note:string|null;
  created_by_admin_id:string|null;
  updated_by_admin_id:string|null;
  created_at:string;
  updated_at:string;
  remaining_minor:number;
}

export interface ZoneBudgetSummary {
  zone_id:string;
  required_categories:string[];
  present_categories:string[];
  missing_categories:string[];
  allocated_minor:number;
  committed_minor:number;
  spent_minor:number;
  remaining_minor:number;
  budget_ready:boolean;
  budgets:ZoneBudget[];
}

export interface RolloutResponse {
  zone_id:string;
  zone_status:string;
  rollout_stage:string;
  rollout_percent:number;
  daily_order_cap:number|null;
  assessment_id:string|null;
  budget_ready:boolean;
  payment_reconciliation_open:number;
  blocked_settlement_batches:number;
  blockers:string[];
  event_id:string|null;
}


export interface TrafficPolicy {
  zone_id:string;
  is_enabled:boolean;
  hourly_order_cap:number|null;
  chef_daily_order_cap:number|null;
  enforce_rollout_bucket:boolean;
  warning_utilization_pct:number;
  critical_utilization_pct:number;
  rejection_spike_pct:number;
  rejection_spike_min_attempts:number;
  slo_auto_pause_enabled:boolean;
  slo_consecutive_red_snapshots:number;
  note:string|null;
  created_by_admin_id:string|null;
  updated_by_admin_id:string|null;
  created_at:string;
  updated_at:string;
}

export interface TrafficMonitoringSnapshot {
  id:string;
  zone_id:string;
  service_date:string;
  rollout_stage:string;
  rollout_percent:number;
  zone_daily_cap:number|null;
  admitted_orders_today:number;
  daily_utilization_pct:number;
  hourly_cap:number|null;
  admitted_orders_last_hour:number;
  hourly_utilization_pct:number;
  admission_attempts_last_hour:number;
  admission_rejections_last_hour:number;
  rejection_rate_pct:number;
  available_drivers:number;
  open_chefs:number;
  top_chef_orders:number;
  chef_daily_cap:number|null;
  top_chef_utilization_pct:number;
  health:"green"|"amber"|"red"|string;
  blockers_json:string[];
  generated_by:string;
  observed_at:string;
}

export interface CapacityForecast {
  id:string;
  zone_id:string;
  monitoring_snapshot_id:string;
  service_date:string;
  horizon_minutes:number;
  sample_count:number;
  current_orders_last_hour:number;
  projected_orders_next_hour:number;
  hourly_cap:number|null;
  projected_hourly_utilization_pct:number;
  current_daily_orders:number;
  daily_cap:number|null;
  daily_headroom_orders:number|null;
  projected_minutes_to_daily_cap:number|null;
  risk:"green"|"amber"|"red"|string;
  reasons_json:string[];
  generated_at:string;
}

export interface TrafficAdmissionEvent {
  id:string;
  zone_id:string;
  order_id:string|null;
  customer_id:string;
  chef_id:string;
  service_date:string;
  area:string;
  decision:"admitted"|"rejected"|string;
  reason:string;
  rollout_stage:string;
  rollout_percent:number;
  rollout_bucket:number|null;
  daily_cap:number|null;
  daily_usage_before:number;
  hourly_cap:number|null;
  hourly_usage_before:number;
  chef_daily_cap:number|null;
  chef_usage_before:number;
  request_id:string|null;
  created_at:string;
}

export interface TrafficZoneOverview {
  zone_id:string;
  area:string;
  zone_status:string;
  rollout_stage:string;
  rollout_percent:number;
  daily_order_cap:number|null;
  policy:TrafficPolicy;
  latest_monitoring:TrafficMonitoringSnapshot|null;
  latest_forecast:CapacityForecast|null;
}

export interface ImportReviewItem {
  id:string;
  provider:string;
  pilot_program_id:string|null;
  area:string|null;
  period_start:string;
  period_end:string;
  source_currency:string;
  external_reference:string;
  status:string;
  review_status:string;
  rows_count:number;
  total_egp_minor:number;
  applied_cost_entries:number;
  validation_errors_json:unknown[];
  risk_flags_json:string[];
  created_by_admin_id:string|null;
  assigned_reviewer_id:string|null;
  reviewed_by_admin_id:string|null;
  review_note:string|null;
  validated_at:string|null;
  reviewed_at:string|null;
  applied_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface SettlementOperationsItem {
  id:string;
  provider:string;
  pilot_program_id:string|null;
  period_start:string;
  period_end:string;
  external_reference:string;
  status:string;
  operations_status:string;
  rows_count:number;
  matched_lines:number;
  mismatched_lines:number;
  gross_minor:number;
  fees_minor:number;
  refunds_minor:number;
  net_settlement_minor:number;
  blockers_json:string[];
  created_by_admin_id:string|null;
  assigned_admin_id:string|null;
  reconciled_by_admin_id:string|null;
  closed_by_admin_id:string|null;
  close_note:string|null;
  reconciled_at:string|null;
  closed_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface VendorAccountingSummary {
  imports_pending_review:number;
  imports_assigned:number;
  imports_approved:number;
  imports_rejected:number;
  imports_high_risk_open:number;
  settlements_open:number;
  settlements_in_review:number;
  settlements_closed:number;
  settlements_reopened:number;
  settlements_blocked:number;
}


export interface LaunchCommandSession {
  id:string;
  pilot_program_id:string;
  zone_id:string;
  launch_date:string;
  status:string;
  incident_commander_admin_id:string;
  finance_admin_id:string|null;
  operations_admin_id:string|null;
  notes:string|null;
  created_by_admin_id:string;
  started_at:string|null;
  paused_at:string|null;
  completed_at:string|null;
  aborted_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface LaunchRunbookStep {
  id:string;
  session_id:string;
  step_key:string;
  sequence:number;
  category:string;
  title:string;
  is_required:boolean;
  status:string;
  evidence_reference:string|null;
  note:string|null;
  completed_by_admin_id:string|null;
  completed_at:string|null;
  created_at:string;
  updated_at:string;
}

export interface LaunchCommandEvent {
  id:string;
  session_id:string;
  event_type:string;
  severity:string;
  title:string;
  details_json:Record<string,unknown>;
  actor_admin_id:string|null;
  created_at:string;
}

export interface LaunchTrafficOverride {
  id:string;
  session_id:string;
  zone_id:string;
  override_type:string;
  previous_value_json:Record<string,unknown>;
  override_value_json:Record<string,unknown>;
  reason:string;
  status:string;
  expires_at:string;
  activated_by_admin_id:string;
  reverted_by_admin_id:string|null;
  activated_at:string;
  reverted_at:string|null;
}

export interface DailyFinancialClose {
  id:string;
  session_id:string;
  pilot_program_id:string;
  close_date:string;
  status:string;
  delivered_orders:number;
  succeeded_payment_orders:number;
  captured_minor:number;
  refunded_minor:number;
  net_collected_minor:number;
  verified_cost_minor:number;
  contribution_minor:number;
  operational_profit_minor:number;
  revenue_coverage_pct:number;
  cost_coverage_pct:number;
  unverified_cost_entries:number;
  pending_provider_imports:number;
  unclosed_settlements:number;
  open_payment_issues:number;
  blockers_json:string[];
  summary_json:Record<string,unknown>;
  checksum_sha256:string|null;
  prepared_by_admin_id:string|null;
  prepared_by_system:boolean;
  cadence_due_at:string|null;
  overdue_notified_at:string|null;
  closed_by_admin_id:string|null;
  reopened_by_admin_id:string|null;
  note:string|null;
  prepared_at:string;
  closed_at:string|null;
  reopened_at:string|null;
  updated_at:string;
}

export interface LaunchRollbackDrill {
  id:string;
  session_id:string;
  zone_id:string;
  mode:string;
  status:string;
  target_recovery_seconds:number;
  recovery_seconds:number|null;
  pre_state_json:Record<string,unknown>;
  result_json:Record<string,unknown>;
  evidence_reference:string|null;
  note:string|null;
  initiated_by_admin_id:string;
  verified_by_admin_id:string|null;
  started_at:string;
  completed_at:string|null;
}

export interface LaunchEvidencePack {
  id:string;
  session_id:string;
  status:string;
  release_version:string;
  migration_head:string;
  evidence_json:Record<string,unknown>;
  blockers_json:string[];
  checksum_sha256:string;
  retention_class:"working"|"final"|string;
  retain_until:string|null;
  generated_by_admin_id:string;
  generated_at:string;
}

export interface LaunchCommandOverview {
  session:LaunchCommandSession;
  zone_status:string;
  rollout_stage:string;
  rollout_percent:number;
  runbook_total:number;
  runbook_passed:number;
  runbook_blocking:number;
  active_overrides:number;
  latest_financial_close:DailyFinancialClose|null;
  latest_rollback_drill:LaunchRollbackDrill|null;
  latest_evidence_pack:LaunchEvidencePack|null;
}


export interface ExpansionReview {
  id:string;
  zone_id:string;
  session_id:string|null;
  review_date:string;
  window_start:string;
  window_end:string;
  status:"healthy"|"watch"|"blocked"|string;
  recommendation:"continue"|"hold"|"pause"|string;
  monitoring_snapshots:number;
  red_snapshots:number;
  amber_snapshots:number;
  auto_pause_events:number;
  required_closes:number;
  closed_closes:number;
  overdue_closes:number;
  blocked_closes:number;
  latest_forecast_risk:string|null;
  blockers_json:string[];
  evidence_json:Record<string,unknown>;
  generated_by:string;
  generated_at:string;
  updated_at:string;
}

export interface PostLaunchSummary {
  zones_reviewed:number;
  healthy:number;
  watch:number;
  blocked:number;
  continue_count:number;
  hold_count:number;
  pause_count:number;
  reviews:ExpansionReview[];
}

export interface ApiErrorEnvelope {
  error: { code: string; message: string; details?: unknown; request_id?: string | null };
}

export interface PublicUser { id: string; phone: string; role: string; }
export interface SendOtpResponse { challenge_expires_at: string; development_otp?: string | null; }
export interface VerifyOtpResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_at: string;
  refresh_token_expires_at: string;
  user: PublicUser;
}

export interface ChefSummary {
  id: string;
  display_name: string;
  specialty: string;
  area: string;
  rating: number;
  is_verified: boolean;
  is_open_today: boolean;
}

export interface Dish {
  id: string;
  chef_id: string;
  name: string;
  description: string;
  category: string;
  base_price_minor: number;
  prep_notice_hours: number;
  is_special_order_available: boolean;
  is_active: boolean;
  image_url: string | null;
  media_asset_id: string | null;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface DailyMenuItem {
  id: string;
  dish_id: string;
  name: string;
  description: string;
  category: string;
  price_minor: number;
  quantity_total: number;
  quantity_available: number;
  max_per_order: number;
  status: string;
  availability_label: string;
  image_url: string | null;
}

export interface TodayMenu {
  chef_id: string;
  service_date: string;
  kitchen_status: string;
  cutoff_at: string | null;
  delivery_window_start: string | null;
  delivery_window_end: string | null;
  items: DailyMenuItem[];
}

export interface HomeTodayItem extends DailyMenuItem {
  chef_id: string;
  chef_name: string;
}

export interface CustomerHomeResponse {
  customer: { id: string; phone: string };
  area: string;
  featured_chefs: ChefSummary[];
  today: { title: string; service_date: string; items: HomeTodayItem[] };
}

export interface CartLine {
  id: string;
  daily_menu_item_id: string | null;
  dish_id: string;
  dish_name: string;
  chef_id: string;
  unit_price_minor: number;
  quantity: number;
  line_total_minor: number;
  max_per_order: number;
  availability_label: string;
}

export interface CartResponse {
  id: string;
  customer_id: string;
  chef_id: string | null;
  service_date: string | null;
  status: string;
  subtotal_minor: number;
  currency: string;
  items: CartLine[];
}

export interface PricingQuote {
  cart_id: string;
  subtotal_minor: number;
  delivery_fee_minor: number;
  coupon_discount_minor: number;
  subscription_discount_minor: number;
  loyalty_discount_minor: number;
  total_discount_minor: number;
  total_minor: number;
  currency: string;
  coupon_code: string | null;
  loyalty_points_to_redeem: number;
  loyalty_balance_points: number;
  subscription_plan_id: string | null;
  subscription_plan_name: string | null;
  minimum_payable_minor: number;
}

export interface OrderLine {
  id: string;
  daily_menu_item_id: string | null;
  dish_id: string;
  dish_name: string;
  unit_price_minor: number;
  quantity: number;
  line_total_minor: number;
}

export interface OrderStatusEvent {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  created_at: string;
}

export interface PricingAdjustment {
  adjustment_type: string;
  reference_code: string | null;
  amount_minor: number;
  metadata_json?: Record<string, unknown>;
}

export interface OrderResponse {
  id: string;
  order_type: string;
  customer_id: string;
  chef_id: string;
  service_date: string;
  status: string;
  subtotal_minor: number;
  delivery_fee_minor: number;
  discount_minor: number;
  total_minor: number;
  currency: string;
  inventory_hold_expires_at: string | null;
  promised_delivery_window_start_at: string | null;
  promised_delivery_window_end_at: string | null;
  promised_delivery_timezone: string | null;
  delivery_promise_source: string | null;
  items: OrderLine[];
  timeline: OrderStatusEvent[];
  pricing_adjustments?: PricingAdjustment[];
  created_at: string;
}

export interface OrderListItem {
  id: string;
  order_type: string;
  chef_id: string;
  service_date: string;
  status: string;
  total_minor: number;
  currency: string;
  promised_delivery_window_start_at: string | null;
  promised_delivery_window_end_at: string | null;
  promised_delivery_timezone: string | null;
  created_at: string;
}

export interface Address {
  id: string;
  label: string | null;
  area: string;
  street: string | null;
  building: string | null;
  floor: string | null;
  apartment: string | null;
  latitude: string | null;
  longitude: string | null;
  is_default: boolean;
}

export interface AddressCreate {
  label?: string | null;
  area: string;
  street?: string | null;
  building?: string | null;
  floor?: string | null;
  apartment?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  is_default?: boolean;
}

export interface PaymentIntent {
  id: string;
  order_id: string;
  provider: string;
  provider_reference: string | null;
  provider_order_reference: string | null;
  provider_transaction_reference: string | null;
  provider_status: string | null;
  provider_last_seen_at: string | null;
  amount_minor: number;
  refunded_minor: number;
  currency: string;
  status: string;
  checkout_url: string | null;
  expires_at: string;
  succeeded_at: string | null;
  failed_at: string | null;
  created_at: string;
}

export interface FulfillmentTracking {
  order_id: string;
  status: string;
  fulfillment_stage: string | null;
  display_status: string;
  detail: string | null;
  estimated_ready_at: string | null;
  updated_at: string;
}

export interface DeliveryTracking {
  order_id: string;
  order_status: string;
  mission_status: string | null;
  display_status: string;
  detail: string | null;
  delivered_at: string | null;
  promised_delivery_window_start_at: string | null;
  promised_delivery_window_end_at: string | null;
  promised_delivery_timezone: string | null;
  delivery_timing_status: "on_time" | "late" | "unmeasurable" | string | null;
  late_by_minutes: number | null;
}

export interface LiveOrderTracking {
  fulfillment: FulfillmentTracking;
  delivery: DeliveryTracking | null;
}

export interface LoyaltySummary {
  balance_points: number;
  lifetime_earned_points: number;
  lifetime_redeemed_points: number;
  transactions?: unknown[];
}



export interface CustomerProfile {
  id: string;
  phone: string;
  display_name: string | null;
  preferred_language: "ar" | "en";
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface CustomerProfileUpdate {
  display_name: string | null;
  preferred_language: "ar" | "en";
}

export interface FavoriteChef {
  favorite_id: string;
  chef_id: string;
  display_name: string;
  specialty: string;
  area: string;
  rating: number;
  is_verified: boolean;
  is_open_today: boolean;
  created_at: string;
}

export interface FavoriteDish {
  favorite_id: string;
  dish_id: string;
  chef_id: string;
  name: string;
  category: string;
  base_price_minor: number;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface FavoritesSummary {
  chefs_count: number;
  dishes_count: number;
}

export interface NotificationItem {
  id: string;
  kind: string;
  title: string;
  body: string;
  action_url: string | null;
  data_json: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export interface NotificationSummary {
  unread_count: number;
  latest: NotificationItem[];
}

export interface NotificationPreferences {
  user_id: string;
  push_enabled: boolean;
  sms_enabled: boolean;
  order_updates: boolean;
  support_updates: boolean;
  marketing_enabled: boolean;
}

export interface LoyaltyTransaction {
  id: string;
  transaction_type: string;
  points: number;
  source_order_id: string | null;
  description: string;
  created_at: string;
}

export interface LoyaltyAccount {
  customer_id: string;
  balance_points: number;
  lifetime_earned_points: number;
  lifetime_redeemed_points: number;
  transactions: LoyaltyTransaction[];
}

export interface SupportAttachment {
  media_asset_id: string;
  mime_type: string;
  filename: string | null;
}

export interface SupportMessage {
  id: string;
  sender_role: string;
  body: string;
  is_internal: boolean;
  created_at: string;
  attachments: SupportAttachment[];
}

export interface SupportTicket {
  id: string;
  customer_id: string;
  order_id: string | null;
  assigned_admin_id: string | null;
  category: string;
  subject: string;
  description: string;
  priority: string;
  status: string;
  resolution_code: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
  messages: SupportMessage[];
}

export interface SupportTicketCreate {
  order_id?: string | null;
  category:
    | "food_quality"
    | "missing_item"
    | "wrong_item"
    | "late_delivery"
    | "delivery_issue"
    | "refund"
    | "payment"
    | "app_issue"
    | "other";
  subject: string;
  description: string;
  priority: "normal" | "high" | "urgent";
  attachment_ids?: string[];
}

export interface SubscriptionPlan {
  id: string;
  code: string;
  name: string;
  description: string;
  price_minor: number;
  duration_days: number;
  order_discount_bps: number;
  max_order_discount_minor: number | null;
  loyalty_multiplier_bps: number;
  is_active: boolean;
}

export interface CustomerSubscription {
  id: string;
  customer_id: string;
  plan_id: string;
  plan_code: string;
  plan_name: string;
  status: string;
  source: string;
  starts_at: string;
  ends_at: string;
  cancelled_at: string | null;
}



export interface Review {
  id: string;
  order_id: string;
  customer_id: string;
  chef_id: string;
  driver_id: string | null;
  food_quality: number;
  packaging: number;
  order_accuracy: number;
  value_for_money: number;
  chef_overall: number;
  delivery_overall: number | null;
  comment: string | null;
  is_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReviewInput {
  food_quality: number;
  packaging: number;
  order_accuracy: number;
  value_for_money: number;
  chef_overall: number;
  delivery_overall: number | null;
  comment: string | null;
}

export interface ReviewEligibility {
  order_id: string;
  order_status: string;
  can_review: boolean;
  reason: "review_exists" | "order_not_delivered" | "ready_for_review" | string;
  review: Review | null;
}

export interface PublicReview {
  id: string;
  food_quality: number;
  packaging: number;
  order_accuracy: number;
  value_for_money: number;
  chef_overall: number;
  comment: string | null;
  created_at: string;
}

export interface ChefRatingSummary {
  chef_id: string;
  rating: number;
  review_count: number;
  food_quality: number;
  packaging: number;
  order_accuracy: number;
  value_for_money: number;
}

export interface AvailabilityDay {
  service_date: string;
  weekday: number;
  is_available: boolean;
  source: string;
  delivery_window_start: string | null;
  delivery_window_end: string | null;
  capacity_total: number;
  capacity_used: number;
  capacity_remaining: number;
}

export interface SpecialOrderEvent {
  from_status: string | null;
  to_status: string;
  reason: string | null;
  data_json: Record<string, unknown>;
  created_at: string;
}

export interface SpecialOrder {
  id: string;
  customer_id: string;
  chef_id: string;
  dish_id: string;
  dish_name: string;
  order_id: string | null;
  request_type: "special" | "preorder";
  status: string;
  quantity: number;
  requested_service_date: string;
  requested_window_start: string | null;
  requested_window_end: string | null;
  requested_unit_price_minor: number;
  proposed_service_date: string | null;
  proposed_window_start: string | null;
  proposed_window_end: string | null;
  proposed_unit_price_minor: number | null;
  final_service_date: string | null;
  final_window_start: string | null;
  final_window_end: string | null;
  final_unit_price_minor: number | null;
  final_total_minor: number | null;
  customer_note: string | null;
  chef_note: string | null;
  rejection_reason: string | null;
  offer_expires_at: string | null;
  chef_responded_at: string | null;
  customer_accepted_at: string | null;
  scheduled_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
  events: SpecialOrderEvent[];
}

export interface SpecialOrderCreate {
  dish_id: string;
  request_type: "special" | "preorder";
  quantity: number;
  requested_service_date: string;
  requested_window_start: string | null;
  requested_window_end: string | null;
  customer_note: string | null;
}

export interface SpecialOrderCheckout {
  special_order: SpecialOrder;
  order: OrderResponse;
  payment: PaymentIntent;
}


export interface PushDevice {
  id: string;
  platform: "ios" | "android" | "web";
  device_name: string | null;
  app_version: string | null;
  is_active: boolean;
  last_seen_at: string;
  created_at: string;
}

export interface MediaAsset {
  id: string;
  owner_user_id: string;
  purpose: string;
  visibility: string;
  storage_provider: string;
  original_filename: string | null;
  mime_type: string;
  expected_size_bytes: number;
  actual_size_bytes: number | null;
  checksum_sha256: string | null;
  status: string;
  upload_expires_at: string;
  ready_at: string | null;
  created_at: string;
}

export interface MediaUpload {
  asset: MediaAsset;
  upload_url: string;
  upload_headers: Record<string,string>;
  expires_at: string;
}

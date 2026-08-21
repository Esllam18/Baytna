export interface VerifyOtpResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: { id: string; phone: string; role: string };
}

export interface ChefProfile {
  id: string;
  display_name: string;
  specialty: string;
  area: string;
  status: string;
  rating: number;
  is_verified: boolean;
  is_open_today: boolean;
}

export interface ChefDashboard {
  chef: ChefProfile;
  service_date: string;
  kitchen_status: string;
  signature_dishes: number;
  today_items: number;
  sold_out_items: number;
  available_quantity: number;
  orders_new: number;
  orders_accepted: number;
  orders_preparing: number;
  orders_packaging: number;
  orders_ready: number;
  special_review: number;
  special_counter_offer: number;
  special_awaiting_payment: number;
  special_scheduled: number;
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

export interface TodayMenuItem {
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
  items: TodayMenuItem[];
}

export interface ChefOrderListItem {
  order_id: string;
  customer_id: string;
  service_date: string;
  order_status: string;
  fulfillment_stage: "new" | "accepted" | "preparing" | "packaging" | "ready" | "rejected";
  total_minor: number;
  currency: string;
  acceptance_deadline_at: string | null;
  estimated_ready_at: string | null;
  created_at: string;
}

export interface ChefOrderDetail extends ChefOrderListItem {
  chef_id: string;
  subtotal_minor: number;
  accepted_at: string | null;
  preparation_started_at: string | null;
  packaging_started_at: string | null;
  ready_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  chef_note: string | null;
  items: {
    dish_id: string;
    dish_name: string;
    quantity: number;
    unit_price_minor: number;
    line_total_minor: number;
  }[];
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
  created_at: string;
  events: {
    from_status: string | null;
    to_status: string;
    reason: string | null;
    created_at: string;
  }[];
}

export interface WeeklyScheduleDay {
  weekday: number;
  is_available: boolean;
  delivery_window_start: string | null;
  delivery_window_end: string | null;
  max_special_orders: number;
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

export interface NotificationPreferences {
  user_id: string;
  push_enabled: boolean;
  sms_enabled: boolean;
  order_updates: boolean;
  support_updates: boolean;
  marketing_enabled: boolean;
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

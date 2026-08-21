export interface VerifyOtpResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: { id: string; phone: string; role: string };
}

export interface DriverProfile {
  id: string;
  phone: string;
  status: "offline" | "available" | "on_mission" | string;
  rating: number;
}

export interface DeliveryAddress {
  label: string | null;
  area: string;
  street: string | null;
  building: string | null;
  floor: string | null;
  apartment: string | null;
  latitude: string | null;
  longitude: string | null;
}

export interface DeliveryMission {
  id: string;
  order_id: string;
  chef_id: string;
  driver_id: string | null;
  status:
    | "unassigned"
    | "to_pickup"
    | "at_pickup"
    | "picked_up"
    | "to_customer"
    | "delivered"
    | "delivery_issue"
    | "cancelled"
    | string;
  order_status: string;
  service_date: string;
  total_minor: number;
  currency: string;
  pickup_name: string;
  pickup_area: string;
  dropoff: DeliveryAddress | null;
  navigation_ready: boolean;
  accepted_at: string | null;
  arrived_pickup_at: string | null;
  picked_up_at: string | null;
  route_started_at: string | null;
  delivered_at: string | null;
  promised_delivery_window_start_at: string | null;
  promised_delivery_window_end_at: string | null;
  promised_delivery_timezone: string | null;
  delivery_timing_status: "on_time" | "late" | "unmeasurable" | string | null;
  late_by_minutes: number | null;
  delivery_proof_type: string | null;
  delivery_proof_media_asset_id: string | null;
  issue_code: string | null;
  issue_note: string | null;
  created_at: string;
}

export interface DriverDashboard {
  driver: DriverProfile;
  active_mission: DeliveryMission | null;
  available_missions_count: number;
  completed_missions_count: number;
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
  status: string;
}

export interface MediaUpload {
  asset: MediaAsset;
  upload_url: string;
  upload_headers: Record<string,string>;
  expires_at: string;
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

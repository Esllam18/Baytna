import { ApiClient, ApiClientError } from "./http";
import {
  ChefDashboard,
  ChefOrderDetail,
  ChefOrderListItem,
  ChefProfile,
  Dish,
  PushDevice,
  NotificationPreferences,
  MediaUpload,
  MediaAsset,
  SpecialOrder,
  TodayMenu,
  VerifyOtpResponse,
  WeeklyScheduleDay,
} from "./types";
import { TokenStore } from "../auth/tokenStore";

export class ChefApi {
  constructor(
    private readonly http: ApiClient,
    private readonly tokens: TokenStore,
  ) {}

  sendOtp(phone: string) {
    return this.http.request<{sent: boolean; development_otp?: string}>(
      "/api/v1/auth/send-otp",
      { method: "POST", auth: false, body: JSON.stringify({ phone }) },
    );
  }

  async verifyOtp(phone: string, code: string) {
    const response = await this.http.request<VerifyOtpResponse>(
      "/api/v1/auth/verify-otp",
      { method: "POST", auth: false, body: JSON.stringify({ phone, code }) },
    );
    if (response.user.role !== "chef") {
      await this.tokens.clear();
      throw new ApiClientError(
        403,
        "chef_role_required",
        "هذا الحساب غير مسجل كشيف في بيتنا.",
      );
    }
    await this.tokens.set({
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
    });
    return response;
  }

  async logout() {
    const pair = await this.tokens.get();
    try {
      if (pair?.refreshToken) {
        await this.http.request("/api/v1/auth/logout", {
          method: "POST",
          auth: false,
          body: JSON.stringify({ refresh_token: pair.refreshToken }),
        });
      }
    } finally {
      await this.tokens.clear();
    }
  }

  profile() {
    return this.http.request<ChefProfile>("/api/v1/chef/profile");
  }

  dashboard(serviceDate: string) {
    return this.http.request<ChefDashboard>(
      `/api/v1/chef/app-dashboard?date=${serviceDate}`,
    );
  }

  signatureMenu(includeInactive = true) {
    return this.http.request<Dish[]>(
      `/api/v1/chef/signature-menu?include_inactive=${String(includeInactive)}`,
    );
  }

  createDish(payload: {
    name: string;
    description: string;
    category: string;
    base_price_minor: number;
    prep_notice_hours: number;
    is_special_order_available: boolean;
    display_order: number;
  }) {
    return this.http.request<Dish>("/api/v1/chef/signature-menu", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  updateDish(dishId: string, payload: Partial<{
    name: string;
    description: string;
    category: string;
    base_price_minor: number;
    prep_notice_hours: number;
    is_special_order_available: boolean;
    is_active: boolean;
    display_order: number;
  }>) {
    return this.http.request<Dish>(
      `/api/v1/chef/signature-menu/${dishId}`,
      { method: "PATCH", body: JSON.stringify(payload) },
    );
  }

  todayMenu(serviceDate: string) {
    return this.http.request<TodayMenu>(
      `/api/v1/chef/today-menu?date=${serviceDate}`,
    );
  }

  openKitchen(payload: {
    service_date: string;
    cutoff_at: string | null;
    delivery_window_start: string | null;
    delivery_window_end: string | null;
  }) {
    return this.http.request("/api/v1/chef/workdays/open", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  closeKitchen(serviceDate: string) {
    return this.http.request(
      `/api/v1/chef/workdays/${serviceDate}/close`,
      { method: "POST" },
    );
  }

  replaceTodayMenu(
    serviceDate: string,
    items: {
      dish_id: string;
      price_minor: number | null;
      quantity_total: number;
      max_per_order: number;
      is_visible: boolean;
    }[],
  ) {
    return this.http.request<TodayMenu>("/api/v1/chef/today-menu", {
      method: "PUT",
      body: JSON.stringify({ service_date: serviceDate, items }),
    });
  }

  updateTodayQuantity(itemId: string, quantityAvailable: number) {
    return this.http.request(
      `/api/v1/chef/today-menu/${itemId}/quantity`,
      {
        method: "PATCH",
        body: JSON.stringify({ quantity_available: quantityAvailable }),
      },
    );
  }

  orders(stage?: string) {
    const query = stage ? `?stage=${stage}` : "";
    return this.http.request<ChefOrderListItem[]>(
      `/api/v1/chef/orders${query}`,
    );
  }

  order(orderId: string) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}`,
    );
  }

  acceptOrder(orderId: string, chefNote?: string | null) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}/accept`,
      {
        method: "POST",
        body: JSON.stringify({
          estimated_ready_at: null,
          chef_note: chefNote ?? null,
        }),
      },
    );
  }

  rejectOrder(orderId: string, reason: string) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) },
    );
  }

  startPreparing(orderId: string, chefNote?: string | null) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}/start-preparing`,
      { method: "POST", body: JSON.stringify({ chef_note: chefNote ?? null }) },
    );
  }

  startPackaging(orderId: string, chefNote?: string | null) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}/start-packaging`,
      { method: "POST", body: JSON.stringify({ chef_note: chefNote ?? null }) },
    );
  }

  readyForPickup(orderId: string, chefNote?: string | null) {
    return this.http.request<ChefOrderDetail>(
      `/api/v1/chef/orders/${orderId}/ready-for-pickup`,
      { method: "POST", body: JSON.stringify({ chef_note: chefNote ?? null }) },
    );
  }

  specialOrders(status?: string) {
    const query = status ? `?status=${status}` : "";
    return this.http.request<SpecialOrder[]>(
      `/api/v1/chef/special-orders${query}`,
    );
  }

  specialOrder(id: string) {
    return this.http.request<SpecialOrder>(
      `/api/v1/chef/special-orders/${id}`,
    );
  }

  acceptSpecialOrder(id: string, payload: {
    unit_price_minor: number | null;
    delivery_window_start: string | null;
    delivery_window_end: string | null;
    chef_note: string | null;
  }) {
    return this.http.request<SpecialOrder>(
      `/api/v1/chef/special-orders/${id}/accept`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }

  counterSpecialOrder(id: string, payload: {
    proposed_service_date: string;
    proposed_unit_price_minor: number;
    proposed_window_start: string | null;
    proposed_window_end: string | null;
    chef_note: string | null;
  }) {
    return this.http.request<SpecialOrder>(
      `/api/v1/chef/special-orders/${id}/counter-offer`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }

  rejectSpecialOrder(id: string, reason: string) {
    return this.http.request<SpecialOrder>(
      `/api/v1/chef/special-orders/${id}/reject`,
      { method: "POST", body: JSON.stringify({ reason }) },
    );
  }


  registerPushDevice(payload: {
    platform: "ios" | "android" | "web";
    token: string;
    device_name: string | null;
    app_version: string | null;
  }) {
    return this.http.request<PushDevice>("/api/v1/notifications/devices", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  notificationPreferences() {
    return this.http.request<NotificationPreferences>(
      "/api/v1/notifications/preferences",
    );
  }

  updateNotificationPreferences(payload: Omit<NotificationPreferences, "user_id">) {
    return this.http.request<NotificationPreferences>(
      "/api/v1/notifications/preferences",
      { method: "PUT", body: JSON.stringify(payload) },
    );
  }

  createDishMediaUpload(payload: {
    filename: string | null;
    mime_type: "image/jpeg" | "image/png" | "image/webp";
    size_bytes: number;
  }) {
    return this.http.request<MediaUpload>("/api/v1/media/uploads", {
      method: "POST",
      body: JSON.stringify({
        purpose: "dish_image",
        visibility: "public",
        ...payload,
      }),
    });
  }

  completeMedia(assetId: string) {
    return this.http.request<{ asset: MediaAsset }>(
      `/api/v1/media/${assetId}/complete`,
      { method: "POST" },
    );
  }

  setDishMedia(dishId: string, mediaAssetId: string | null) {
    return this.http.request<Dish>(
      `/api/v1/chef/signature-menu/${dishId}/media`,
      {
        method: "PUT",
        body: JSON.stringify({ media_asset_id: mediaAssetId }),
      },
    );
  }

  weeklySchedule() {
    return this.http.request<WeeklyScheduleDay[]>(
      "/api/v1/chef/schedule/weekly",
    );
  }

  saveWeeklySchedule(days: WeeklyScheduleDay[]) {
    return this.http.request<WeeklyScheduleDay[]>(
      "/api/v1/chef/schedule/weekly",
      { method: "PUT", body: JSON.stringify({ days }) },
    );
  }
}

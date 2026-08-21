import { ApiClient, ApiClientError } from "./http";
import {
  DeliveryMission,
  DriverDashboard,
  DriverProfile,
  MediaAsset,
  MediaUpload,
  PushDevice,
  NotificationPreferences,
  VerifyOtpResponse,
} from "./types";
import { TokenStore } from "../auth/tokenStore";

export class DriverApi {
  constructor(
    private readonly http: ApiClient,
    private readonly tokens: TokenStore,
  ) {}

  sendOtp(phone: string) {
    return this.http.request<{sent:boolean; development_otp?:string}>(
      "/api/v1/auth/send-otp",
      {method:"POST", auth:false, body:JSON.stringify({phone})},
    );
  }

  async verifyOtp(phone: string, code: string) {
    const response = await this.http.request<VerifyOtpResponse>(
      "/api/v1/auth/verify-otp",
      {method:"POST", auth:false, body:JSON.stringify({phone,code})},
    );
    if (response.user.role !== "driver") {
      await this.tokens.clear();
      throw new ApiClientError(
        403,
        "driver_role_required",
        "هذا الحساب غير مسجل كمندوب في بيتنا.",
      );
    }
    await this.tokens.set({
      accessToken:response.access_token,
      refreshToken:response.refresh_token,
    });
    return response;
  }

  async logout() {
    const pair=await this.tokens.get();
    try {
      if (pair?.refreshToken) {
        await this.http.request("/api/v1/auth/logout", {
          method:"POST",
          auth:false,
          body:JSON.stringify({refresh_token:pair.refreshToken}),
        });
      }
    } finally {
      await this.tokens.clear();
    }
  }

  profile() {
    return this.http.request<DriverProfile>("/api/v1/driver/profile");
  }

  dashboard() {
    return this.http.request<DriverDashboard>("/api/v1/driver/app-dashboard");
  }

  status() {
    return this.http.request<{
      driver_id:string;
      status:string;
      rating:number;
      active_mission_id:string|null;
    }>("/api/v1/driver/status");
  }

  setAvailability(available:boolean) {
    return this.http.request<{
      driver_id:string;
      status:string;
      rating:number;
      active_mission_id:string|null;
    }>("/api/v1/driver/availability", {
      method:"PUT",
      body:JSON.stringify({available}),
    });
  }

  availableMissions() {
    return this.http.request<DeliveryMission[]>(
      "/api/v1/driver/missions/available",
    );
  }

  availableMission(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/available/${id}`,
    );
  }

  currentMission() {
    return this.http.request<DeliveryMission>(
      "/api/v1/driver/missions/current",
    );
  }

  mission(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}`,
    );
  }

  history() {
    return this.http.request<DeliveryMission[]>(
      "/api/v1/driver/missions/history",
    );
  }

  acceptMission(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/accept`,
      {method:"POST"},
    );
  }

  arrivePickup(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/arrive-pickup`,
      {method:"POST"},
    );
  }

  confirmPickup(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/confirm-pickup`,
      {method:"POST"},
    );
  }

  startDelivery(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/start-delivery`,
      {method:"POST"},
    );
  }

  deliver(id:string, proof:{
    proof_type:"otp"|"photo"|"signature"|"manual";
    proof_reference?:string|null;
    media_asset_id?:string|null;
  }) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/deliver`,
      {method:"POST", body:JSON.stringify(proof)},
    );
  }

  reportIssue(id:string, payload:{issue_code:string; note:string}) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/issue`,
      {method:"POST", body:JSON.stringify(payload)},
    );
  }

  resumeMission(id:string) {
    return this.http.request<DeliveryMission>(
      `/api/v1/driver/missions/${id}/resume`,
      {method:"POST"},
    );
  }


  registerPushDevice(payload:{
    platform:"ios"|"android"|"web";
    token:string;
    device_name:string|null;
    app_version:string|null;
  }) {
    return this.http.request<PushDevice>("/api/v1/notifications/devices", {
      method:"POST",
      body:JSON.stringify(payload),
    });
  }

  notificationPreferences() {
    return this.http.request<NotificationPreferences>(
      "/api/v1/notifications/preferences",
    );
  }

  updateNotificationPreferences(payload:Omit<NotificationPreferences,"user_id">) {
    return this.http.request<NotificationPreferences>(
      "/api/v1/notifications/preferences",
      {method:"PUT",body:JSON.stringify(payload)},
    );
  }

  createMediaUpload(payload:{
    purpose:"delivery_proof";
    visibility:"private";
    filename:string|null;
    mime_type:"image/jpeg"|"image/png"|"image/webp";
    size_bytes:number;
  }) {
    return this.http.request<MediaUpload>("/api/v1/media/uploads", {
      method:"POST",
      body:JSON.stringify(payload),
    });
  }

  completeMedia(assetId:string) {
    return this.http.request<{asset:MediaAsset}>(
      `/api/v1/media/${assetId}/complete`,
      {method:"POST"},
    );
  }
}

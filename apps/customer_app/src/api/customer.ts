import { ApiClient, ApiClientError } from "./http";
import {
  Address,
  AddressCreate,
  AvailabilityDay,
  CartResponse,
  ChefRatingSummary,
  ChefSummary,
  CustomerHomeResponse,
  CustomerProfile,
  CustomerProfileUpdate,
  CustomerSubscription,
  DeliveryTracking,
  Dish,
  FavoriteChef,
  FavoriteDish,
  FavoritesSummary,
  FulfillmentTracking,
  LiveOrderTracking,
  PushDevice,
  MediaUpload,
  MediaAsset,
  LoyaltyAccount,
  NotificationItem,
  NotificationPreferences,
  NotificationSummary,
  OrderListItem,
  OrderResponse,
  PaymentIntent,
  PricingQuote,
  PublicReview,
  Review,
  ReviewEligibility,
  ReviewInput,
  SendOtpResponse,
  SpecialOrder,
  SpecialOrderCheckout,
  SpecialOrderCreate,
  SubscriptionPlan,
  SupportTicket,
  SupportTicketCreate,
  TodayMenu,
  VerifyOtpResponse,
} from "./types";
import { TokenStore } from "../auth/tokenStore";

export class CustomerApi {
  constructor(private http: ApiClient, private tokenStore: TokenStore) {}

  sendOtp(phone: string) {
    return this.http.request<SendOtpResponse>("/api/v1/auth/send-otp", {
      method: "POST", auth: false, body: JSON.stringify({ phone }),
    });
  }

  async verifyOtp(phone: string, code: string) {
    const r = await this.http.request<VerifyOtpResponse>("/api/v1/auth/verify-otp", {
      method: "POST", auth: false, body: JSON.stringify({ phone, code }),
    });
    await this.tokenStore.set({ accessToken: r.access_token, refreshToken: r.refresh_token });
    return r;
  }

  async logout() {
    const t = await this.tokenStore.get();
    try {
      if (t?.refreshToken) {
        await this.http.request("/api/v1/auth/logout", {
          method: "POST", auth: false, body: JSON.stringify({ refresh_token: t.refreshToken }),
        });
      }
    } finally {
      await this.tokenStore.clear();
    }
  }

  home() { return this.http.request<CustomerHomeResponse>("/api/v1/customer/home"); }
  chefs(area?: string, openToday?: boolean) {
    const q = new URLSearchParams();
    if (area) q.set("area", area);
    if (openToday !== undefined) q.set("open_today", String(openToday));
    const query = q.toString();
    return this.http.request<ChefSummary[]>(`/api/v1/chefs${query ? `?${query}` : ""}`, { auth: false });
  }
  chef(id: string) { return this.http.request<ChefSummary>(`/api/v1/chefs/${id}`, { auth: false }); }
  signatureMenu(id: string) { return this.http.request<Dish[]>(`/api/v1/chefs/${id}/signature-menu`, { auth: false }); }
  todayMenu(id: string) { return this.http.request<TodayMenu>(`/api/v1/chefs/${id}/today-menu`, { auth: false }); }

  cart() { return this.http.request<CartResponse>("/api/v1/customer/cart"); }
  addCartItem(daily_menu_item_id: string, quantity: number) {
    return this.http.request<CartResponse>("/api/v1/customer/cart/items", {
      method: "POST", body: JSON.stringify({ daily_menu_item_id, quantity }),
    });
  }
  updateCartItem(cartItemId: string, quantity: number) {
    return this.http.request<CartResponse>(`/api/v1/customer/cart/items/${cartItemId}`, {
      method: "PATCH", body: JSON.stringify({ quantity }),
    });
  }
  removeCartItem(cartItemId: string) {
    return this.http.request<CartResponse>(`/api/v1/customer/cart/items/${cartItemId}`, { method: "DELETE" });
  }
  clearCart() { return this.http.request<CartResponse>("/api/v1/customer/cart", { method: "DELETE" }); }

  pricingQuote(cart_id: string, coupon_code?: string | null, loyalty_points_to_redeem = 0) {
    return this.http.request<PricingQuote>("/api/v1/customer/pricing/quote", {
      method: "POST",
      body: JSON.stringify({ cart_id, coupon_code: coupon_code || null, loyalty_points_to_redeem }),
    });
  }

  addresses() { return this.http.request<Address[]>("/api/v1/customer/addresses"); }
  createAddress(payload: AddressCreate) {
    return this.http.request<Address>("/api/v1/customer/addresses", { method: "POST", body: JSON.stringify(payload) });
  }

  createOrder(cart_id: string, delivery_address_id: string, coupon_code?: string | null, loyalty_points_to_redeem = 0) {
    return this.http.request<OrderResponse>("/api/v1/customer/orders", {
      method: "POST",
      body: JSON.stringify({
        cart_id,
        delivery_address_id,
        coupon_code: coupon_code || null,
        loyalty_points_to_redeem,
      }),
    });
  }
  order(id: string) { return this.http.request<OrderResponse>(`/api/v1/customer/orders/${id}`); }
  orders() { return this.http.request<OrderListItem[]>("/api/v1/customer/orders"); }
  cancelOrder(id: string) { return this.http.request<OrderResponse>(`/api/v1/customer/orders/${id}/cancel`, { method: "POST" }); }
  setOrderDeliveryAddress(orderId: string, address_id: string) {
    return this.http.request<Record<string, unknown>>(`/api/v1/customer/orders/${orderId}/delivery-address`, {
      method: "PUT", body: JSON.stringify({ address_id }),
    });
  }

  createPaymentIntent(orderId: string, idempotency_key: string) {
    return this.http.request<PaymentIntent>(`/api/v1/customer/orders/${orderId}/payment-intent`, {
      method: "POST", body: JSON.stringify({ idempotency_key }),
    });
  }
  payment(orderId: string) { return this.http.request<PaymentIntent>(`/api/v1/customer/orders/${orderId}/payment`); }

  tracking(orderId: string) { return this.http.request<FulfillmentTracking>(`/api/v1/customer/orders/${orderId}/tracking`); }
  deliveryTracking(orderId: string) { return this.http.request<DeliveryTracking>(`/api/v1/customer/orders/${orderId}/delivery-tracking`); }
  async liveTracking(orderId: string): Promise<LiveOrderTracking> {
    const fulfillment = await this.tracking(orderId);
    let delivery: DeliveryTracking | null = null;
    try {
      delivery = await this.deliveryTracking(orderId);
    } catch (error) {
      if (!(error instanceof ApiClientError) || error.status !== 404) throw error;
    }
    return { fulfillment, delivery };
  }

  profile() {
    return this.http.request<CustomerProfile>("/api/v1/customer/profile");
  }
  updateProfile(payload: CustomerProfileUpdate) {
    return this.http.request<CustomerProfile>("/api/v1/customer/profile", {
      method: "PATCH", body: JSON.stringify(payload),
    });
  }

  updateAddress(addressId: string, payload: AddressCreate) {
    return this.http.request<Address>(`/api/v1/customer/addresses/${addressId}`, {
      method: "PATCH", body: JSON.stringify(payload),
    });
  }
  setDefaultAddress(addressId: string) {
    return this.http.request<Address>(`/api/v1/customer/addresses/${addressId}/default`, {
      method: "POST",
    });
  }
  deleteAddress(addressId: string) {
    return this.http.request<void>(`/api/v1/customer/addresses/${addressId}`, {
      method: "DELETE",
    });
  }

  favorites() {
    return this.http.request<FavoritesSummary>("/api/v1/customer/favorites/summary");
  }
  favoriteChefs() {
    return this.http.request<FavoriteChef[]>("/api/v1/customer/favorites/chefs");
  }
  addFavoriteChef(chefId: string) {
    return this.http.request<FavoriteChef>(`/api/v1/customer/favorites/chefs/${chefId}`, {
      method: "PUT",
    });
  }
  removeFavoriteChef(chefId: string) {
    return this.http.request<void>(`/api/v1/customer/favorites/chefs/${chefId}`, {
      method: "DELETE",
    });
  }
  favoriteDishes() {
    return this.http.request<FavoriteDish[]>("/api/v1/customer/favorites/dishes");
  }
  addFavoriteDish(dishId: string) {
    return this.http.request<FavoriteDish>(`/api/v1/customer/favorites/dishes/${dishId}`, {
      method: "PUT",
    });
  }
  removeFavoriteDish(dishId: string) {
    return this.http.request<void>(`/api/v1/customer/favorites/dishes/${dishId}`, {
      method: "DELETE",
    });
  }

  notifications(unreadOnly = false) {
    return this.http.request<NotificationItem[]>(
      `/api/v1/customer/notifications?unread_only=${String(unreadOnly)}`,
    );
  }
  notificationSummary() {
    return this.http.request<NotificationSummary>("/api/v1/customer/notifications/summary");
  }
  markNotificationRead(notificationId: string) {
    return this.http.request<NotificationItem>(
      `/api/v1/customer/notifications/${notificationId}/read`,
      { method: "POST" },
    );
  }
  markAllNotificationsRead() {
    return this.http.request<{ updated: number }>("/api/v1/customer/notifications/read-all", {
      method: "POST",
    });
  }
  notificationPreferences() {
    return this.http.request<NotificationPreferences>(
      "/api/v1/customer/notifications/preferences",
    );
  }
  updateNotificationPreferences(payload: NotificationPreferences) {
    const {
      user_id: _userId,
      ...body
    } = payload;
    return this.http.request<NotificationPreferences>(
      "/api/v1/customer/notifications/preferences",
      { method: "PUT", body: JSON.stringify(body) },
    );
  }

  loyalty() {
    return this.http.request<LoyaltyAccount>("/api/v1/customer/loyalty");
  }

  supportTickets() {
    return this.http.request<SupportTicket[]>("/api/v1/customer/support/tickets");
  }
  supportTicket(ticketId: string) {
    return this.http.request<SupportTicket>(`/api/v1/customer/support/tickets/${ticketId}`);
  }
  createSupportTicket(payload: SupportTicketCreate) {
    return this.http.request<SupportTicket>("/api/v1/customer/support/tickets", {
      method: "POST", body: JSON.stringify({ ...payload, attachment_ids: payload.attachment_ids ?? [] }),
    });
  }
  addSupportMessage(ticketId: string, body: string, attachmentIds: string[] = []) {
    return this.http.request<SupportTicket>(
      `/api/v1/customer/support/tickets/${ticketId}/messages`,
      { method: "POST", body: JSON.stringify({ body, attachment_ids: attachmentIds }) },
    );
  }


  reviewEligibility(orderId: string) {
    return this.http.request<ReviewEligibility>(
      `/api/v1/customer/orders/${orderId}/review-eligibility`,
    );
  }
  reviewForOrder(orderId: string) {
    return this.http.request<Review>(
      `/api/v1/customer/orders/${orderId}/review`,
    );
  }
  createReview(orderId: string, payload: ReviewInput) {
    return this.http.request<Review>(
      `/api/v1/customer/orders/${orderId}/review`,
      { method: "POST", body: JSON.stringify(payload) },
    );
  }
  updateReview(reviewId: string, payload: Partial<ReviewInput>) {
    return this.http.request<Review>(
      `/api/v1/customer/reviews/${reviewId}`,
      { method: "PATCH", body: JSON.stringify(payload) },
    );
  }
  myReviews() {
    return this.http.request<Review[]>("/api/v1/customer/reviews");
  }
  chefReviews(chefId: string) {
    return this.http.request<PublicReview[]>(
      `/api/v1/chefs/${chefId}/reviews`,
      { auth: false },
    );
  }
  chefRatingSummary(chefId: string) {
    return this.http.request<ChefRatingSummary>(
      `/api/v1/chefs/${chefId}/rating-summary`,
      { auth: false },
    );
  }

  chefAvailability(chefId: string, days = 30) {
    return this.http.request<AvailabilityDay[]>(
      `/api/v1/chefs/${chefId}/availability?days=${days}`,
      { auth: false },
    );
  }
  specialOrders() {
    return this.http.request<SpecialOrder[]>("/api/v1/customer/special-orders");
  }
  specialOrder(specialOrderId: string) {
    return this.http.request<SpecialOrder>(
      `/api/v1/customer/special-orders/${specialOrderId}`,
    );
  }
  createSpecialOrder(payload: SpecialOrderCreate) {
    return this.http.request<SpecialOrder>("/api/v1/customer/special-orders", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
  acceptSpecialOrderCounter(specialOrderId: string) {
    return this.http.request<SpecialOrder>(
      `/api/v1/customer/special-orders/${specialOrderId}/accept-counter-offer`,
      { method: "POST" },
    );
  }
  cancelSpecialOrder(specialOrderId: string) {
    return this.http.request<SpecialOrder>(
      `/api/v1/customer/special-orders/${specialOrderId}/cancel`,
      { method: "POST" },
    );
  }
  checkoutSpecialOrder(specialOrderId: string, idempotencyKey: string) {
    return this.http.request<SpecialOrderCheckout>(
      `/api/v1/customer/special-orders/${specialOrderId}/checkout`,
      {
        method: "POST",
        body: JSON.stringify({ idempotency_key: idempotencyKey }),
      },
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

  createMediaUpload(payload: {
    purpose: "support_attachment" | "customer_attachment";
    visibility: "private";
    filename: string | null;
    mime_type: "image/jpeg" | "image/png" | "image/webp";
    size_bytes: number;
  }) {
    return this.http.request<MediaUpload>("/api/v1/media/uploads", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  completeMedia(assetId: string) {
    return this.http.request<{ asset: MediaAsset }>(
      `/api/v1/media/${assetId}/complete`,
      { method: "POST" },
    );
  }

  subscriptionPlans() {
    return this.http.request<SubscriptionPlan[]>("/api/v1/customer/subscriptions/plans");
  }
  currentSubscription() {
    return this.http.request<CustomerSubscription | null>(
      "/api/v1/customer/subscriptions/current",
    );
  }
  cancelSubscription() {
    return this.http.request<CustomerSubscription>(
      "/api/v1/customer/subscriptions/current/cancel",
      { method: "POST" },
    );
  }
}

export const chefKeys = {
  profile: ["chef", "profile"] as const,
  dashboard: (date: string) => ["chef", "dashboard", date] as const,
  signatureMenu: ["chef", "signature-menu"] as const,
  todayMenu: (date: string) => ["chef", "today-menu", date] as const,
  orders: (stage?: string) => ["chef", "orders", stage ?? "all"] as const,
  order: (id: string) => ["chef", "order", id] as const,
  specialOrders: (status?: string) => ["chef", "special-orders", status ?? "all"] as const,
  specialOrder: (id: string) => ["chef", "special-order", id] as const,
  schedule: ["chef", "schedule"] as const,
};

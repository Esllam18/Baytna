import * as SecureStore from "expo-secure-store";
const KEY = "baytna_pending_payment_order_id";
export async function setPendingPaymentOrder(orderId: string): Promise<void> { await SecureStore.setItemAsync(KEY, orderId); }
export async function getPendingPaymentOrder(): Promise<string | null> { return SecureStore.getItemAsync(KEY); }
export async function clearPendingPaymentOrder(): Promise<void> { await SecureStore.deleteItemAsync(KEY); }

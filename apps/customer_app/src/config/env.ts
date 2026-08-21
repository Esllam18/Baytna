export type AppEnvironment = "development" | "staging" | "production";
export function loadConfig(env = process.env) {
  const environment = (env.EXPO_PUBLIC_BAYTNA_ENV ?? "development") as AppEnvironment;
  const apiBaseUrl = (env.EXPO_PUBLIC_BAYTNA_API_BASE_URL ?? (environment === "development" ? "http://127.0.0.1:8000" : "")).replace(/\/+$/, "");
  if (!apiBaseUrl) throw new Error("EXPO_PUBLIC_BAYTNA_API_BASE_URL is required");
  if (environment !== "development" && !apiBaseUrl.startsWith("https://")) throw new Error("Non-development API URL must use HTTPS");
  return { environment, apiBaseUrl, paymentReturnUrl: env.EXPO_PUBLIC_BAYTNA_PAYMENT_RETURN_URL ?? "baytna://payment/result" };
}
export const config = loadConfig();

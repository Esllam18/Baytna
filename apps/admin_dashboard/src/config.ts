export const config = (() => {
  const environment = import.meta.env.VITE_BAYTNA_ENV ?? "development";
  const apiBaseUrl = (
    import.meta.env.VITE_BAYTNA_API_BASE_URL ??
    (environment === "development" ? "http://127.0.0.1:8000" : "")
  ).replace(/\/+$/, "");

  if (!apiBaseUrl) throw new Error("VITE_BAYTNA_API_BASE_URL is required.");
  if (environment !== "development" && !apiBaseUrl.startsWith("https://")) {
    throw new Error("Admin API URL must use HTTPS outside development.");
  }
  return { environment, apiBaseUrl };
})();

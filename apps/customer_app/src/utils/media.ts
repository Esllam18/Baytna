import { config } from "../config/env";
export function mediaUri(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  return `${config.apiBaseUrl}${url.startsWith("/") ? url : `/${url}`}`;
}

import { useEffect, useRef } from "react";
import { Platform } from "react-native";
import * as Device from "expo-device";
import { router } from "expo-router";
import { chefApi } from "../api";
import { useAuth } from "../auth/AuthProvider";

const APP_VERSION = process.env.EXPO_PUBLIC_BAYTNA_RELEASE ?? "0.50.0";
const NATIVE_PUSH_ENABLED =
  process.env.EXPO_PUBLIC_BAYTNA_ENABLE_NATIVE_PUSH === "true";

export function PushBootstrap() {
  const auth = useAuth();
  const attempted = useRef(false);

  useEffect(() => {
    if (!NATIVE_PUSH_ENABLED) return;

    let active = true;
    let remove: (() => void) | undefined;

    void import("expo-notifications").then((Notifications) => {
      if (!active) return;
      const sub = Notifications.addNotificationResponseReceivedListener((response) => {
        const route = response.notification.request.content.data?.route;
        if (typeof route === "string" && route.startsWith("/")) {
          router.push(route as never);
        }
      });
      remove = () => sub.remove();
    }).catch(() => undefined);

    return () => {
      active = false;
      remove?.();
    };
  }, []);

  useEffect(() => {
    if (!NATIVE_PUSH_ENABLED || !auth.authenticated) {
      attempted.current = false;
      return;
    }
    if (attempted.current) return;
    attempted.current = true;
    void registerAndroidFcmDevice().catch(() => undefined);
  }, [auth.authenticated]);

  return null;
}

async function registerAndroidFcmDevice() {
  if (!NATIVE_PUSH_ENABLED) return;
  if (!Device.isDevice || Platform.OS !== "android") return;

  const Notifications = await import("expo-notifications");

  await Notifications.setNotificationChannelAsync("default", {
    name: "Baytna Chef",
    importance: Notifications.AndroidImportance.HIGH,
  });

  let status = (await Notifications.getPermissionsAsync()).status;
  if (status !== "granted") {
    status = (await Notifications.requestPermissionsAsync()).status;
  }
  if (status !== "granted") return;

  const native = await Notifications.getDevicePushTokenAsync();
  const token = String(native.data ?? "").trim();
  if (token.length < 12) return;

  await chefApi.registerPushDevice({
    platform: "android",
    token,
    device_name: Device.modelName ?? "Android Chef",
    app_version: APP_VERSION,
  });
}

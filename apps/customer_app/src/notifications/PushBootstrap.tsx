import { useEffect, useRef } from "react";
import { Platform } from "react-native";
import * as Device from "expo-device";
import * as Notifications from "expo-notifications";
import { router } from "expo-router";
import { customerApi } from "../api";
import { useAuth } from "../auth/AuthProvider";

const APP_VERSION = "0.41.0";

export function PushBootstrap() {
  const auth = useAuth();
  const attempted = useRef(false);

  useEffect(() => {
    const sub = Notifications.addNotificationResponseReceivedListener((response) => {
      const route = response.notification.request.content.data?.route;
      if (typeof route === "string" && route.startsWith("/")) {
        router.push(route as never);
      }
    });
    return () => sub.remove();
  }, []);

  useEffect(() => {
    if (auth.status !== "authenticated") {
      attempted.current = false;
      return;
    }
    if (attempted.current) return;
    attempted.current = true;
    void registerAndroidFcmDevice().catch(() => undefined);
  }, [auth.status]);

  return null;
}

async function registerAndroidFcmDevice() {
  if (process.env.EXPO_PUBLIC_BAYTNA_ENABLE_NATIVE_PUSH === "false") return;
  if (!Device.isDevice || Platform.OS !== "android") return;

  await Notifications.setNotificationChannelAsync("default", {
    name: "Baytna",
    importance: Notifications.AndroidImportance.HIGH,
  });

  const current = await Notifications.getPermissionsAsync();
  let status = current.status;
  if (status !== "granted") {
    status = (await Notifications.requestPermissionsAsync()).status;
  }
  if (status !== "granted") return;

  const native = await Notifications.getDevicePushTokenAsync();
  const token = String(native.data ?? "").trim();
  if (token.length < 12) return;

  await customerApi.registerPushDevice({
    platform: "android",
    token,
    device_name: Device.modelName ?? "Android",
    app_version: APP_VERSION,
  });
}

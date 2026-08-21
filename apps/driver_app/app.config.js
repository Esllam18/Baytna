module.exports = ({ config }) => {
  const googleServicesFile = process.env.GOOGLE_SERVICES_JSON;

  return {
    ...config,
    plugins: [
      ...(config.plugins || []),
      "@sentry/react-native",
    ],
    android: {
      ...(config.android || {}),
      ...(googleServicesFile ? { googleServicesFile } : {}),
    },
    extra: {
      ...(config.extra || {}),
      baytnaRelease:
        process.env.EXPO_PUBLIC_BAYTNA_RELEASE || config.version || "0.50.0",
      baytnaEnvironment:
        process.env.EXPO_PUBLIC_BAYTNA_ENV || "development",
    },
  };
};

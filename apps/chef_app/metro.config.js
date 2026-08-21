const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);

// Local Expo Go uses standard Metro. Enable Sentry serializer only in a
// configured build pipeline where Debug IDs and Sentry build settings exist.
if (process.env.BAYTNA_ENABLE_SENTRY_METRO === "true") {
  const { withSentryConfig } = require("@sentry/react-native/metro");
  module.exports = withSentryConfig(config);
} else {
  module.exports = config;
}

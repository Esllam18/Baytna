import React from "react";
import { Sentry, sentryEnabled } from "../observability/sentry";
import { PageTitle } from "../components/Ui";

const enabled =
  import.meta.env.VITE_BAYTNA_ENABLE_DIAGNOSTICS === "true";

export function DiagnosticsPage() {
  if (!enabled) {
    return (
      <PageTitle
        title="Diagnostics disabled"
        subtitle="هذه الصفحة مغلقة في التشغيل العادي."
      />
    );
  }

  return (
    <>
      <PageTitle
        title="Sprint 43 Diagnostics"
        subtitle={`Sentry: ${sentryEnabled ? "configured" : "not configured"} • release 0.50.0`}
      />
      <section className="panel">
        <h2>Controlled crash verification</h2>
        <p>
          استخدم الأزرار دي فقط في diagnostic build قبل الإطلاق.
        </p>
        <div className="form-row">
          <button
            className="primary"
            onClick={() =>
              Sentry.captureMessage(
                "Baytna Sprint 43 admin diagnostic event",
                "info",
              )
            }
          >
            Send non-fatal event
          </button>
          <button
            className="danger-button"
            onClick={() => {
              throw new Error(
                "Baytna Sprint 43 admin controlled crash probe",
              );
            }}
          >
            Trigger controlled crash
          </button>
        </div>
      </section>
    </>
  );
}

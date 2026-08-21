# Sprint 33 — Frontend Architecture

```text
Expo / React Native
        ↓
Expo Router
        ↓
TanStack Query
        ↓
CustomerApi
        ↓
ApiClient
        ↓
Baytna FastAPI
```

Access/Refresh tokens محفوظة في SecureStore. عند 401 يتم refresh مرة واحدة ثم retry للطلب الأصلي. إذا فشل refresh يتم حذف الجلسة محليًا.

Server state يبقى في Query Cache. الدفع يفتح hosted checkout، وبعد redirect يعاد جلب payment + order من الـbackend. لا نعتمد redirect parameters كدليل نجاح مالي.

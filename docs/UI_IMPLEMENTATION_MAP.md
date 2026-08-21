# Sprint 35 — UI Implementation Map

| Product Bible Screen | Implementation | Backend |
|---|---|---|
| C01/C02 Auth entry | `app/auth/phone.tsx` | send OTP |
| C03 OTP | `app/auth/otp.tsx` | verify OTP |
| C07 Home | `app/home.tsx` | customer/home |
| C08 Chefs | `app/chefs/index.tsx` | public chefs |
| C10 Chef Profile | `app/chefs/[chefId].tsx` | chef + menus |
| C11 Dish Details | `app/chefs/[chefId]/dish/[dishId].tsx` | today/signature menu + cart add |
| C13 Cart | `app/cart.tsx` | cart get/update/remove/clear |
| C14 Checkout | `app/checkout.tsx` | addresses + pricing quote + order + payment intent |
| Payment Return | `app/payment/result.tsx` | payment + order re-fetch |
| C15 Tracking | `app/orders/[orderId]/tracking.tsx` | fulfillment + delivery tracking |
| C16 Orders/History foundation | `app/orders/index.tsx`, `app/orders/[orderId].tsx` | order list/detail/cancel |

C09 Search remains local frontend filtering because a dedicated search backend is still not invented.

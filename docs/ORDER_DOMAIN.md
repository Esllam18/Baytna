# Order Domain — Sprint 18

## Cart
السلة هي اختيار مؤقت للعميل.

### قواعد السلة
1. عميل واحد.
2. شيف واحد فقط.
3. يوم خدمة واحد فقط.
4. عناصر من Today’s Kitchen فقط.
5. لا يوجد inventory hold داخل السلة.
6. السعر يعاد قراءته من Today’s Kitchen.

## Checkout / Pending Order
عند `POST /customer/orders`:

1. إعادة التحقق من كل سطر.
2. التحقق من أن المطبخ مفتوح.
3. التحقق من cutoff.
4. التحقق من الكمية.
5. إنشاء order snapshot.
6. حجز المخزون Atomic.
7. تحويل السلة إلى `converted`.
8. إنشاء order status event.
9. الطلب يدخل `pending_payment`.

## Inventory Reservation
الحجز له TTL افتراضي:
**10 دقائق**

يمكن تغييره:
`BAYTNA_INVENTORY_HOLD_TTL_MINUTES`

### عند انتهاء الحجز
- يعاد المخزون.
- reservation → `expired`.
- order → `expired`.
- يسجل status event.

### عند الإلغاء قبل الدفع
- يعاد المخزون.
- reservation → `released`.
- order → `cancelled`.

## Concurrency
خصم المخزون يستخدم:
`UPDATE ... WHERE quantity_available >= requested`

وبذلك إذا حاول عميلان شراء آخر كمية في نفس اللحظة، واحد فقط يمكن أن ينجح.

## Payment Boundary
Sprint 18 لا يعتبر `pending_payment` طلبًا مؤكدًا.

في Sprint 19:
- Payment success → reservation converted + order confirmed.
- Payment failure/timeout → reservation released/expired.

# Menu Domain

## Signature Menu
القائمة الدائمة التي تعرّف تخصص الشيف.

خصائص الطبق:
- name
- description
- category
- base price
- prep notice hours
- special order availability
- active/inactive
- image
- display order

وجود الطبق في Signature Menu لا يعني أنه متاح للطلب الفوري.

## Chef Workday
يمثل يوم تشغيل الشيف:
- service date
- open/closed
- cutoff
- delivery window

## Today’s Kitchen
نسخة يومية محدودة من أطباق Signature Menu.

لكل صنف:
- price for the day
- total quantity
- available quantity
- max per order
- available / sold_out / hidden

## Business Rules
1. لا يمكن إضافة طبق لمطبخ اليوم إلا إذا كان من قائمة نفس الشيف.
2. الطبق يجب أن يكون Active.
3. مطبخ اليوم يتطلب Workday مفتوحًا.
4. الصنف بكمية صفر يصبح `sold_out`.
5. Public API لا يعرض hidden items.
6. Public API لا يعرض عناصر Workday مغلق.
7. الكمية المتاحة لا تتجاوز الكمية الأصلية.
8. إلغاء تنشيط طبق يخفيه من Signature Menu العام.

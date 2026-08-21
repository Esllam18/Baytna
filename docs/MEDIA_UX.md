# Sprint 41 — Media UX

## Customer Support Attachments

Allowed mobile attachment types in Sprint 41:
- JPEG
- PNG
- WebP

Backend media remains capable of PDF where appropriate, but the mobile picker in this sprint intentionally focuses on photos.

Support media:
```text
purpose = support_attachment
visibility = private
```

The customer can attach:
- up to 5 images when creating a ticket,
- one new image with a support reply in the current mobile UX.

Backend remains the final source of the maximum attachment count.

## Chef Dish Images

Dish images:
```text
purpose = dish_image
visibility = public
```

The upload must be:
- owned by the chef,
- complete,
- ready,
- public,
- correct purpose.

Only then can it be bound to the chef's dish.

## Driver Delivery Proof

Driver proof:
```text
purpose = delivery_proof
visibility = private
```

The delivery service validates proof ownership and readiness before accepting it.

## Storage

All three media UX flows use the same provider abstraction:
- local signed storage in development/tests,
- S3-compatible presigned storage in pilot/production.

Application code never writes object-storage credentials.

# Sprint 39 — Delivery Proof & Navigation

## Proof-of-Delivery Principle

The driver cannot complete an order with an empty proof.

Backend accepted proof types remain:
- otp
- photo
- signature
- manual

Sprint 39 mobile UI exposes:
- photo
- OTP/reference
- manual reference

Signature capture is intentionally not simulated as a fake scribble pad in this sprint.

## Photo Proof

Media metadata:

```text
purpose = delivery_proof
visibility = private
```

The image is uploaded through the existing signed-transfer system.

The app does not send a local device URI to the delivery endpoint.

It sends the completed Baytna Media Asset UUID.

## Security

Before accepting a photo as proof, backend verifies:
- current driver owns the asset,
- asset status is ready,
- purpose is delivery_proof.

This prevents reusing another user's file or an unfinished upload as proof.

## Navigation

Pickup:
```text
chef name + pickup area
→ external maps search
```

Dropoff:
```text
latitude + longitude
→ external maps search
```

Fallback:
```text
area + street + building + floor + apartment
→ external maps search
```

This is only a map-launch integration.

No claims are made for:
- turn-by-turn SDK integration,
- live vehicle tracking,
- distance matrix,
- traffic-aware ETA,
- route optimization.

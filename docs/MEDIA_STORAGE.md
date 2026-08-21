# Sprint 29 — Media / Object Storage Domain

## Upload Lifecycle

```text
client asks API for upload
        ↓
media_assets: pending
        ↓
signed provider upload URL
        ↓
client uploads directly
        ↓
client calls complete
        ↓
provider HEAD / metadata validation
        ↓
media_assets: ready
```

This keeps large binary bodies away from the main API in production.

## Development Provider
`storage_provider=local`

The API returns a signed local upload route so integration tests can exercise the complete flow with real bytes.

## Production Provider
`storage_provider=s3`

Uses boto3 presigned URLs:
- `put_object`
- `get_object`
- `head_object`
- `delete_object`

Works with AWS S3 and S3-compatible endpoints when configured.

## Asset Purposes
- chef_avatar
- dish_image
- support_attachment
- delivery_proof
- customer_attachment
- other

## Visibility
Private is the default.

Public is limited to:
- chef_avatar
- dish_image

Support attachments and delivery proofs cannot accidentally become public through this API.

## Verification
Completion verifies:
- object exists
- exact size matches expected size
- max upload size is respected
- checksum is captured where provider exposes it

## Authorization
Private media:
- owner
- admin

Public media:
- signed public download URL

Direct permanent object URLs are not stored/exposed.

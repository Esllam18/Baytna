# Media Attachments — Sprint 30

## Dish Image
Chef may bind only a media asset that is:
- owned by the chef
- ready
- purpose = dish_image
- visibility = public

## Support Attachments
Customer/admin support attachments must be owned by the sender and use `support_attachment` or `customer_attachment` purpose. Attachments are linked to the exact support message.

## Delivery Photo Proof
When `proof_type=photo`, `media_asset_id` is mandatory. The asset must be owned by the driver, ready, and purpose = `delivery_proof`.

import { driverApi, http } from "../api";

export interface LocalImage {
  uri:string;
  fileName:string|null;
  mimeType:"image/jpeg"|"image/png"|"image/webp";
  fileSize?:number|null;
}

export async function uploadDeliveryProof(image:LocalImage) {
  const source=await fetch(image.uri);
  if (!source.ok) throw new Error("proof_image_read_failed");
  const blob=await source.blob();
  const size=image.fileSize ?? blob.size;
  if (!size || size<=0) throw new Error("proof_image_empty");

  const upload=await driverApi.createMediaUpload({
    purpose:"delivery_proof",
    visibility:"private",
    filename:image.fileName ?? "delivery-proof.jpg",
    mime_type:image.mimeType,
    size_bytes:size,
  });

  const uploadUrl=http.resolveTransferUrl(upload.upload_url);
  const result=await fetch(uploadUrl,{
    method:"PUT",
    headers:upload.upload_headers,
    body:blob,
  });
  if (!result.ok) throw new Error(`proof_upload_failed_${result.status}`);

  const completed=await driverApi.completeMedia(upload.asset.id);
  if (completed.asset.status!=="ready") throw new Error("proof_media_not_ready");
  return completed.asset;
}

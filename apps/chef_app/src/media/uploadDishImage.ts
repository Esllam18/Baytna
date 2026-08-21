import { chefApi, http } from "../api";

export interface LocalDishImage {
  uri: string;
  fileName: string | null;
  mimeType: "image/jpeg" | "image/png" | "image/webp";
  fileSize?: number | null;
}

export async function uploadDishImage(dishId: string, image: LocalDishImage) {
  const source = await fetch(image.uri);
  if (!source.ok) throw new Error("dish_image_read_failed");

  const blob = await source.blob();
  const size = image.fileSize ?? blob.size;
  if (!size || size <= 0) throw new Error("dish_image_empty");

  const upload = await chefApi.createDishMediaUpload({
    filename: image.fileName ?? `dish-${dishId}.jpg`,
    mime_type: image.mimeType,
    size_bytes: size,
  });

  const uploaded = await fetch(http.resolveTransferUrl(upload.upload_url), {
    method: "PUT",
    headers: upload.upload_headers,
    body: blob,
  });
  if (!uploaded.ok) throw new Error(`dish_image_upload_${uploaded.status}`);

  const completed = await chefApi.completeMedia(upload.asset.id);
  if (completed.asset.status !== "ready") {
    throw new Error("dish_image_not_ready");
  }

  return chefApi.setDishMedia(dishId, completed.asset.id);
}

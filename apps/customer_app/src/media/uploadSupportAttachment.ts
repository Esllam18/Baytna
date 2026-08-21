import { customerApi, http } from "../api";

export interface LocalAttachment {
  uri: string;
  fileName: string | null;
  mimeType: "image/jpeg" | "image/png" | "image/webp";
  fileSize?: number | null;
}

export async function uploadSupportAttachment(image: LocalAttachment) {
  const source = await fetch(image.uri);
  if (!source.ok) throw new Error("support_attachment_read_failed");

  const blob = await source.blob();
  const size = image.fileSize ?? blob.size;
  if (!size || size <= 0) throw new Error("support_attachment_empty");

  const upload = await customerApi.createMediaUpload({
    purpose: "support_attachment",
    visibility: "private",
    filename: image.fileName ?? "support-image.jpg",
    mime_type: image.mimeType,
    size_bytes: size,
  });

  const result = await fetch(http.resolveTransferUrl(upload.upload_url), {
    method: "PUT",
    headers: upload.upload_headers,
    body: blob,
  });
  if (!result.ok) throw new Error(`support_attachment_upload_${result.status}`);

  const completed = await customerApi.completeMedia(upload.asset.id);
  if (completed.asset.status !== "ready") {
    throw new Error("support_attachment_not_ready");
  }
  return completed.asset;
}

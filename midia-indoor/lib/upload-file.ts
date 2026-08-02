import path from "node:path";

const mimeTypes: Record<string, string> = {
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".png": "image/png",
  ".webp": "image/webp",
  ".mp4": "video/mp4",
  ".webm": "video/webm",
};

export function safeUploadFilename(requested: string) {
  const filename = path.basename(requested);
  return filename && filename === requested ? filename : null;
}

export function uploadMimeType(filename: string) {
  return mimeTypes[path.extname(filename).toLowerCase()] || null;
}

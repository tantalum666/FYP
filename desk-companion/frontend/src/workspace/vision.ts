export const MAX_VOICE_IMAGE_BASE64 = 256 * 1024;

export function voiceImageSize(width: number, height: number) {
  if (
    !Number.isFinite(width) ||
    !Number.isFinite(height) ||
    width <= 0 ||
    height <= 0
  )
    throw new Error("INVALID_VOICE_IMAGE");
  const scale = Math.min(1, 1280 / width, 720 / height);
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

export function encodeVoiceImage(
  source: CanvasImageSource,
  width: number,
  height: number,
) {
  const size = voiceImageSize(width, height);
  const canvas = document.createElement("canvas");
  canvas.width = size.width;
  canvas.height = size.height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("VOICE_IMAGE_UNAVAILABLE");
  context.drawImage(source, 0, 0, size.width, size.height);
  for (const quality of [0.8, 0.6, 0.4]) {
    const url = canvas.toDataURL("image/jpeg", quality);
    if (!url.startsWith("data:image/jpeg;base64,"))
      throw new Error("INVALID_VOICE_IMAGE");
    const image = url.slice(url.indexOf(",") + 1);
    if (image.length <= MAX_VOICE_IMAGE_BASE64) return image;
  }
  throw new Error("VOICE_IMAGE_TOO_LARGE");
}

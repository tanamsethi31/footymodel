/** VAPID applicationServerKey helpers for Web Push subscribe(). */

export function normalizeVapidPublicKey(raw: string | null | undefined): string | null {
  if (!raw) return null;

  let key = raw.trim();
  if (
    (key.startsWith('"') && key.endsWith('"')) ||
    (key.startsWith("'") && key.endsWith("'"))
  ) {
    key = key.slice(1, -1).trim();
  }

  if (key.includes("BEGIN")) {
    const body = key
      .replace(/-----BEGIN [^-]+-----/g, "")
      .replace(/-----END [^-]+-----/g, "")
      .replace(/\s/g, "");
    const fromPem = extractUncompressedPointFromSpki(body);
    if (fromPem) return fromPem;
    key = body;
  } else {
    key = key.replace(/\s/g, "");
  }

  if (!key || !/^[A-Za-z0-9+/_-]+=*$/.test(key)) return null;
  return key;
}

function extractUncompressedPointFromSpki(base64Body: string): string | null {
  try {
    const binary = atob(base64Body.replace(/-/g, "+").replace(/_/g, "/"));
    if (binary.length < 65) return null;
    const point = binary.slice(-65);
    if (point.charCodeAt(0) !== 0x04) return null;
    const bytes = Uint8Array.from(point, (c) => c.charCodeAt(0));
    return uint8ArrayToUrlBase64(bytes);
  } catch {
    return null;
  }
}

function uint8ArrayToUrlBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const normalized = normalizeVapidPublicKey(base64String);
  if (!normalized) {
    throw new Error("Invalid VAPID public key format");
  }
  const padding = "=".repeat((4 - (normalized.length % 4)) % 4);
  const base64 = (normalized + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from(rawData, (c) => c.charCodeAt(0));
}

export function isValidVapidPublicKey(raw: string | null | undefined): boolean {
  try {
    const bytes = urlBase64ToUint8Array(raw ?? "");
    // Uncompressed P-256 public key: 0x04 + X + Y
    return bytes.length === 65 && bytes[0] === 0x04;
  } catch {
    return false;
  }
}

export function resolveVapidPublicKey(
  ...candidates: Array<string | null | undefined>
): string | null {
  for (const candidate of candidates) {
    const normalized = normalizeVapidPublicKey(candidate);
    if (normalized && isValidVapidPublicKey(normalized)) return normalized;
  }
  return null;
}

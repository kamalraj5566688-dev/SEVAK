import DOMPurify from 'dompurify';

/**
 * Sanitize backend-rendered content for safe UI rendering (C-02).
 *
 * Uses DOMPurify to strip any HTML/script markup from document-derived
 * text before it is inserted into the DOM. Falls back to textContent-style
 * escaping if DOMPurify is unavailable.
 */
export const sanitizeHtml = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  const text = String(value);

  // DOMPurify with USE_PROFILES = { html: false } strips all HTML tags
  // and attributes, leaving only safe text content.
  if (typeof DOMPurify !== 'undefined' && DOMPurify.sanitize) {
    return DOMPurify.sanitize(text, { USE_PROFILES: { html: false } });
  }

  // Fallback: escape HTML special characters.
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
};

/**
 * Validate a URL for safe use in href attributes (C-02).
 *
 * Only allows http:// and https:// schemes. Blocks javascript:,
 * data:, vbscript:, file:, and other dangerous schemes.
 * Returns null if the URL is unsafe or empty.
 */
export const sanitizeUrl = (value: unknown): string | null => {
  if (value === null || value === undefined) return null;
  const url = String(value).trim();
  if (!url) return null;

  try {
    const parsed = new URL(url);
    const scheme = parsed.protocol.toLowerCase();
    if (scheme !== 'http:' && scheme !== 'https:') {
      return null;
    }
    return url;
  } catch {
    return null;
  }
};

/**
 * Validate base64-encoded audio data (M-05).
 *
 * Checks that the string is valid base64 and decodes to a reasonable
 * audio size. Returns null if invalid.
 */
export const validateBase64Audio = (value: unknown): string | null => {
  if (value === null || value === undefined) return null;
  const b64 = String(value).trim();
  if (!b64) return null;

  // Base64 regex: must be valid base64 characters with optional padding.
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(b64)) {
    return null;
  }

  // Must be at least 100 bytes when decoded (tiny audio is likely silent/error).
  try {
    const decoded = atob(b64);
    if (decoded.length < 100) {
      return null;
    }
    return b64;
  } catch {
    return null;
  }
};

/**
 * Validate file magic bytes against its claimed extension (M-06).
 *
 * Reads the first bytes of the file and checks the file signature matches
 * the extension. Returns true if the signature is valid, false otherwise.
 * This is a client-side pre-check; the backend also verifies signatures.
 */
export const validateFileMagicBytes = async (file: File): Promise<boolean> => {
  const ext = (file.name || '').split('.').pop()?.toLowerCase();
  if (!ext) return false;

  try {
    const slice = file.slice(0, 16);
    const ab = await slice.arrayBuffer();
    const header = new Uint8Array(ab);

    const bytes = Array.from(header).map((b) => String.fromCharCode(b)).join('');

    switch (ext) {
      case 'pdf':
        return bytes.startsWith('%PDF');
      case 'png':
        return (
          header[0] === 0x89 &&
          header[1] === 0x50 &&
          header[2] === 0x4e &&
          header[3] === 0x47
        );
      case 'jpg':
      case 'jpeg':
        return header[0] === 0xff && header[1] === 0xd8 && header[2] === 0xff;
      case 'webp':
        return (
          header[0] === 0x52 &&
          header[1] === 0x49 &&
          header[2] === 0x46 &&
          header[3] === 0x46 &&
          header[8] === 0x57 &&
          header[9] === 0x45 &&
          header[10] === 0x42 &&
          header[11] === 0x50
        );
      default:
        return false;
    }
  } catch {
    return false;
  }
};

/**
 * Development-only debug logger. Strips sensitive data in production builds
 * to prevent accidental PII exposure via console.log (L-03).
 */
export const debugLog = (message: string, ...args: unknown[]): void => {
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    console.log(message, ...args);
  }
};

export const debugWarn = (message: string, ...args: unknown[]): void => {
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    console.warn(message, ...args);
  }
};

export const debugError = (message: string, ...args: unknown[]): void => {
  if (import.meta.env.DEV || import.meta.env.MODE === 'development') {
    console.error(message, ...args);
  }
};

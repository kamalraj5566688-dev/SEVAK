import { SevakAnalysisResult, SupportedLanguage } from '../types';
import { debugLog, debugWarn, debugError } from '../utils/security';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const SEVAK_API_KEY = import.meta.env.VITE_SEVAK_API_KEY || '';

export interface AnalyzeDocumentPayload {
  file: File;
  language: SupportedLanguage;
}

export interface VoiceRespondPayload {
  question: string;
  documentId?: string;
  language: SupportedLanguage;
}

/**
 * Converts snake_case object keys to camelCase recursively.
 * The FastAPI backend returns snake_case keys; the frontend TypeScript type
 * and components expect camelCase. Without this transformation, every
 * backend-sourced field would be undefined at runtime.
 */
function snakeToCamel(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  if (obj !== null && typeof obj === 'object') {
    const result: any = {};
    for (const [key, value] of Object.entries(obj)) {
      const camelKey = key.replace(/[_](.)/g, (_, char) => char.toUpperCase());
      result[camelKey] = snakeToCamel(value);
    }
    return result;
  }
  return obj;
}

export class SevakApiService {
  private static async checkBackendHealth(): Promise<boolean> {
    const maxRetries = 2;
    for (let attempt = 0; attempt < maxRetries; attempt += 1) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3500);
        const res = await fetch(`${API_BASE_URL}/health`, {
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          return true;
        }
      } catch {
        // retry on next iteration
      }
    }
    return false;
  }

  /**
   * POST /api/analyze-document
   */
  static async analyzeDocument(file: File, language: SupportedLanguage): Promise<SevakAnalysisResult> {
    const isOnline = await this.checkBackendHealth();

    if (isOnline) {
      try {
        const formData = new FormData();
        formData.append('document', file);
        formData.append('language', language);

        const response = await fetch(`${API_BASE_URL}/api/analyze-document`, {
          method: 'POST',
          headers: SEVAK_API_KEY ? { 'X-API-Key': SEVAK_API_KEY } : {},
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        const camelData = snakeToCamel(data) as Partial<SevakAnalysisResult>;
        // Preserve the backend's demo-fallback flag instead of overwriting it.
        return {
          ...camelData,
          isDemoFallback: camelData.isDemoFallback ?? false,
        } as SevakAnalysisResult;
      } catch (err) {
        console.warn('Real backend call failed, falling back to safe local demo parser:', err);
      }
    }

    // Backend unavailable: return an honest error instead of faking a document analysis.
    throw new Error(
      `Backend unreachable at ${API_BASE_URL}. Start the FastAPI backend and try again.`
    );
  }

  /**
   * POST /api/voice/transcribe
   */

  static async transcribeAudio(audioBlob: Blob, language: SupportedLanguage): Promise<string> {
    try {
      const formData = new FormData();

      const blobType = (audioBlob.type || '').toLowerCase();
      let extension = 'wav';
      let contentType = 'audio/wav';

      if (blobType.includes('webm')) {
        extension = 'webm';
        contentType = 'audio/webm';
      } else if (blobType.includes('ogg')) {
        extension = 'ogg';
        contentType = 'audio/ogg';
      } else if (blobType.includes('mp4') || blobType.includes('m4a')) {
        extension = 'm4a';
        contentType = 'audio/mp4';
      } else if (blobType.includes('wav')) {
        extension = 'wav';
        contentType = 'audio/wav';
      }

      const audioFile = new File([audioBlob], `sevak-voice-${Date.now()}.${extension}`, { type: contentType });
      formData.append('audio', audioFile);
      formData.append('language', language);

      console.log('[SEVAK][STT] Sending audio:', {
        type: audioBlob.type,
        size: audioBlob.size,
        language,
      });

      const response = await fetch(
        `${API_BASE_URL}/api/voice/transcribe`,
        {
          method: 'POST',
          headers: SEVAK_API_KEY ? { 'X-API-Key': SEVAK_API_KEY } : {},
          body: formData,
        }
      );

      const rawText = await response.text();

      if (!response.ok) {
        debugError(
          '[SEVAK][STT] Backend error:',
          response.status,
        );

        throw new Error(
          `Speech transcription failed: ${response.status}`
        );
      }

      let data: any = {};

      try {
        data = JSON.parse(rawText);
      } catch {
        throw new Error('Invalid STT response from backend');
      }

      const transcript = (
        data.transcript ||
        data.transcription ||
        data.output?.literal ||
        ''
      ).trim();

      debugLog('[SEVAK][STT] Transcript:', transcript);

      return transcript;
    } catch (error) {
      console.error('[SEVAK][STT] Failed:', error);
      return '';
    }
  }
/**
   * POST /api/voice/respond & POST /api/ask
   */

  static async askQuestion(payload: VoiceRespondPayload): Promise<string> {
    const question = payload.question.trim();

    if (!question) {
      return '';
    }

    // No document: send the real user question to the backend.
    // Backend handles conversational/general questions and
    // document-grounded questions when a document is available.
    try {
      debugLog('[SEVAK][ASK] Sending question:', {
        question,
        documentId: payload.documentId,
        language: payload.language,
      });

      const response = await fetch(
        `${API_BASE_URL}/api/ask`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(SEVAK_API_KEY ? { 'X-API-Key': SEVAK_API_KEY } : {}),
          },
          body: JSON.stringify({
            question,
            document_id: payload.documentId,
            language: payload.language,
          }),
        }
      );

      const rawText = await response.text();

      if (!response.ok) {
        debugError(
          '[SEVAK][ASK] Backend error:',
          response.status,
        );

        throw new Error(
          `Question request failed: ${response.status}`
        );
      }

      let data: any = {};

      try {
        data = JSON.parse(rawText);
      } catch {
        throw new Error('Invalid answer response from backend');
      }

      const answer = (
        data.answer ||
        data.response ||
        data.message ||
        ''
      ).trim();

      debugLog('[SEVAK][ASK] Answer:', answer);

      if (!answer) {
        throw new Error('Backend returned an empty answer');
      }

      return answer;
    } catch (error) {
      console.error('[SEVAK][ASK] Failed:', error);

      const q = question.toLowerCase();

      if (
        q.includes('deadline') ||
        q.includes('kab tak') ||
        q.includes('last date') ||
        q.includes('tarikh')
      ) {
        return 'Notice ke anusar deadline document mein di gayi antim tithi ko check karein.';
      }

      if (
        q.includes('jail') ||
        q.includes('police') ||
        q.includes('arrest') ||
        q.includes('court')
      ) {
        return 'Is question ka exact answer dene ke liye SEVAK ko uploaded document ka context chahiye.';
      }

      if (
        q.includes('paise') ||
        q.includes('fine') ||
        q.includes('kitna') ||
        q.includes('amount')
      ) {
        return 'Is question ka exact amount document se verify karna zaroori hai.';
      }

      return `SEVAK ne aapka question suna: "${question}". Lekin backend se document-grounded answer nahi mil saka.`;
    }
  }

}

/**
 * Client-side heuristic used to flag uploads that appear to be AI-generated
 * or synthetic rather than genuine issued documents.
 *
 * This is a best-effort, non-blocking signal: it inspects the file name and,
 * for PDFs, a bounded slice of the file bytes for producer/tool metadata. It
 * never blocks upload — it only surfaces a warning so the user verifies the
 * content against the original issuing source.
 */
export interface AIDetectionSignal {
  likely: boolean;
  signals: string[];
}

const AI_NAME_PATTERNS = [
  /\b(chatgpt|gpt-?4|dall-e|midjourney|claude-ai|synthetic-doc|deepfake|copy\.ai|writesonic|rytr)\b/i,
  /^ai[_-]/i,
];

const AI_PRODUCER_PATTERNS = [
  /\/Producer\s*\([^)]*(?:chatgpt|openai|anthropic|claude|jasper|writesonic)/i,
  /\/Creator\s*\([^)]*(?:chatgpt|openai|anthropic|claude|jasper|writesonic)/i,
];

async function scanPdfProducer(file: File): Promise<string[]> {
  const signals: string[] = [];
  try {
    const slice = file.slice(0, 2 * 1024 * 1024);
    const ab = await slice.arrayBuffer();
    const text = new TextDecoder('latin-1', { fatal: false }).decode(ab);

    for (const pattern of AI_PRODUCER_PATTERNS) {
      if (pattern.test(text)) {
        signals.push(`PDF metadata suggests AI generation: ${pattern.source}`);
      }
    }
  } catch {
    // Ignore read errors; detection is best-effort only.
  }
  return signals;
}

export async function detectAIGeneratedSignals(
  file: File
): Promise<AIDetectionSignal> {
  const signals: string[] = [];
  const name = (file.name || '').toLowerCase();

  for (const pattern of AI_NAME_PATTERNS) {
    if (pattern.test(name)) {
      signals.push(`File name indicates AI generation: ${pattern.source}`);
    }
  }

  if (
    file.type === 'application/pdf' ||
    /\.(pdf)$/i.test(name)
  ) {
    signals.push(...(await scanPdfProducer(file)));
  }
  return { likely: signals.length > 0, signals };
}







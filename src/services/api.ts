import { SevakAnalysisResult, SupportedLanguage } from '../types';
import { SAMPLE_DOCUMENTS } from '../data/sampleDocuments';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

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
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1200);
      const res = await fetch(`${API_BASE_URL}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);
      return res.ok;
    } catch {
      return false;
    }
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

    // Demo Fallback Mode (Safe, informative, responsive to file characteristics)
    await new Promise((r) => setTimeout(r, 2200)); // realistic thinking latency

    const fileNameLower = file.name.toLowerCase();
    let template = SAMPLE_DOCUMENTS.echallan;

    if (fileNameLower.includes('bank') || fileNameLower.includes('kyc') || fileNameLower.includes('sbi') || fileNameLower.includes('hdfc')) {
      template = SAMPLE_DOCUMENTS.bank_kyc;
    } else if (fileNameLower.includes('tax') || fileNameLower.includes('itd') || fileNameLower.includes('income') || fileNameLower.includes('142')) {
      template = SAMPLE_DOCUMENTS.tax_notice;
    }

    const sizeInMB = (file.size / (1024 * 1024)).toFixed(1);

    return {
      ...template,
      id: `doc-${Date.now()}`,
      originalFileName: file.name,
      fileSize: `${sizeInMB} MB`,
      fileType: file.type || 'application/pdf',
      uploadDate: new Date().toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      }),
      isDemoFallback: true,
    };
  }

  /**
   * POST /api/voice/transcribe
   */

  static async transcribeAudio(audioBlob: Blob, language: SupportedLanguage): Promise<string> {
    try {
      const formData = new FormData();

      const extension = audioBlob.type.includes('webm')
        ? 'webm'
        : audioBlob.type.includes('ogg')
          ? 'ogg'
          : 'wav';

      formData.append(
        'audio',
        audioBlob,
        `sevak-voice-${Date.now()}.${extension}`
      );
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
          body: formData,
        }
      );

      const rawText = await response.text();

      if (!response.ok) {
        console.error(
          '[SEVAK][STT] Backend error:',
          response.status,
          rawText
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

      console.log('[SEVAK][STT] Transcript:', transcript);

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
      console.log('[SEVAK][ASK] Sending question:', {
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
        console.error(
          '[SEVAK][ASK] Backend error:',
          response.status,
          rawText
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

      console.log('[SEVAK][ASK] Answer:', answer);

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






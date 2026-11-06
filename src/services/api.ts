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
        return {
          ...data,
          isDemoFallback: false,
        };
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
      formData.append('audio', audioBlob);
      formData.append('language', language);

      const response = await fetch(`${API_BASE_URL}/api/voice/transcribe`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        return data.transcript || '';
      }
    } catch {
      // ignore
    }
    return '';
  }

  /**
   * POST /api/voice/respond & POST /api/ask
   */
  static async askQuestion(payload: VoiceRespondPayload): Promise<string> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const data = await response.json();
        return data.answer || data.response;
      }
    } catch {
      // fallback
    }

    // Contextual demo answer based on query
    const q = payload.question.toLowerCase();
    if (q.includes('deadline') || q.includes('kab tak') || q.includes('last date') || q.includes('tarikh')) {
      return 'Notice ke anusar iska antargat action lene ki antim tithi 21 November 2026 hai. Uske pehle dispute ya payment clear karein.';
    }
    if (q.includes('jail') || q.includes('police') || q.includes('arrest') || q.includes('court')) {
      return 'Ghabraye nahi! Yeh shuruati administrative notice hai. Isme seedhe arrest ya impound nahi hota. Sabse pehle apna reply portal par darj karein.';
    }
    if (q.includes('paise') || q.includes('fine') || q.includes('kitna') || q.includes('amount')) {
      return 'Document ke anusaar prescribed amount Rs. 2,000 dikh raha hai. Official Parivahan/Bank portal par exact challan ID dalkar verify kar sakte hain.';
    }

    return 'SEVAK ne aapka prashna suna: Aap is document ka official portal verify karein aur 3 practical steps follow karein.';
  }
}

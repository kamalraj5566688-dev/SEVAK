export type SupportedLanguage = 'hinglish' | 'hindi' | 'english' | 'bhojpuri' | 'maithili';

export type AppView = 'home' | 'file_selected' | 'analyzing' | 'results';

export interface NextStepItem {
  step: number;
  title: string;
  description: string;
  actionUrl?: string;
}

export interface SevakAnalysisResult {
  id: string;
  documentTitle: string;
  category: 'Traffic Police Notice' | 'Banking & KYC' | 'Income Tax Department' | 'Government Notice' | 'Legal Summons';
  originalFileName: string;
  fileSize: string;
  fileType: string;
  uploadDate: string;
  confidenceScore: number;
  isDemoFallback?: boolean;

  // Key SEVAK Response Structure
  what: {
    summary: string;
    details: string;
  };
  why: {
    significance: string;
    urgencyReason: string;
  };
  nextSteps: [NextStepItem, NextStepItem, NextStepItem];
  rights: {
    title: string;
    safeguards: string[];
    disclaimer: string;
  };
  deadline: {
    hasDeadline: boolean;
    date?: string;
    daysRemaining?: number;
    urgencyLevel?: 'high' | 'medium' | 'low';
    consequenceText?: string;
  };
  source: {
    issuingAuthority: string;
    legalSection: string;
    referenceNumber: string;
    officialPortalUrl?: string;
  };

  // Multi-lingual voice audio transcriptions
  voiceSummaries: Record<SupportedLanguage, string>;
}

export interface VoiceState {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  error?: string;
  status: 'idle' | 'listening' | 'processing' | 'responded';
  response?: string;
}

import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { LanguageSelector } from './components/LanguageSelector';
import { HowSevakHelps } from './components/HowSevakHelps';
import { SafetyCard } from './components/SafetyCard';
import { Footer } from './components/Footer';
import { VoiceModal } from './components/VoiceModal';
import { UploadModal } from './components/UploadModal';
import { AnalyzingView } from './components/AnalyzingView';
import { ResultsView } from './components/ResultsView';
import { CookieConsent } from './components/CookieConsent';
import {
  AppView,
  SupportedLanguage,
  SevakAnalysisResult,
} from './types';
import { SevakApiService, detectAIGeneratedSignals } from './services/api';
import { ShieldAlert, AlertCircle } from 'lucide-react';
import { SAMPLE_DOCUMENTS } from './data/sampleDocuments';

export default function App() {
  const [view, setView] = useState<AppView>('home');
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>('hinglish');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<SevakAnalysisResult | null>(null);
  const [aiWarning, setAiWarning] = useState<{
    likely: boolean;
    signals: string[];
  } | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // File Upload flow
  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setAnalysisResult(null);
    setAiWarning(null);
    setView('analyzing');

    try {
      // Best-effort AI-generated document detection (non-blocking warning only).
      const aiSignal = await detectAIGeneratedSignals(file);
      setAiWarning(aiSignal);

      const result = await SevakApiService.analyzeDocument(
        file,
        selectedLanguage
      );

      // Preserve the actual uploaded filename.
      result.originalFileName = file.name;

      // Real uploads are not demo documents.
      // Demo mode remains available through explicit sample buttons.
      result.isDemoFallback = false;

      setAnalysisResult(result);
    } catch (err) {
      console.error('Document analysis failed:', err);
      setAnalysisResult(null);
      setView('home');
      setAnalysisError(
        err instanceof Error
          ? err.message
          : 'Document analysis failed. Please try uploading the file again.'
      );
    }
  };

  const handleSelectSampleDoc = (sample: SevakAnalysisResult) => {
    setSelectedFile(null);
    setAnalysisResult(sample);
    setView('analyzing');
    setAiWarning(null);
    setAnalysisError(null);
  };

  const handleAnalysisComplete = () => {
    if (!analysisResult) {
      console.error('Analysis completed without a result.');
      setView('home');
      setAnalysisError(null);
      return;
    }

    setView('results');
    setAnalysisError(null);
  };

  const handleGoHome = () => {
    setView('home');
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  const handleReset = () => {
    setView('home');
    setSelectedFile(null);
    setAnalysisResult(null);
    setAiWarning(null);
    setAnalysisError(null);
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF7F0] text-slate-800 flex flex-col justify-between selection:bg-orange-200 selection:text-orange-950 font-sans">
      {/* Top Navigation */}
      <Navbar
        onGoHome={handleGoHome}
        onOpenUpload={() => setIsUploadModalOpen(true)}
        selectedLanguage={selectedLanguage}
        onSelectLanguage={setSelectedLanguage}
      />

      {/* Main Content Area Based on State */}
      <main className="flex-1 w-full">
        {analysisError && (
          <div className="w-full px-4 sm:px-8 lg:px-12 py-4">
            <div className="max-w-xl mx-auto p-4 bg-red-50 rounded-xl border border-red-200/80 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-bold text-red-900 mb-1">
                  Document analysis failed
                </h4>
                <p className="text-xs text-red-800 leading-relaxed">
                  {analysisError}
                </p>
                <button
                  onClick={() => setAnalysisError(null)}
                  className="mt-2 text-xs underline text-[#0B57D0] hover:text-[#0848af]"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}
        {view === 'home' && (
          <div className="w-full animate-in fade-in duration-200">
            {/* Hero Section */}
            <Hero
              onFileSelect={handleFileSelect}
              onVoiceClick={() => setIsVoiceModalOpen(true)}
              onSelectSampleDoc={handleSelectSampleDoc}
            />

            {/* Pill-Style Language Selector */}
            <LanguageSelector
              selectedLanguage={selectedLanguage}
              onSelectLanguage={setSelectedLanguage}
            />

            {/* HOW SEVAK HELPS + SAFETY FIRST CARDS ROW */}
            <section className="w-full px-4 sm:px-8 lg:px-12 pt-2 pb-6 max-w-7xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                {/* 4 Feature Cards: WHAT, WHY, NEXT, SOURCE */}
                <div className="lg:col-span-8 flex">
                  <HowSevakHelps />
                </div>

                {/* SAFETY FIRST Card */}
                <div className="lg:col-span-4 flex">
                  <SafetyCard />
                </div>
              </div>
            </section>
          </div>
        )}

        {view === 'analyzing' && (
          <AnalyzingView
            fileName={
              selectedFile?.name ||
              analysisResult?.originalFileName ||
              'Indian_Legal_Notice.pdf'
            }
            fileSize={
              selectedFile
                ? `${(selectedFile.size / (1024 * 1024)).toFixed(1)} MB`
                : analysisResult?.fileSize
            }
            language={selectedLanguage}
            onAnalysisComplete={handleAnalysisComplete}
          />
        )}

        {view === 'results' && analysisResult && (
          <>
            {aiWarning && aiWarning.likely && (
              <div className="mb-4 p-4 bg-amber-50 rounded-xl border border-amber-200/80 flex items-start gap-3">
                <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-amber-900 mb-1">
                    AI-generated document detected
                  </h4>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    This upload appears to be AI-generated or synthetic. Verify
                    the content against the original issuing source before acting
                    on it.
                  </p>
                  {aiWarning.signals.slice(0, 3).map((signal, i) => (
                    <p key={i} className="text-[10px] text-amber-600 mt-1">
                      {signal}
                    </p>
                  ))}
                </div>
              </div>
            )}
            <ResultsView
              result={analysisResult}
              selectedLanguage={selectedLanguage}
              onSelectLanguage={setSelectedLanguage}
              onReset={handleReset}
              onOpenVoiceModal={() => setIsVoiceModalOpen(true)}
            />
          </>
        )}
      </main>

      {/* Footer */}
      <Footer />

      {/* Cookie consent banner */}
      <CookieConsent />

      {/* Interactive Modals */}
      <VoiceModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        selectedLanguage={selectedLanguage}
        onDocumentAnalyzeRequested={() => setIsUploadModalOpen(true)}
        currentDocumentId={analysisResult?.id}
      />

      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onFileSelect={handleFileSelect}
        onSelectSampleDoc={handleSelectSampleDoc}
      />
    </div>
  );
}












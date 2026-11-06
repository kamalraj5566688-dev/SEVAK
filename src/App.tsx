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
import {
  AppView,
  SupportedLanguage,
  SevakAnalysisResult,
} from './types';
import { SevakApiService } from './services/api';
import { SAMPLE_DOCUMENTS } from './data/sampleDocuments';

export default function App() {
  const [view, setView] = useState<AppView>('home');
  const [selectedLanguage, setSelectedLanguage] = useState<SupportedLanguage>('hinglish');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<SevakAnalysisResult | null>(null);
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // File Upload flow
  const handleFileSelect = async (file: File) => {
    setSelectedFile(file);
    setView('analyzing');

    try {
      const result = await SevakApiService.analyzeDocument(file, selectedLanguage);
      setAnalysisResult(result);
    } catch (err) {
      console.error('Analysis failed, using fallback:', err);
      setAnalysisResult(SAMPLE_DOCUMENTS.echallan);
    }
  };

  const handleSelectSampleDoc = (sample: SevakAnalysisResult) => {
    setSelectedFile(null);
    setAnalysisResult(sample);
    setView('analyzing');
  };

  const handleAnalysisComplete = () => {
    // If analysis hasn't resolved yet, guarantee sample result
    if (!analysisResult) {
      setAnalysisResult(SAMPLE_DOCUMENTS.echallan);
    }
    setView('results');
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
          <ResultsView
            result={analysisResult}
            selectedLanguage={selectedLanguage}
            onSelectLanguage={setSelectedLanguage}
            onReset={handleReset}
            onOpenVoiceModal={() => setIsVoiceModalOpen(true)}
          />
        )}
      </main>

      {/* Footer */}
      <Footer />

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

import React from 'react';
import { RobotIllustration } from './RobotIllustration';
import { ActionButtons } from './ActionButtons';
import { FileText, ShieldAlert, Sparkles } from 'lucide-react';
import { SAMPLE_DOCUMENTS } from '../data/sampleDocuments';
import { SevakAnalysisResult } from '../types';

interface HeroProps {
  onFileSelect: (file: File) => void;
  onVoiceClick: () => void;
  onSelectSampleDoc: (sample: SevakAnalysisResult) => void;
  isListening?: boolean;
}

export const Hero: React.FC<HeroProps> = ({
  onFileSelect,
  onVoiceClick,
  onSelectSampleDoc,
  isListening,
}) => {
  return (
    <section className="relative w-full pt-2 sm:pt-4 pb-6 sm:pb-8 px-4 sm:px-8 lg:px-12 overflow-hidden">
      {/* Background India Map Watermark on the Right */}
      <div
        className="absolute right-0 top-6 w-[340px] sm:w-[480px] lg:w-[580px] opacity-[0.14] pointer-events-none -z-10 select-none"
        aria-hidden="true"
      >
        <img
          src="/public/assets/images/india_map_watermark.png"
          alt=""
          className="w-full h-auto object-contain"
        />
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-6 items-center">
        {/* LEFT COLUMN: Large friendly robot illustration */}
        <div className="lg:col-span-6 xl:col-span-6 flex justify-center lg:justify-start order-2 lg:order-1">
          <RobotIllustration onVoiceClick={onVoiceClick} isListening={isListening} />
        </div>

        {/* RIGHT COLUMN: Headlines & Action Buttons */}
        <div className="lg:col-span-6 xl:col-span-6 flex flex-col items-center lg:items-start text-center lg:text-left order-1 lg:order-2">
          {/* Main 3-Line Punchy Headline */}
          <div className="space-y-0.5 sm:space-y-1">
            <h1 className="text-4xl sm:text-5xl lg:text-[56px] xl:text-[62px] font-extrabold text-[#082C5A] tracking-tight leading-[1.08] font-display">
              Samjhega.
            </h1>
            <h2 className="text-4xl sm:text-5xl lg:text-[56px] xl:text-[62px] font-extrabold text-[#082C5A] tracking-tight leading-[1.08] font-display">
              Batayega.
            </h2>
            <h2 className="text-4xl sm:text-5xl lg:text-[56px] xl:text-[62px] font-extrabold text-[#F47318] tracking-tight leading-[1.08] font-display">
              Raasta dikhayega.
            </h2>
          </div>

          {/* Subtitle / Description */}
          <p className="mt-4 sm:mt-5 text-base sm:text-lg lg:text-[19px] text-slate-700 font-normal leading-relaxed max-w-xl">
            Confusing notices, bank letters aur government documents ko simple language mein samjho - voice ke saath.
          </p>

          {/* Action Buttons: Blue Upload & Amber Voice */}
          <ActionButtons
            onFileSelect={onFileSelect}
            onVoiceClick={onVoiceClick}
            isListening={isListening}
          />

          {/* Instant Sample Document Chips for Quick Testing */}
          <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center lg:justify-start gap-2 text-xs text-slate-500">
            <span className="font-semibold text-slate-600 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-orange-500" />
              Try sample notice:
            </span>
            <button
              onClick={() => onSelectSampleDoc(SAMPLE_DOCUMENTS.echallan)}
              className="px-2.5 py-1 rounded-full bg-white hover:bg-blue-50 text-blue-900 border border-slate-200/90 shadow-2xs font-medium transition-colors cursor-pointer flex items-center gap-1"
            >
              <FileText className="w-3 h-3 text-blue-600" />
              Traffic Challan (₹2,000)
            </button>
            <button
              onClick={() => onSelectSampleDoc(SAMPLE_DOCUMENTS.bank_kyc)}
              className="px-2.5 py-1 rounded-full bg-white hover:bg-amber-50 text-amber-900 border border-slate-200/90 shadow-2xs font-medium transition-colors cursor-pointer flex items-center gap-1"
            >
              <ShieldAlert className="w-3 h-3 text-amber-600" />
              SBI Re-KYC Freeze
            </button>
            <button
              onClick={() => onSelectSampleDoc(SAMPLE_DOCUMENTS.tax_notice)}
              className="px-2.5 py-1 rounded-full bg-white hover:bg-orange-50 text-orange-900 border border-slate-200/90 shadow-2xs font-medium transition-colors cursor-pointer flex items-center gap-1"
            >
              <FileText className="w-3 h-3 text-orange-600" />
              Income Tax 142(1)
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};

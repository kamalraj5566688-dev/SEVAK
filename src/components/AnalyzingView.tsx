import React, { useEffect, useState } from 'react';
import { SupportedLanguage } from '../types';
import { Sparkles, CheckCircle2 } from 'lucide-react';

interface AnalyzingViewProps {
  fileName: string;
  fileSize?: string;
  language: SupportedLanguage;
  onAnalysisComplete: () => void;
}

const STEPS = [
  'Extracting text, stamp & authority seal from document...',
  'Analyzing legal sections, Acts and government clauses...',
  'Detecting deadlines, fines and mandatory obligations...',
  'Preparing simple language voice summary and 3 next steps...',
];

export const AnalyzingView: React.FC<AnalyzingViewProps> = ({
  fileName,
  fileSize,
  language,
  onAnalysisComplete,
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < STEPS.length - 1) {
          return prev + 1;
        }
        clearInterval(stepInterval);
        return prev;
      });
    }, 700);

    const completeTimeout = setTimeout(() => {
      onAnalysisComplete();
    }, 3200);

    return () => {
      clearInterval(stepInterval);
      clearTimeout(completeTimeout);
    };
  }, [onAnalysisComplete]);

  return (
    <div className="w-full max-w-3xl mx-auto px-4 py-12 sm:py-16 flex flex-col items-center text-center">
      {/* Animated Robot Composition Centerpiece */}
      <div className="relative mb-8 flex items-center justify-center">
        {/* Glowing Pulsing Ring */}
        <div className="absolute w-44 h-44 rounded-full bg-orange-400/20 blur-xl animate-pulse" />
        <div className="absolute w-36 h-36 rounded-full bg-blue-500/20 blur-lg animate-ping" />

        {/* Robot Avatar Mini Card */}
        <div className="relative z-10 w-28 h-28 sm:w-32 sm:h-32 rounded-3xl bg-white border-2 border-amber-300 shadow-xl p-3 flex flex-col items-center justify-center overflow-hidden">
          <img
            src="/public/assets/images/hero_robot_final.png"
            alt="SEVAK"
            className="w-full h-full object-contain scale-125 translate-x-3 -translate-y-1"
          />

          {/* Scanner laser beam scanning down */}
          <div
            className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_8px_#22d3ee] animate-bounce"
            style={{ animationDuration: '1.6s' }}
          />
        </div>
      </div>

      {/* Main Status Headings */}
      <div className="space-y-1.5 mb-6">
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[#082C5A] tracking-tight font-display">
          SEVAK is reading your document...
        </h2>
        <p className="text-lg sm:text-xl font-bold text-[#F47318] font-display">
          Samajh raha hai... Raasta dikhayega.
        </p>
        <div className="text-xs text-slate-500 font-medium">
          File: <span className="font-semibold text-slate-700">{fileName}</span>
          {fileSize && <span> ({fileSize})</span>} • Language: <span className="font-semibold capitalize text-blue-700">{language}</span>
        </div>
      </div>

      {/* Audio Waveform Animation */}
      <div className="flex items-center gap-1.5 mb-8 h-8">
        {[40, 75, 95, 60, 85, 100, 70, 50, 90, 65, 80, 45].map((height, i) => (
          <span
            key={i}
            className="w-1.5 bg-gradient-to-t from-[#0B57D0] to-cyan-400 rounded-full soundwave-bar"
            style={{
              animationDelay: `${i * 100}ms`,
              height: `${height * 0.3}px`,
            }}
          />
        ))}
      </div>

      {/* Step-by-Step Analysis Progress */}
      <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200/90 shadow-sm p-4 text-left space-y-3">
        {STEPS.map((step, idx) => {
          const isDone = idx < currentStepIndex;
          const isCurrent = idx === currentStepIndex;

          return (
            <div
              key={step}
              className={`flex items-start gap-3 transition-opacity duration-300 ${
                idx > currentStepIndex ? 'opacity-35' : 'opacity-100'
              }`}
            >
              <div className="shrink-0 mt-0.5">
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : isCurrent ? (
                  <Sparkles className="w-4 h-4 text-amber-500 animate-spin" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-slate-300" />
                )}
              </div>
              <span
                className={`text-xs ${
                  isCurrent
                    ? 'font-bold text-[#082C5A]'
                    : isDone
                    ? 'font-medium text-slate-700'
                    : 'text-slate-400'
                }`}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

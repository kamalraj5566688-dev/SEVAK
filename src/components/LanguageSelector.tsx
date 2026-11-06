import React from 'react';
import { SupportedLanguage } from '../types';

interface LanguageSelectorProps {
  selectedLanguage: SupportedLanguage;
  onSelectLanguage: (lang: SupportedLanguage) => void;
}

const LANGUAGES: { id: SupportedLanguage; label: string; native: string }[] = [
  { id: 'hinglish', label: 'Hinglish', native: 'Hinglish' },
  { id: 'hindi', label: 'Hindi', native: 'हिन्दी' },
  { id: 'english', label: 'English', native: 'English' },
  { id: 'bhojpuri', label: 'Bhojpuri', native: 'भोजपुरी' },
  { id: 'maithili', label: 'Maithili', native: 'मैथिली' },
];

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  selectedLanguage,
  onSelectLanguage,
}) => {
  return (
    <div className="w-full flex justify-center px-4 pt-1 pb-6">
      <div className="bg-white/95 backdrop-blur-xs rounded-full px-3.5 sm:px-6 py-2 sm:py-2.5 shadow-[0_2px_12px_rgba(0,0,0,0.06)] border border-slate-200/70 inline-flex flex-wrap items-center justify-center gap-2 sm:gap-3 transition-shadow hover:shadow-[0_4px_16px_rgba(0,0,0,0.08)]">
        <span className="text-xs sm:text-sm font-bold text-[#082C5A] tracking-tight whitespace-nowrap pl-1 pr-1 font-display">
          Talk to SEVAK in:
        </span>

        <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto py-0.5">
          {LANGUAGES.map((lang) => {
            const isSelected = selectedLanguage === lang.id;
            return (
              <button
                key={lang.id}
                onClick={() => onSelectLanguage(lang.id)}
                className={`px-3.5 sm:px-5 py-1 sm:py-1.5 rounded-full text-xs sm:text-sm font-medium transition-all duration-200 cursor-pointer select-none whitespace-nowrap active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                  isSelected
                    ? 'bg-[#0B57D0] text-white font-semibold shadow-xs shadow-blue-500/20'
                    : 'bg-transparent text-slate-700 hover:bg-slate-100/80 hover:text-slate-900'
                }`}
                aria-pressed={isSelected}
              >
                {lang.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Home, Upload, Globe, ChevronDown, Check } from 'lucide-react';
import { SupportedLanguage } from '../types';

interface NavbarProps {
  onGoHome: () => void;
  onOpenUpload: () => void;
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

export const Navbar: React.FC<NavbarProps> = ({
  onGoHome,
  onOpenUpload,
  selectedLanguage,
  onSelectLanguage,
}) => {
  const [langMenuOpen, setLangMenuOpen] = useState(false);

  return (
    <header className="relative z-30 w-full px-4 sm:px-8 lg:px-12 pt-4 pb-2">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        {/* Left: SEVAK Logo & Subtitle */}
        <button
          onClick={onGoHome}
          className="flex items-center text-left group focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 rounded-lg p-1 transition-transform active:scale-95"
          aria-label="SEVAK Home"
        >
          <div className="flex flex-col">
            <div className="flex items-baseline">
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#082C5A] font-display">
                SE
              </span>
              <span className="relative inline-block text-3xl sm:text-4xl font-extrabold font-display">
                <span className="text-[#F47318]">V</span>
              </span>
              <span className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#082C5A] font-display">
                AK
              </span>
            </div>
            <span className="text-[11px] sm:text-[13px] font-semibold text-[#082C5A] tracking-tight -mt-1 sm:-mt-1.5">
              Voice-First Indian Document Assistant
            </span>
          </div>
        </button>

        {/* Right Navigation */}
        <nav className="flex items-center gap-2 sm:gap-3" aria-label="Main Navigation">
          {/* Home Button - Dark Blue Pill */}
          <button
            onClick={onGoHome}
            className="flex items-center gap-2 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#0B57D0] hover:bg-[#0848af] text-white text-xs sm:text-sm font-semibold shadow-sm transition-all duration-150 active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-700"
            aria-label="Navigate to Home"
          >
            <Home className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" strokeWidth={2.5} />
            <span>Home</span>
          </button>

          {/* Upload Button - Light Rounded Pill */}
          <button
            onClick={onOpenUpload}
            className="flex items-center gap-2 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full bg-white/90 hover:bg-white text-[#082C5A] border border-slate-200/80 shadow-xs text-xs sm:text-sm font-medium transition-all duration-150 active:scale-95 hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            aria-label="Upload Document"
          >
            <Upload className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#082C5A]" strokeWidth={2.2} />
            <span>Upload</span>
          </button>

          {/* Language Dropdown Button */}
          <div className="relative">
            <button
              onClick={() => setLangMenuOpen(!langMenuOpen)}
              className="flex items-center gap-1.5 sm:gap-2 px-3.5 sm:px-4 py-2 sm:py-2.5 rounded-full bg-white/90 hover:bg-white text-[#082C5A] border border-slate-200/80 shadow-xs text-xs sm:text-sm font-medium transition-all duration-150 active:scale-95 hover:shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
              aria-expanded={langMenuOpen}
              aria-haspopup="true"
              aria-label="Select Language"
            >
              <Globe className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[#082C5A]" strokeWidth={2} />
              <span className="hidden xs:inline capitalize">{selectedLanguage}</span>
              <span className="xs:hidden">Lang</span>
              <ChevronDown
                className={`w-3.5 h-3.5 text-slate-500 transition-transform duration-200 ${
                  langMenuOpen ? 'rotate-180' : ''
                }`}
              />
            </button>

            {/* Dropdown Menu */}
            {langMenuOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setLangMenuOpen(false)}
                />
                <div className="absolute right-0 mt-2 w-48 bg-white rounded-2xl shadow-xl border border-slate-200/90 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
                  <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Select Language
                  </div>
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang.id}
                      onClick={() => {
                        onSelectLanguage(lang.id);
                        setLangMenuOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3.5 py-2 text-xs sm:text-sm transition-colors ${
                        selectedLanguage === lang.id
                          ? 'bg-blue-50 text-[#0B57D0] font-semibold'
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span>
                        {lang.label}{' '}
                        <span className="text-slate-400 text-xs font-normal">
                          ({lang.native})
                        </span>
                      </span>
                      {selectedLanguage === lang.id && (
                        <Check className="w-4 h-4 text-[#0B57D0]" />
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
};

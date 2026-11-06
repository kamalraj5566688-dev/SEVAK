import React from 'react';
import { Search, ArrowRight, ShieldCheck, FileText } from 'lucide-react';

export const HowSevakHelps: React.FC = () => {
  return (
    <div className="w-full bg-white/95 backdrop-blur-xs rounded-3xl border border-slate-200/90 shadow-[0_4px_24px_rgba(0,0,0,0.04)] px-6 sm:px-8 py-6 sm:py-7 flex flex-col justify-between transition-all duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
      {/* Section Header with Horizontal Dividers */}
      <div className="flex items-center justify-center gap-4 mb-6">
        <div className="h-[1.5px] flex-1 bg-gradient-to-r from-transparent via-[#0B57D0]/30 to-[#0B57D0]" />
        <h3 className="text-sm sm:text-base font-extrabold tracking-wider text-[#082C5A] uppercase font-display flex items-center gap-1.5 whitespace-nowrap">
          <span>HOW</span>
          <span className="text-[#0B57D0]">
            SE<span className="text-[#F47318]">V</span>AK
          </span>
          <span>HELPS</span>
        </h3>
        <div className="h-[1.5px] flex-1 bg-gradient-to-l from-transparent via-[#0B57D0]/30 to-[#0B57D0]" />
      </div>

      {/* 4 Cards Grid with Clean Dividers */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-0 divide-y md:divide-y-0 md:divide-x divide-slate-100">
        {/* Card 01: WHAT */}
        <div className="flex flex-col items-center text-center p-3 sm:p-4 group">
          <div className="relative mb-3 flex items-center justify-center">
            {/* Subtle glow */}
            <div className="absolute inset-0 bg-blue-400/20 rounded-full blur-md group-hover:scale-125 transition-transform" />
            <div className="relative w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center text-[#0B57D0] shadow-2xs">
              <div className="relative">
                <FileText className="w-7 h-7 text-[#0B57D0]" strokeWidth={2.2} />
                <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-[#0B57D0] flex items-center justify-center text-white text-[9px] shadow-xs">
                  <Search className="w-2.5 h-2.5 text-white" strokeWidth={3} />
                </span>
              </div>
            </div>
          </div>
          <span className="text-sm sm:text-[15px] font-extrabold text-[#082C5A] tracking-wider uppercase font-display">
            WHAT
          </span>
          <p className="mt-1 text-xs sm:text-[13px] text-slate-600 leading-snug max-w-[130px]">
            Document actually kya keh raha hai.
          </p>
        </div>

        {/* Card 02: WHY */}
        <div className="flex flex-col items-center text-center p-3 sm:p-4 pt-4 md:pt-4 group">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute inset-0 bg-amber-400/20 rounded-full blur-md group-hover:scale-125 transition-transform" />
            <div className="relative w-12 h-12 rounded-full bg-[#F47318] flex items-center justify-center text-white shadow-2xs">
              <span className="text-2xl font-bold font-display leading-none">?</span>
            </div>
          </div>
          <span className="text-sm sm:text-[15px] font-extrabold text-[#082C5A] tracking-wider uppercase font-display">
            WHY
          </span>
          <p className="mt-1 text-xs sm:text-[13px] text-slate-600 leading-snug max-w-[130px]">
            Ye notice important kyun hai.
          </p>
        </div>

        {/* Card 03: NEXT */}
        <div className="flex flex-col items-center text-center p-3 sm:p-4 pt-4 md:pt-4 group">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute inset-0 bg-emerald-400/20 rounded-full blur-md group-hover:scale-125 transition-transform" />
            <div className="relative w-12 h-12 rounded-full bg-[#16A34A] flex items-center justify-center text-white shadow-2xs">
              <ArrowRight className="w-6 h-6 text-white" strokeWidth={2.6} />
            </div>
          </div>
          <span className="text-sm sm:text-[15px] font-extrabold text-[#082C5A] tracking-wider uppercase font-display">
            NEXT
          </span>
          <p className="mt-1 text-xs sm:text-[13px] text-slate-600 leading-snug max-w-[130px]">
            Exactly 3 practical next steps.
          </p>
        </div>

        {/* Card 04: SOURCE */}
        <div className="flex flex-col items-center text-center p-3 sm:p-4 pt-4 md:pt-4 group">
          <div className="relative mb-3 flex items-center justify-center">
            <div className="absolute inset-0 bg-blue-900/20 rounded-full blur-md group-hover:scale-125 transition-transform" />
            <div className="relative w-12 h-12 rounded-2xl bg-[#082C5A] flex items-center justify-center text-white shadow-2xs">
              <ShieldCheck className="w-6 h-6 text-white" strokeWidth={2.4} />
            </div>
          </div>
          <span className="text-sm sm:text-[15px] font-extrabold text-[#082C5A] tracking-wider uppercase font-display">
            SOURCE
          </span>
          <p className="mt-1 text-xs sm:text-[13px] text-slate-600 leading-snug max-w-[130px]">
            Important information kahan se aayi.
          </p>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { Shield, Check } from 'lucide-react';

export const SafetyCard: React.FC = () => {
  return (
    <div className="relative w-full h-full bg-white/95 backdrop-blur-xs rounded-3xl border border-slate-200/90 shadow-[0_4px_24px_rgba(0,0,0,0.04)] px-6 sm:px-7 py-6 sm:py-7 flex flex-col justify-between overflow-hidden transition-all duration-200 hover:shadow-[0_8px_30px_rgba(0,0,0,0.06)]">
      {/* Top Section with Green Shield & Content */}
      <div className="flex items-start gap-4 z-10">
        {/* Green Shield Icon with Checkmark */}
        <div className="relative w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-[#16A34A] flex items-center justify-center shrink-0 shadow-md shadow-emerald-600/20">
          <Shield className="w-8 h-8 sm:w-9 sm:h-9 text-white" fill="white" fillOpacity={0.15} strokeWidth={2.4} />
          <Check className="absolute w-5 h-5 sm:w-6 sm:h-6 text-white" strokeWidth={3} />
        </div>

        {/* Text Details */}
        <div className="flex flex-col pr-12 sm:pr-14">
          <span className="text-xs sm:text-[13px] font-extrabold text-[#16A34A] tracking-wider uppercase font-display">
            SAFETY FIRST
          </span>
          <h4 className="mt-1 text-base sm:text-lg font-bold text-[#082C5A] leading-snug font-display">
            Information, not false certainty.
          </h4>
          <p className="mt-1.5 text-xs sm:text-[13px] text-slate-600 leading-relaxed">
            SEVAK documents ko explain karta hai, legal guarantee nahi deta.
          </p>
        </div>
      </div>

      {/* Bottom Right Corner: Indian Tricolor Swirl Accent from Reference */}
      <div
        className="absolute -bottom-2 -right-2 w-32 sm:w-36 h-32 sm:h-36 pointer-events-none select-none z-0 opacity-95"
        aria-hidden="true"
      >
        <img
          src="/public/assets/images/tricolor_accent.png"
          alt=""
          className="w-full h-full object-contain object-bottom-right"
        />
      </div>
    </div>
  );
};

import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="relative w-full mt-10 sm:mt-14 z-20">
      {/* Heritage Monuments Skyline Silhouette along the horizon */}
      <div className="relative w-full h-10 sm:h-14 overflow-hidden pointer-events-none select-none -mb-1">
        <img
          src="/assets/images/heritage_silhouette.png"
          alt=""
          className="w-full h-full object-cover object-bottom opacity-85 max-w-full h-auto"
          loading="lazy"
          decoding="async"
        />
      </div>

      {/* Main Navy Footer Bar with Subtle Top Wave Curve */}
      <div className="relative bg-[#04295A] text-white px-4 sm:px-8 lg:px-12 py-4 sm:py-5 border-t border-[#0d3b75]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3 text-center md:text-left">
          {/* Left Brand & Motto */}
          <div className="flex flex-wrap items-center justify-center md:justify-start gap-2 sm:gap-2.5 text-xs sm:text-sm font-medium">
            <span className="font-extrabold tracking-tight text-white font-display text-sm sm:text-base">
              SE<span className="text-[#F47318]">V</span>AK
            </span>
            <span className="text-blue-300/60 font-light" aria-hidden="true">
              |
            </span>
            <span className="text-slate-200">
              Samjhega. Batayega. Raasta dikhayega.
            </span>
          </div>

          {/* Right Attribution & Challenge Badge */}
          <div className="text-xs sm:text-[13px] text-blue-200/90 font-medium flex items-center justify-center gap-1.5 flex-wrap">
            <span>Powered by <strong className="text-white font-semibold">Gnani AI</strong></span>
            <span>•</span>
            <span>Great Indian AI Internship Challenge</span>
            <span role="img" aria-label="Indian Flag" className="text-sm">🇮🇳</span>
            <a
              href="/privacy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-300/80 hover:text-white underline underline-offset-2"
            >
              Privacy
            </a>
            <a
              href="/terms.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-300/80 hover:text-white underline underline-offset-2"
            >
              Terms
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

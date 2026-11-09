import React, { useEffect, useState } from 'react';

const CONSENT_KEY = 'sevak_cookie_consent';

interface CookieConsentProps {
  onAccept?: () => void;
}

export const CookieConsent: React.FC<CookieConsentProps> = ({ onAccept }) => {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Only show banner when consent has not been recorded.
    try {
      const stored = localStorage.getItem(CONSENT_KEY);
      setShow(stored !== 'accepted');
    } catch {
      setShow(false);
    }
  }, []);

  const accept = () => {
    try {
      localStorage.setItem(CONSENT_KEY, 'accepted');
    } catch {
      /* storage unavailable — proceed anyway */
    }
    setShow(false);
    onAccept?.();
  };

  if (!show) return null;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between px-4 sm:px-6 lg:px-8 py-4 sm:py-5 bg-white border-t border-slate-200 shadow-2xl bg-opacity-97 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Cookie consent"
    >
      <div className="flex items-start gap-3 text-sm sm:text-base text-slate-700 leading-relaxed">
        <span className="flex-shrink-0 mt-0.5">🍪</span>
        <div>
          <p className="font-semibold text-slate-900 mb-1">
            SEVAK uses cookies to remember your preferences and improve your experience.
          </p>
          <p className="text-slate-500 text-xs sm:text-sm">
            No tracking or advertising cookies are set by default. Learn more in our{' '}
            <a
              href="/privacy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#0B57D0] underline font-medium"
            >
              Privacy Policy
            </a>
            .
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <button
          onClick={accept}
          className="px-5 sm:px-7 py-2 sm:py-2.5 rounded-full bg-[#0B57D0] text-white text-sm sm:text-base font-semibold shadow-sm hover:bg-[#0848af] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        >
          I Accept
        </button>
        <button
          onClick={accept}
          className="px-4 sm:px-6 py-2 sm:py-2.5 rounded-full border border-slate-300 bg-transparent text-slate-700 text-sm sm:text-base font-medium hover:bg-slate-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          Close
        </button>
      </div>
    </div>
  );
};

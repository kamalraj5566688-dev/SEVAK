import React, { useState, useEffect, useRef } from 'react';
import {
  SevakAnalysisResult,
  SupportedLanguage,
} from '../types';
import {
  Volume2,
  VolumeX,
  Calendar,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Scale,
  RotateCcw,
  Sparkles,
  ExternalLink,
  Mic,
  Send,
  HelpCircle,
  FileText,
  Clock,
  Printer,
} from 'lucide-react';
import { SevakApiService } from '../services/api';

const decodeHtmlEntities = (value: unknown): string => {
  if (value === null || value === undefined) return '';

  let text = String(value);

  // Decode repeatedly because the backend can return
  // single- or double-encoded HTML entities.
  for (let i = 0; i < 3; i += 1) {
    const before = text;

    // Hexadecimal entities: &#x50; -> P
    text = text.replace(
      /&#x([0-9a-f]+);/gi,
      (_, hex) => String.fromCodePoint(parseInt(hex, 16))
    );

    // Decimal entities: &#80; -> P
    text = text.replace(
      /&#([0-9]+);/g,
      (_, dec) => String.fromCodePoint(parseInt(dec, 10))
    );

    // Common named entity needed for double encoding:
    // &amp;#x50; -> &#x50;
    text = text
      .replace(/&amp;/gi, '&')
      .replace(/&quot;/gi, '"')
      .replace(/&apos;/gi, "'")
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>');

    if (text === before) break;
  }

  return text;
};
interface ResultsViewProps {
  result: SevakAnalysisResult;
  selectedLanguage: SupportedLanguage;
  onSelectLanguage: (lang: SupportedLanguage) => void;
  onReset: () => void;
  onOpenVoiceModal: () => void;
}

export const ResultsView: React.FC<ResultsViewProps> = ({
  result,
  selectedLanguage,
  onSelectLanguage,
  onReset,
  onOpenVoiceModal,
}) => {
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [questionInput, setQuestionInput] = useState('');
  const [chatMessages, setChatMessages] = useState<
    { role: 'user' | 'sevak'; text: string }[]
  >([]);
  const [isAsking, setIsAsking] = useState(false);
  const [askError, setAskError] = useState('');

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const honeypotRef = useRef<HTMLInputElement>(null);

  // Stop any audio when unmounting
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const playBrowserSpeech = () => {
    if (!('speechSynthesis' in window)) {
      alert('Speech synthesis is not supported on this device/browser.');
      return;
    }

    const textToSpeak =
      result.voiceSummaries[selectedLanguage] ||
      result.what.summary + '. ' + result.why.significance;

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    if (selectedLanguage === 'hindi') {
      utterance.lang = 'hi-IN';
    } else {
      utterance.lang = 'en-IN';
    }
    utterance.rate = 0.95;

    utterance.onstart = () => setIsPlayingAudio(true);
    utterance.onend = () => setIsPlayingAudio(false);
    utterance.onerror = () => setIsPlayingAudio(false);

    window.speechSynthesis.speak(utterance);
  };

  const handleToggleVoice = () => {
    if (isPlayingAudio) {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingAudio(false);
      return;
    }

    // 1. Prefer real Gnani Timbre neural audio if available
    if (result.audioBase64) {
      try {
        if (!audioRef.current) {
          audioRef.current = new Audio();
        }
        audioRef.current.src = `data:audio/wav;base64,${result.audioBase64}`;
        audioRef.current.onplay = () => setIsPlayingAudio(true);
        audioRef.current.onended = () => setIsPlayingAudio(false);
        audioRef.current.onerror = () => {
          setIsPlayingAudio(false);
          playBrowserSpeech();
        };
        audioRef.current.play();
        return;
      } catch (err) {
        console.warn('Direct Timbre playback failed, falling back to speech synthesis:', err);
      }
    }

    // 2. Fall back to browser Web Speech API
    playBrowserSpeech();
  };

  const handleAskQuestion = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAskError('');

    // Spam / bot protection: honeypot field left blank by humans.
    // Bots often auto-fill hidden fields; if it has a value, drop the submission.
    if (honeypotRef.current && honeypotRef.current.value.trim()) {
      setAskError('');
      return;
    }

    if (!questionInput.trim() || isAsking) return;
    if (questionInput.trim().length < 2) {
      setAskError('Kripya thoda vistar se sawal likhein.');
      return;
    }

    const query = questionInput.trim();
    setChatMessages((prev) => [...prev, { role: 'user', text: query }]);
    setQuestionInput('');
    setIsAsking(true);

    try {
      const answer = await SevakApiService.askQuestion({
        question: query,
        documentId: result.id,
        language: selectedLanguage,
      });
      setChatMessages((prev) => [...prev, { role: 'sevak', text: answer }]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'sevak',
          text: 'Notice ke official portal par jakar exact status verify kar sakte hain.',
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      {/* Top Banner & Navigation Back */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white hover:bg-slate-100 text-[#082C5A] border border-slate-200 text-xs sm:text-sm font-semibold transition-colors cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Naya Document / Back to Home</span>
        </button>

        {/* Live Audio Readout Button */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleToggleVoice}
            className={`flex items-center gap-2 px-4 py-2 rounded-full font-bold text-xs sm:text-sm transition-all shadow-sm cursor-pointer ${
              isPlayingAudio
                ? 'bg-orange-500 text-white animate-pulse'
                : 'bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600'
            }`}
            aria-label="Bolke sunayein"
          >
            {isPlayingAudio ? (
              <>
                <VolumeX className="w-4 h-4" />
                <span>Rukiye (Stop Audio)</span>
              </>
            ) : (
              <>
                <Volume2 className="w-4 h-4" />
                <span>Bolke Sunayein (Voice Summary)</span>
              </>
            )}
          </button>

          <button
            onClick={() => window.print()}
            className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-full bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold"
            title="Print Summary"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print</span>
          </button>
        </div>
      </div>

      {/* Main Document Identification Card */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-md p-6 sm:p-8 mb-6 relative overflow-hidden">
        {/* Saffron & Green Accent Lines */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-[#F47318] via-white to-[#16A34A]" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800">
                {result.category}
              </span>
              {result.isDemoFallback && !result.originalFileName && (
                <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200">
                  Demo Analysis Mode
                </span>
              )}
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#082C5A] tracking-tight font-display">
              {result.documentTitle}
            </h1>

            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span>File: {result.originalFileName}</span>
              <span>•</span>
              <span>Size: {result.fileSize}</span>
              <span>•</span>
              <span>Confidence: {(result.confidenceScore > 1 ? result.confidenceScore : Math.round(result.confidenceScore * 100))}%</span>
            </div>
          </div>

          {/* Deadline Callout Pill if Detected */}
          {result.deadline.hasDeadline && (
            <div className="shrink-0 bg-red-50/90 border-2 border-red-200 rounded-2xl p-3.5 sm:p-4 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500 text-white flex items-center justify-center shrink-0 shadow-sm">
                <Clock className="w-5 h-5" />
              </div>
              <div className="text-left">
                <span className="text-[11px] font-extrabold text-red-700 uppercase tracking-wider block">
                  IMPORTANT DEADLINE
                </span>
                <span className="text-sm sm:text-base font-extrabold text-slate-900 font-display">
                  {result.deadline.date}
                </span>
                {result.deadline.daysRemaining !== undefined && (
                  <span className="text-xs text-red-700 block font-semibold">
                    ({result.deadline.daysRemaining} days remaining)
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Dynamic Language Switcher Bar inside Results */}
        <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
            <span>Translate this explanation:</span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {(['hinglish', 'hindi', 'english', 'bhojpuri', 'maithili'] as SupportedLanguage[]).map(
              (lang) => (
                <button
                  key={lang}
                  onClick={() => onSelectLanguage(lang)}
                  className={`px-3 py-1 rounded-full text-xs font-semibold capitalize transition-colors ${
                    selectedLanguage === lang
                      ? 'bg-[#0B57D0] text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }`}
                >
                  {lang}
                </button>
              )
            )}
          </div>
        </div>
      </div>

      {/* CORE 6-SECTION SEVAK BREAKDOWN */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        {/* 1. WHAT — What does this document actually say? */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-3 text-[#0B57D0]">
              <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                <FileText className="w-5 h-5" />
              </div>
              <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
                WHAT — Document actually kya keh raha hai
              </h2>
            </div>
            <p className="text-base sm:text-lg font-bold text-slate-900 leading-snug font-display mb-2">
              {result.what.summary}
            </p>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {result.what.details}
            </p>
          </div>
        </div>

        {/* 2. WHY — Why is this important? */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-3 text-[#F47318]">
              <div className="w-8 h-8 rounded-xl bg-amber-50 flex items-center justify-center">
                <AlertTriangle className="w-5 h-5 text-[#F47318]" />
              </div>
              <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
                WHY — Ye notice important kyun hai
              </h2>
            </div>
            <p className="text-base sm:text-lg font-bold text-slate-900 leading-snug font-display mb-2">
              {result.why.significance}
            </p>
            <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
              {result.why.urgencyReason}
            </p>
          </div>
        </div>

        {/* 3. NEXT — Exactly 3 Practical Next Steps (Full Width) */}
        <div className="md:col-span-12 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-7">
          <div className="flex items-center gap-2.5 mb-5 text-[#16A34A]">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
              <ArrowRight className="w-5 h-5 text-[#16A34A]" />
            </div>
            <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
              NEXT — Exactly 3 Practical Next Steps
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {result.nextSteps.map((item) => (
              <div
                key={item.step}
                className="bg-slate-50/80 rounded-2xl p-4 border border-slate-200 flex flex-col justify-between relative group hover:bg-emerald-50/40 hover:border-emerald-200 transition-colors"
              >
                <div>
                  <div className="w-7 h-7 rounded-full bg-[#16A34A] text-white flex items-center justify-center text-xs font-bold mb-2.5">
                    0{item.step}
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 mb-1.5 font-display">
                    {item.title}
                  </h4>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {item.description}
                  </p>
                </div>

                {item.actionUrl && (
                  <a
                    href={item.actionUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#0B57D0] hover:underline"
                  >
                    <span>Official portal link</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 4. RIGHTS — What relevant rights/information should the user know? */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6">
          <div className="flex items-center gap-2.5 mb-3 text-emerald-700">
            <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center">
              <Scale className="w-5 h-5 text-emerald-700" />
            </div>
            <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
              RIGHTS — Citizen Protections & Rights
            </h2>
          </div>

          <ul className="space-y-2.5 mb-4">
            {result.rights.safeguards.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs sm:text-sm text-slate-700">
                <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div className="p-3 bg-amber-50/80 rounded-xl border border-amber-200/70 text-[11px] text-amber-900 leading-tight">
            <strong>Advisory Note:</strong> {result.rights.disclaimer}
          </div>
        </div>

        {/* 5. SOURCE & DEADLINE DETAIL */}
        <div className="md:col-span-6 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-3 text-[#082C5A]">
              <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-[#082C5A]" />
              </div>
              <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
                SOURCE — Issuing Authority & Legal Basis
              </h2>
            </div>

            <div className="space-y-2.5 text-xs text-slate-700">
              <div>
                <span className="font-semibold text-slate-500 block">Authority:</span>
                <span className="text-slate-900 font-bold">{result.source.issuingAuthority}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-500 block">Legal Section:</span>
                <span className="text-blue-900 font-medium">{result.source.legalSection}</span>
              </div>
              <div>
                <span className="font-semibold text-slate-500 block">Reference No:</span>
                <span className="font-mono text-slate-800">{decodeHtmlEntities(result.source.referenceNumber)}</span>
              </div>
            </div>
          </div>

          {result.source.officialPortalUrl && (
            <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
              <span className="text-xs text-slate-500">Official Portal:</span>
              <a
                href={result.source.officialPortalUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-semibold text-[#0B57D0] hover:underline flex items-center gap-1"
              >
                <span>Visit Official Site</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
        </div>

        {/* 6. CITATIONS — Show Me Where Grounding */}
        {result.citations && result.citations.length > 0 && (
          <div className="md:col-span-12 bg-white rounded-3xl border border-slate-200/90 shadow-sm p-6 sm:p-7">
            <div className="flex items-center gap-2.5 mb-4 text-[#0B57D0]">
              <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center">
                <FileText className="w-5 h-5 text-[#0B57D0]" />
              </div>
              <div>
                <h2 className="text-sm font-extrabold tracking-wider uppercase font-display text-[#082C5A]">
                  SHOW ME WHERE — Verified Document Grounding
                </h2>
                <span className="text-[11px] text-slate-500 font-medium">
                  Every claim is mapped to the exact page and paragraph in your notice
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {result.citations.map((cite, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between"
                >
                  <p className="text-xs sm:text-sm font-medium text-slate-800 mb-2.5">
                    "{cite.claim}"
                  </p>
                  <div className="inline-flex items-center gap-1.5 text-[11px] font-bold text-[#0B57D0] bg-blue-50 px-2.5 py-1 rounded-full w-fit">
                    <ExternalLink className="w-3 h-3" />
                    <span>Verified Source: {cite.sourceLocation}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Interactive Follow-up Question Bar with SEVAK */}
      <div className="mt-8 bg-white rounded-3xl border border-slate-200/90 shadow-md p-6 sm:p-7">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-[#F47318]" />
            <h3 className="text-base font-bold text-[#082C5A] font-display">
              Have questions about this notice? Ask SEVAK
            </h3>
          </div>
          <button
            onClick={onOpenVoiceModal}
            className="flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 px-3 py-1.5 rounded-full border border-amber-200 cursor-pointer"
          >
            <Mic className="w-3.5 h-3.5 text-amber-800" />
            <span>Voice Mode</span>
          </button>
        </div>

        {/* Chat History if any */}
        {chatMessages.length > 0 && (
          <div className="mb-4 space-y-2.5 max-h-48 overflow-y-auto pr-1">
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`p-3 rounded-2xl text-xs sm:text-sm ${
                  msg.role === 'user'
                    ? 'bg-blue-50 text-blue-900 ml-8'
                    : 'bg-amber-50/80 text-amber-950 mr-8 border border-amber-200/60'
                }`}
              >
                <span className="font-bold block text-[11px] opacity-75 mb-0.5">
                  {msg.role === 'user' ? 'You' : 'SEVAK'}:
                </span>
                {msg.text}
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleAskQuestion} className="flex items-center gap-2">
          {/* Honeypot: invisible to humans, a spam-signal for bots. */}
          <input
            ref={honeypotRef}
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            className="sr-only"
          />
          <label className="sr-only">
            If you are human, leave this field blank.
          </label>
          <input
            type="text"
            value={questionInput}
            onChange={(e) => setQuestionInput(e.target.value)}
            placeholder="e.g. Kya mujhe fine bharna padega? Ya deadline extend ho sakti hai?"
            className="flex-1 px-4 py-2.5 rounded-full bg-slate-50 border border-slate-200 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {askError && (
            <span className="text-xs text-red-600 font-medium whitespace-nowrap">
              {askError}
            </span>
          )}
          <button
            type="submit"
            disabled={isAsking || !questionInput.trim()}
            className="px-5 py-2.5 rounded-full bg-[#0B57D0] hover:bg-[#0848af] text-white text-xs sm:text-sm font-semibold transition-colors disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
          >
            <span>Ask</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
    </div>
  );
};







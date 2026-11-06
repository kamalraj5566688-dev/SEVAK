import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, X, Volume2, Sparkles, AlertCircle, ArrowRight } from 'lucide-react';
import { SupportedLanguage } from '../types';
import { SevakApiService } from '../services/api';

interface VoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedLanguage: SupportedLanguage;
  onDocumentAnalyzeRequested?: () => void;
  currentDocumentId?: string;
}

export const VoiceModal: React.FC<VoiceModalProps> = ({
  isOpen,
  onClose,
  selectedLanguage,
  onDocumentAnalyzeRequested,
  currentDocumentId,
}) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [sevakAnswer, setSevakAnswer] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (!isOpen) {
      stopListening();
      setTranscript('');
      setSevakAnswer(null);
      setErrorMessage(null);
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      return;
    }

    startListening();

    return () => {
      stopListening();
      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isOpen, selectedLanguage]);

  const startListening = () => {
    setErrorMessage(null);
    setSevakAnswer(null);

    // Check Web Speech API support
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setErrorMessage(
        'Speech recognition is not supported in this browser. You can still type your question below!'
      );
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;

      // Select speech recognition language
      if (selectedLanguage === 'hindi' || selectedLanguage === 'bhojpuri' || selectedLanguage === 'maithili') {
        recognition.lang = 'hi-IN';
      } else if (selectedLanguage === 'english') {
        recognition.lang = 'en-IN';
      } else {
        recognition.lang = 'hi-IN'; // Hinglish
      }

      recognition.onstart = () => {
        setIsListening(true);
        setErrorMessage(null);
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        let current = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          current += event.results[i][0].transcript;
        }
        setTranscript(current);
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = (event: any) => {
        console.warn('Speech recognition error:', event.error);
        if (event.error === 'not-allowed') {
          setErrorMessage('Microphone access was denied. Please allow microphone permission to talk with SEVAK.');
        } else if (event.error === 'no-speech') {
          setErrorMessage('Koi aawaz nahi sunai di. Please dubara boleiye.');
        } else {
          setErrorMessage(`Audio capture error: ${event.error}. You can type your question below.`);
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
        if (transcript.trim().length > 2) {
          handleProcessQuestion(transcript);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Failed to start speech recognition:', err);
      setErrorMessage('Could not initiate microphone. You can type your query below.');
      setIsListening(false);
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  const handleProcessQuestion = async (text: string) => {
    if (!text.trim()) return;
    setIsProcessing(true);
    try {
      const answer = await SevakApiService.askQuestion({
        question: text,
        documentId: currentDocumentId,
        language: selectedLanguage,
      });
      setSevakAnswer(answer);
      speakAnswer(answer);
    } catch {
      setSevakAnswer('SEVAK samajh raha hai. Kripya apna document upload karein taaki hum exact sections explain kar sakein.');
    } finally {
      setIsProcessing(false);
    }
  };

  const speakAnswer = (text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    if (selectedLanguage === 'hindi') {
      utterance.lang = 'hi-IN';
    } else {
      utterance.lang = 'en-IN';
    }
    utterance.rate = 0.95;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const handleQuickQuestion = (q: string) => {
    setTranscript(q);
    handleProcessQuestion(q);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-[#FAF7F0] rounded-3xl border border-slate-200 shadow-2xl p-6 sm:p-7 overflow-hidden">
        {/* Background gradient decorative glow */}
        <div className="absolute -top-16 -right-16 w-44 h-44 rounded-full bg-orange-300/30 blur-2xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-44 h-44 rounded-full bg-blue-300/30 blur-2xl pointer-events-none" />

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 transition-colors focus:outline-none"
          aria-label="Close voice modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-800">
            <Mic className="w-5 h-5 text-[#853509]" strokeWidth={2.4} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[#082C5A] font-display">
              Talk to SEVAK
            </h3>
            <p className="text-xs text-slate-600">
              Voice-First Indian Document Assistant ({selectedLanguage.toUpperCase()})
            </p>
          </div>
        </div>

        {/* Main Listening Orb / Visualizer */}
        <div className="my-6 flex flex-col items-center justify-center">
          <div className="relative flex items-center justify-center">
            {/* Animated Pulsing Rings */}
            {isListening && (
              <>
                <div className="absolute w-28 h-28 rounded-full bg-amber-400/25 animate-ping" />
                <div className="absolute w-24 h-24 rounded-full bg-orange-400/30 animate-pulse" />
              </>
            )}

            <button
              onClick={isListening ? stopListening : startListening}
              className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg cursor-pointer focus:outline-none focus-visible:ring-4 focus-visible:ring-amber-400 ${
                isListening
                  ? 'bg-gradient-to-tr from-amber-500 to-orange-500 text-white scale-110 shadow-orange-500/40'
                  : 'bg-white text-slate-700 border-2 border-slate-200 hover:border-amber-400'
              }`}
              aria-label={isListening ? 'Stop listening' : 'Start listening'}
            >
              {isListening ? (
                <Mic className="w-9 h-9 animate-pulse" />
              ) : (
                <MicOff className="w-8 h-8 text-slate-400" />
              )}
            </button>
          </div>

          {/* Equalizer Bars when listening */}
          {isListening && (
            <div className="flex items-center gap-1.5 mt-4 h-8">
              <span className="w-1.5 bg-amber-500 rounded-full soundwave-bar" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 bg-orange-500 rounded-full soundwave-bar" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 bg-blue-600 rounded-full soundwave-bar" style={{ animationDelay: '300ms' }} />
              <span className="w-1.5 bg-amber-500 rounded-full soundwave-bar" style={{ animationDelay: '200ms' }} />
              <span className="w-1.5 bg-emerald-600 rounded-full soundwave-bar" style={{ animationDelay: '400ms' }} />
            </div>
          )}

          <span className="mt-3 text-xs font-semibold text-slate-600">
            {isListening
              ? 'SEVAK sun raha hai... Bolo aap kya jaanna chahte hain'
              : 'Mic icon par tap karke bolein'}
          </span>
        </div>

        {/* Captured Transcript Box */}
        {transcript && (
          <div className="mb-4 p-3.5 bg-white rounded-2xl border border-slate-200/90 shadow-2xs">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
              You said:
            </span>
            <p className="text-sm text-slate-800 font-medium italic">
              "{transcript}"
            </p>
          </div>
        )}

        {/* SEVAK Answer Display */}
        {isProcessing && (
          <div className="p-4 bg-blue-50/80 rounded-2xl border border-blue-200/60 flex items-center gap-3">
            <Sparkles className="w-5 h-5 text-blue-600 animate-spin" />
            <span className="text-xs font-semibold text-blue-900">
              SEVAK samajh raha hai... Raasta dhundh raha hai...
            </span>
          </div>
        )}

        {sevakAnswer && !isProcessing && (
          <div className="p-4 bg-white rounded-2xl border-2 border-amber-300 shadow-sm animate-in fade-in duration-200">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-[#082C5A] uppercase tracking-wider flex items-center gap-1 font-display">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                SEVAK ka jawab:
              </span>
              <button
                onClick={() => speakAnswer(sevakAnswer)}
                className={`p-1 rounded-md text-slate-600 hover:text-amber-700 transition-colors ${
                  isSpeaking ? 'text-amber-600 animate-pulse' : ''
                }`}
                title="Speak answer again"
              >
                <Volume2 className="w-4 h-4" />
              </button>
            </div>
            <p className="text-sm text-slate-800 leading-relaxed font-medium">
              {sevakAnswer}
            </p>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div className="my-3 p-3 bg-red-50 rounded-xl border border-red-200/80 flex items-start gap-2.5 text-xs text-red-800">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <p>{errorMessage}</p>
          </div>
        )}

        {/* Quick Suggestion Prompts */}
        <div className="mt-5 pt-4 border-t border-slate-200/80">
          <span className="text-[11px] font-semibold text-slate-500 block mb-2">
            Ya yeh puchhein:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {[
              'Mujhe ye document samjhao',
              'Is notice ka last date kab hai?',
              'Kya mujhe court jana hoga?',
              'Mujhe kitne paise bharne honge?',
            ].map((q) => (
              <button
                key={q}
                onClick={() => handleQuickQuestion(q)}
                className="text-xs bg-white hover:bg-amber-50 text-slate-700 hover:text-amber-900 px-3 py-1.5 rounded-full border border-slate-200 transition-colors cursor-pointer text-left"
              >
                "{q}"
              </button>
            ))}
          </div>
        </div>

        {/* If user needs to analyze document */}
        {onDocumentAnalyzeRequested && (
          <div className="mt-4 pt-3 flex justify-end">
            <button
              onClick={() => {
                onClose();
                onDocumentAnalyzeRequested();
              }}
              className="text-xs text-[#0B57D0] hover:underline font-semibold flex items-center gap-1"
            >
              Document upload karke full analysis dekhein
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

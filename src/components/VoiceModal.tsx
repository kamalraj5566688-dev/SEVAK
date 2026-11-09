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

  // MediaRecorder refs for backend Prisma STT
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mediaRecorderRef = useRef<any>(null);
  const voiceSessionRef = useRef(false);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mediaStreamRef = useRef<any>(null);
  const audioChunksRef = useRef<Blob[]>([]);
const audioContextRef = useRef<any>(null);
  const vadIntervalRef = useRef<number | null>(null);
  const silenceStartedAtRef = useRef<number | null>(null);
  const speechDetectedRef = useRef(false);

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

    return () => {
      stopListening();

      if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isOpen, selectedLanguage]);

  const cleanupMediaStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track: MediaStreamTrack) => {
        track.stop();
      });

      mediaStreamRef.current = null;
    }

    mediaRecorderRef.current = null;
  };

  const convertAudioBlobToWav = async (audioBlob: Blob): Promise<Blob> => {
    const AudioContextClass =
      window.AudioContext ||
      (window as typeof window & {
        webkitAudioContext?: typeof AudioContext;
      }).webkitAudioContext;

    if (!AudioContextClass) {
      throw new Error('Web Audio API is not supported in this browser.');
    }

    const audioContext = new AudioContextClass();

    try {
      const arrayBuffer = await audioBlob.arrayBuffer();
      const decodedBuffer = await audioContext.decodeAudioData(arrayBuffer);

      const targetSampleRate = 16000;
      const targetChannels = 1;

      const sourceLength = decodedBuffer.length;

      const targetLength = Math.max(
        1,
        Math.round(
          sourceLength *
          targetSampleRate /
          decodedBuffer.sampleRate
        )
      );

      const monoSamples = new Float32Array(targetLength);

      const channelCount = decodedBuffer.numberOfChannels;

      for (let i = 0; i < targetLength; i++) {
        const sourcePosition =
          i * decodedBuffer.sampleRate / targetSampleRate;

        const sourceIndex = Math.floor(sourcePosition);
        const nextIndex = Math.min(
          sourceIndex + 1,
          sourceLength - 1
        );

        const interpolation =
          sourcePosition - sourceIndex;

        let sample = 0;

        for (let channel = 0; channel < channelCount; channel++) {
          const channelData =
            decodedBuffer.getChannelData(channel);

          const current =
            channelData[sourceIndex] || 0;

          const next =
            channelData[nextIndex] || 0;

          sample +=
            current +
            (next - current) * interpolation;
        }

        monoSamples[i] =
          sample / channelCount;
      }

      const bytesPerSample = 2;
      const blockAlign =
        targetChannels * bytesPerSample;

      const byteRate =
        targetSampleRate * blockAlign;

      const wavBuffer =
        new ArrayBuffer(
          44 + monoSamples.length * bytesPerSample
        );

      const view =
        new DataView(wavBuffer);

      const writeString = (
        offset: number,
        value: string
      ) => {
        for (let i = 0; i < value.length; i++) {
          view.setUint8(
            offset + i,
            value.charCodeAt(i)
          );
        }
      };

      writeString(0, 'RIFF');

      view.setUint32(
        4,
        36 + monoSamples.length * bytesPerSample,
        true
      );

      writeString(8, 'WAVE');

      writeString(12, 'fmt ');

      view.setUint32(16, 16, true);
      view.setUint16(20, 1, true);
      view.setUint16(22, targetChannels, true);
      view.setUint32(24, targetSampleRate, true);
      view.setUint32(28, byteRate, true);
      view.setUint16(32, blockAlign, true);
      view.setUint16(34, 16, true);

      writeString(36, 'data');

      view.setUint32(
        40,
        monoSamples.length * bytesPerSample,
        true
      );

      let offset = 44;

      for (let i = 0; i < monoSamples.length; i++) {
        const sample =
          Math.max(
            -1,
            Math.min(1, monoSamples[i])
          );

        const pcm =
          sample < 0
            ? sample * 0x8000
            : sample * 0x7fff;

        view.setInt16(
          offset,
          Math.round(pcm),
          true
        );

        offset += 2;
      }

      return new Blob(
        [wavBuffer],
        { type: 'audio/wav' }
      );
    } finally {
      await audioContext.close();
    }
  };
  const stopVoiceActivityMonitor = () => {
    if (vadIntervalRef.current !== null) {
      window.clearInterval(vadIntervalRef.current);
      vadIntervalRef.current = null;
    }

    silenceStartedAtRef.current = null;
    speechDetectedRef.current = false;

    const audioContext = audioContextRef.current;

    if (audioContext) {
      try {
        void audioContext.close();
      } catch (error) {
        console.warn(
          '[SEVAK][VOICE] Failed to close VAD audio context:',
          error
        );
      }

      audioContextRef.current = null;
    }
  };

  const startVoiceActivityMonitor = (stream: MediaStream) => {
    stopVoiceActivityMonitor();

    const AudioContextClass =
      window.AudioContext ||
      (window as any).webkitAudioContext;

    if (!AudioContextClass) {
      console.warn(
        '[SEVAK][VOICE] Web Audio API unavailable. Manual stop remains available.'
      );
      return;
    }

    try {
      const audioContext = new AudioContextClass();

      audioContextRef.current = audioContext;

      const analyser = audioContext.createAnalyser();

      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.15;

      const source =
        audioContext.createMediaStreamSource(stream);

      source.connect(analyser);

      const data = new Uint8Array(analyser.fftSize);

      // Voice activity settings.
      // User must speak first.
      // After speech stops, 1.2 seconds of silence ends the recording.
      const SILENCE_THRESHOLD = 0.018;
      const SILENCE_DURATION_MS = 1200;
      const MAX_RECORDING_MS = 30000;

      const startedAt = performance.now();

      speechDetectedRef.current = false;
      silenceStartedAtRef.current = null;

      vadIntervalRef.current = window.setInterval(() => {
        const recorder = mediaRecorderRef.current;

        if (!recorder || recorder.state !== 'recording') {
          stopVoiceActivityMonitor();
          return;
        }

        analyser.getByteTimeDomainData(data);

        let sum = 0;

        for (let i = 0; i < data.length; i += 1) {
          const normalized = (data[i] - 128) / 128;
          sum += normalized * normalized;
        }

        const rms = Math.sqrt(sum / data.length);
        const now = performance.now();

        // Speech/noise detected.
        if (rms >= SILENCE_THRESHOLD) {
          speechDetectedRef.current = true;
          silenceStartedAtRef.current = null;
          return;
        }

        // Do not stop while waiting for the user to begin speaking.
        if (!speechDetectedRef.current) {
          if (now - startedAt >= MAX_RECORDING_MS) {
            console.log(
              '[SEVAK][VOICE] Maximum recording time reached. Auto-stopping...'
            );

            try {
              recorder.stop();
            } catch (error) {
              console.warn(
                '[SEVAK][VOICE] Failed to stop recorder:',
                error
              );
            }
          }

          return;
        }

        // Speech has already happened.
        // Start measuring silence.
        if (silenceStartedAtRef.current === null) {
          silenceStartedAtRef.current = now;
          return;
        }

        const silenceDuration =
          now - silenceStartedAtRef.current;

        if (silenceDuration >= SILENCE_DURATION_MS) {
          console.log(
            '[SEVAK][VOICE] Speech ended. Auto-stopping recording...'
          );

          try {
            recorder.stop();
          } catch (error) {
            console.warn(
              '[SEVAK][VOICE] Failed to auto-stop recorder:',
              error
            );
          }
        }
      }, 100);

    } catch (error) {
      console.warn(
        '[SEVAK][VOICE] VAD initialization failed. Manual stop remains available.',
        error
      );

      stopVoiceActivityMonitor();
    }
  };

  const scheduleAutomaticListening = () => {
    if (!voiceSessionRef.current) {
      return;
    }

    window.setTimeout(() => {
      if (!voiceSessionRef.current) {
        return;
      }

      console.log(
        '[SEVAK][VOICE] Automatically resuming microphone...'
      );

      startListening(true);
    }, 500);
  };

  const startListening = async (automatic = false) => {
    voiceSessionRef.current = true;
    console.log('[SEVAK][VOICE] START LISTENING CLICKED');

    setErrorMessage('🎤 Microphone permission check ho rahi hai...');

    // Manual mic click starts a fresh question.
    // Automatic restart keeps the previous "You said" transcript
    // and answer visible until the next transcript is received.
    if (!automatic) {
      setSevakAnswer(null);
      setTranscript('');
    }

    setIsProcessing(false);

    if (!window.isSecureContext) {
      setErrorMessage(
        'Microphone ke liye localhost use karein: http://localhost:3000/'
      );
      console.error('[SEVAK][VOICE] Insecure context:', window.location.href);
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMessage(
        'Browser microphone access support nahi karta. Chrome/Edge mein localhost par try karein.'
      );
      console.error('[SEVAK][VOICE] getUserMedia unavailable');
      return;
    }

    if (typeof MediaRecorder === 'undefined') {
      setErrorMessage(
        'Browser audio recording support nahi karta.'
      );
      console.error('[SEVAK][VOICE] MediaRecorder unavailable');
      return;
    }

    try {
      console.log('[SEVAK][VOICE] Requesting microphone permission...');

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });

      console.log('[SEVAK][VOICE] MICROPHONE ACCESS GRANTED');

      mediaStreamRef.current = stream;

      const audioTracks = stream.getAudioTracks();

      console.log('[SEVAK][VOICE] Audio tracks:', audioTracks.map((track) => ({
        label: track.label,
        enabled: track.enabled,
        muted: track.muted,
        readyState: track.readyState,
      })));

      if (!audioTracks.length) {
        throw new Error('Microphone stream mein audio track nahi mila.');
      }

      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
      ];

      const supportedMimeType =
        mimeTypes.find((type) => MediaRecorder.isTypeSupported(type)) || '';

      console.log('[SEVAK][VOICE] Recorder MIME:', supportedMimeType || 'browser-default');

      const recorder = supportedMimeType
        ? new MediaRecorder(stream, {
            mimeType: supportedMimeType,
          })
        : new MediaRecorder(stream);

      audioChunksRef.current = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);

          console.log('[SEVAK][VOICE] Audio chunk:', {
            size: event.data.size,
            type: event.data.type,
          });
        }
      };

      recorder.onstart = () => {
        console.log('[SEVAK][VOICE] RECORDING STARTED');

        setIsListening(true);
        setErrorMessage(
          '🎙️ Sun raha hoon... Bolna start karein. Complete hone par mic dobara dabayein.'
        );
      };

      recorder.onerror = (event) => {
        console.error('[SEVAK][VOICE] MediaRecorder error:', event);

        setIsListening(false);

        setErrorMessage(
          'Audio recording mein problem aayi. Please microphone permission/check karke dobara try karein.'
        );

        cleanupMediaStream();
      };

      recorder.onstop = async () => {
        stopVoiceActivityMonitor();
        console.log('[SEVAK][VOICE] RECORDING STOPPED');

        setIsListening(false);

        const chunks = audioChunksRef.current;

        console.log('[SEVAK][VOICE] Total audio chunks:', chunks.length);

        if (!chunks.length) {
          setErrorMessage(
            'Koi audio capture nahi hua. Please dobara boliye.'
          );
          cleanupMediaStream();
          scheduleAutomaticListening();
          return;
        }

        const recordedBlob = new Blob(chunks, {
          type: recorder.mimeType || 'audio/webm',
        });

        console.log('[SEVAK][VOICE] Recorded audio:', {
          type: recordedBlob.type,
          size: recordedBlob.size,
        });

        cleanupMediaStream();

        setIsProcessing(true);
        setErrorMessage('🔊 Audio process ho raha hai...');

        try {
          console.log('[SEVAK][VOICE] Converting audio to WAV...');

          const audioBlob =
            await convertAudioBlobToWav(recordedBlob);

          console.log('[SEVAK][VOICE] WAV ready:', {
            type: audioBlob.type,
            size: audioBlob.size,
          });

          setErrorMessage('🧠 SEVAK aapki voice samajh raha hai...');

          console.log('[SEVAK][VOICE] Sending audio to Prisma STT...');

          const finalTranscript =
            await SevakApiService.transcribeAudio(
              audioBlob,
              selectedLanguage
            );

          console.log(
            '[SEVAK][VOICE] Prisma transcript:',
            finalTranscript
          );

          if (!finalTranscript) {
            setErrorMessage(
              'SEVAK aapki awaaz samajh nahi paaya. Please clearly dobara boliye.'
            );
            return;
          }

          setTranscript(finalTranscript);

          const currentVoiceQuestion = finalTranscript.trim();

          if (!currentVoiceQuestion) {
            setErrorMessage(
              'SEVAK aapki awaaz samajh nahi paaya. Please dobara clearly boliye.'
            );
            scheduleAutomaticListening();
            return;
          }

          setTranscript(currentVoiceQuestion);

          setErrorMessage('✨ Answer prepare ho raha hai...');

          console.log('[SEVAK][VOICE] Sending question:', {
            question: currentVoiceQuestion,
            documentId: currentDocumentId,
            language: selectedLanguage,
          });

          const answer =
            await SevakApiService.askQuestion({
              question: currentVoiceQuestion,
              documentId: currentDocumentId,
              language: selectedLanguage,
            });

          console.log(
            '[SEVAK][VOICE] SEVAK answer:',
            answer
          );

          if (!answer) {
            throw new Error('SEVAK ne empty answer return kiya.');
          }

          setSevakAnswer(answer);

          console.log('[SEVAK][VOICE] Speaking answer...');

          speakAnswer(answer);

        } catch (error) {
          console.error(
            '[SEVAK][VOICE] Voice pipeline failed:',
            error
          );

          const message =
            error instanceof Error
              ? error.message
              : 'Unknown voice processing error';

          setErrorMessage(
            `Voice processing mein problem aayi: ${message}`
          );

          // Keep the current voice session alive after
          // a temporary STT / question / TTS failure.
          scheduleAutomaticListening();

        } finally {
          setIsProcessing(false);
        }
      };

      mediaRecorderRef.current = recorder;

      recorder.start(250);
      startVoiceActivityMonitor(stream);
      console.log('[SEVAK][VOICE] recorder.start() called');

    } catch (error) {
      console.error(
        '[SEVAK][VOICE] MICROPHONE ACCESS FAILED:',
        error
      );

      setIsListening(false);
      voiceSessionRef.current = false;
      cleanupMediaStream();

      if (error instanceof DOMException) {
        if (error.name === 'NotAllowedError') {
          setErrorMessage(
            '🎤 Microphone permission denied hai. Browser mein Microphone → Allow karein, phir page reload karein.'
          );
        } else if (error.name === 'NotFoundError') {
          setErrorMessage(
            '🎤 Koi microphone detect nahi hua. Windows microphone/device settings check karein.'
          );
        } else if (error.name === 'NotReadableError') {
          setErrorMessage(
            '🎤 Microphone kisi aur application mein busy hai. Dusri recording app/browser tab band karke try karein.'
          );
        } else if (error.name === 'SecurityError') {
          setErrorMessage(
            '🔒 Browser ne microphone security ke wajah se block kiya. Sirf http://localhost:3000/ use karein.'
          );
        } else {
          setErrorMessage(
            `Microphone error: ${error.name}`
          );
        }
      } else {
        setErrorMessage(
          'Microphone access nahi mil saka. Please browser microphone permission allow karein.'
        );
      }
    }
  };
  const stopListening = () => {
    stopVoiceActivityMonitor();
    // User explicitly pressed the mic button to stop.
    // Do not automatically start listening again after TTS.
    voiceSessionRef.current = false;

    const recorder = mediaRecorderRef.current;

    if (recorder) {
      try {
        if (recorder.state !== 'inactive') {
          recorder.stop();
          return;
        }
      } catch (error) {
        console.warn('Failed to stop recorder:', error);
      }
    }

    cleanupMediaStream();
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
    if (!window.speechSynthesis || !text.trim()) {
      console.warn('Browser speech synthesis is unavailable.');
      return;
    }

    const synthesis = window.speechSynthesis;

    // Stop any previous utterance before starting a new one.
    synthesis.cancel();

    const speak = () => {
      const cleanText = text.trim();

      if (!cleanText) {
        setIsSpeaking(false);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(cleanText);

      const voices = synthesis.getVoices();

      const preferredVoice =
        voices.find((voice) =>
          selectedLanguage === 'hindi'
            ? voice.lang.toLowerCase().startsWith('hi-in')
            : voice.lang.toLowerCase().startsWith('en-in')
        ) ||
        voices.find((voice) =>
          selectedLanguage === 'hindi'
            ? voice.lang.toLowerCase().startsWith('hi')
            : voice.lang.toLowerCase().startsWith('en')
        );

      // Only assign a voice when Chrome actually provides one.
      // Otherwise let the browser choose its default voice.
      if (preferredVoice) {
        utterance.voice = preferredVoice;
        utterance.lang = preferredVoice.lang;
      } else {
        utterance.lang =
          selectedLanguage === 'hindi' ? 'hi-IN' : 'en-IN';
      }

      utterance.rate = 0.95;
      utterance.pitch = 1;
      utterance.volume = 1;

      utterance.onstart = () => {
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        setIsSpeaking(false);

        // Continue the voice conversation only while the
        // user-controlled voice session is still ON.
        if (voiceSessionRef.current) {
          console.log(
            '[SEVAK][VOICE] Answer finished. Resuming listening...'
          );

          window.setTimeout(() => {
            if (voiceSessionRef.current) {
              console.log(
                '[SEVAK][VOICE] Restarting microphone for next question...'
              );
              startListening(true);
            }
          }, 400);
        }
      };

      utterance.onerror = (event) => {
        // Chrome can report "canceled" or "interrupted" when a previous
        // utterance is stopped. These are not real TTS failures.
        if (
          event.error !== 'canceled' &&
          event.error !== 'interrupted'
        ) {
          console.error('Speech synthesis error:', event.error);
        }

        setIsSpeaking(false);

        if (
          event.error !== 'canceled' &&
          event.error !== 'interrupted' &&
          voiceSessionRef.current
        ) {
          scheduleAutomaticListening();
        }
      };

      setIsSpeaking(true);
      synthesis.speak(utterance);
    };

    // Chrome can load voices asynchronously. Wait briefly only when
    // the voice list is genuinely empty, and ensure the handler fires once.
    const voices = synthesis.getVoices();

    if (voices.length > 0) {
      speak();
    } else {
      let spoken = false;

      const speakOnce = () => {
        if (spoken) return;
        spoken = true;
        synthesis.onvoiceschanged = null;
        speak();
      };

      synthesis.onvoiceschanged = speakOnce;

      window.setTimeout(speakOnce, 500);
    }
  };

  const handleQuickQuestion = (q: string) => {
    setTranscript(q);
    handleProcessQuestion(q);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[99999] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200">
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
              onClick={isListening ? stopListening : () => startListening()}
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














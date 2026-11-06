import React, { useRef } from 'react';
import { ArrowRight, Cloud, Plus, Mic } from 'lucide-react';

interface ActionButtonsProps {
  onFileSelect: (file: File) => void;
  onVoiceClick: () => void;
  isListening?: boolean;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onFileSelect,
  onVoiceClick,
  isListening,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 8 * 1024 * 1024) {
        alert('File size exceeds the 8 MB limit. Please select a smaller document.');
        return;
      }
      onFileSelect(file);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3.5 sm:gap-4 mt-6 sm:mt-8 w-full max-w-xl">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={handleFileChange}
        aria-hidden="true"
      />

      {/* 1. Glossy Blue Button: Upload Document */}
      <button
        onClick={handleUploadClick}
        type="button"
        className="glossy-blue-button group relative flex-1 flex items-center justify-between px-5 sm:px-6 py-3.5 sm:py-4 rounded-full text-white cursor-pointer transition-all duration-200 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
        aria-label="Upload Document (PDF, JPG, PNG up to 8 MB)"
      >
        <div className="flex items-center gap-3.5">
          {/* Cloud Icon with Plus */}
          <div className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-white/15 flex items-center justify-center shrink-0 border border-white/20">
            <Cloud className="w-5 h-5 text-white" strokeWidth={2.2} fill="white" fillOpacity={0.2} />
            <span className="absolute inset-0 flex items-center justify-center pt-0.5">
              <Plus className="w-3 h-3 text-white" strokeWidth={3} />
            </span>
          </div>

          {/* Text Labels */}
          <div className="text-left flex flex-col">
            <span className="text-[15px] sm:text-[17px] font-bold tracking-tight text-white leading-tight font-display">
              Upload Document
            </span>
            <span className="text-[11px] sm:text-[12px] text-blue-100/90 font-medium">
              PDF, JPG, PNG up to 8 MB
            </span>
          </div>
        </div>

        {/* Right Arrow */}
        <div className="w-7 h-7 flex items-center justify-center rounded-full text-white group-hover:translate-x-1 transition-transform">
          <ArrowRight className="w-5 h-5 text-white" strokeWidth={2.2} />
        </div>
      </button>

      {/* 2. Glossy Amber Button: Ask by Voice */}
      <button
        onClick={onVoiceClick}
        type="button"
        className={`glossy-amber-button group relative flex-1 flex items-center justify-between px-5 sm:px-6 py-3.5 sm:py-4 rounded-full cursor-pointer transition-all duration-200 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
          isListening ? 'ring-4 ring-amber-400/50 scale-[1.02]' : ''
        }`}
        aria-label="Ask by Voice (Mujhe ye document samjhao)"
      >
        <div className="flex items-center gap-3.5">
          {/* Microphone Icon */}
          <div className="relative w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-amber-500/15 flex items-center justify-center shrink-0 border border-amber-600/20">
            <Mic
              className={`w-5 h-5 text-[#632a0c] ${
                isListening ? 'animate-bounce text-red-600' : ''
              }`}
              strokeWidth={2.4}
            />
          </div>

          {/* Text Labels */}
          <div className="text-left flex flex-col">
            <span className="text-[15px] sm:text-[17px] font-bold tracking-tight text-[#451a03] leading-tight font-display">
              Ask by Voice
            </span>
            <span className="text-[11px] sm:text-[12px] text-[#78350f] font-medium">
              {isListening ? 'Listening now...' : "Mujhe ye document samjhao'"}
            </span>
          </div>
        </div>

        {/* Right Arrow */}
        <div className="w-7 h-7 flex items-center justify-center rounded-full text-[#542007] group-hover:translate-x-1 transition-transform">
          <ArrowRight className="w-5 h-5 text-[#542007]" strokeWidth={2.2} />
        </div>
      </button>
    </div>
  );
};

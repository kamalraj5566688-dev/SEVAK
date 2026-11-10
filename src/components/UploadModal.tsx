import React, { useState, useRef } from 'react';
import { Upload, X, FileText, AlertCircle, Sparkles, ShieldAlert, FileCheck } from 'lucide-react';
import { SAMPLE_DOCUMENTS } from '../data/sampleDocuments';
import { SevakAnalysisResult } from '../types';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFileSelect: (file: File) => void;
  onSelectSampleDoc: (sample: SevakAnalysisResult) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onFileSelect,
  onSelectSampleDoc,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const validateAndProceed = (file: File) => {
    setError(null);
    const validTypes = [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png',
      'image/webp',
    ];

    const hasValidExt = /\.(pdf|jpg|jpeg|png|webp)$/i.test(file.name);

    if (!validTypes.includes(file.type) && !hasValidExt) {
      setError('Unsupported file type. Please upload a PDF, JPG, PNG, or WEBP document.');
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setError('File size exceeds the 8 MB limit. Please compress or select a smaller document.');
      return;
    }

    onFileSelect(file);
    onClose();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      validateAndProceed(file);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-[#FAF7F0] rounded-3xl border border-slate-200 shadow-2xl p-6 sm:p-7 overflow-hidden">
        {/* Background glow */}
        <div className="absolute -top-16 -right-16 w-44 h-44 rounded-full bg-blue-300/30 blur-2xl pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-44 h-44 rounded-full bg-orange-300/30 blur-2xl pointer-events-none" />

        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 transition-colors focus:outline-none"
          aria-label="Close upload modal"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-2xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center text-[#0B57D0]">
            <Upload className="w-5 h-5 text-[#0B57D0]" strokeWidth={2.4} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-[#082C5A] font-display">
              Upload Document for SEVAK
            </h3>
            <p className="text-xs text-slate-600">
              PDF, JPG, PNG up to 8 MB
            </p>
          </div>
        </div>

        {/* Drag and Drop Box */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-7 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-blue-500 bg-blue-50/80 scale-[1.01]'
              : 'border-slate-300 hover:border-blue-400 bg-white'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) validateAndProceed(file);
            }}
          />

          <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center text-[#0B57D0] mb-3 shadow-2xs">
            <Upload className="w-6 h-6" />
          </div>

          <h4 className="text-sm font-bold text-[#082C5A] mb-1 font-display">
            Drag & drop document here, or <span className="text-[#0B57D0] underline">browse</span>
          </h4>
          <p className="text-xs text-slate-500 max-w-xs">
            Government notices, traffic challans, bank letters, court summons, ya registry kagaz
          </p>

          <span className="mt-3 inline-block text-[11px] font-semibold text-slate-400 bg-slate-100 px-3 py-1 rounded-full">
            Max 8 MB • PDF, PNG, JPG, WEBP
          </span>
        </div>

        {/* Validation Error */}
        {error && (
          <div className="mt-3.5 p-3 bg-red-50 rounded-xl border border-red-200 flex items-center gap-2 text-xs text-red-800">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Quick Sample Document Selector for Instant Test */}
        <div className="mt-6 pt-4 border-t border-slate-200">
          <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5 mb-2 font-display">
            <Sparkles className="w-3.5 h-3.5 text-orange-500" />
            Demo sample documents — real upload se alag:
          </span>

          <div className="space-y-2">
            <button
              onClick={() => {
                onSelectSampleDoc(SAMPLE_DOCUMENTS.echallan);
                onClose();
              }}
              className="w-full flex items-center justify-between p-2.5 rounded-xl bg-white hover:bg-blue-50/70 border border-slate-200 transition-colors text-left group"
            >
              <div className="flex items-center gap-2.5">
                <FileText className="w-4 h-4 text-blue-600 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">
                    Delhi Traffic Police E-Challan Notice
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Over-speeding fine (₹2,000) • Section 133
                  </span>
                </div>
              </div>
              <span className="text-xs font-semibold text-blue-600 group-hover:translate-x-0.5 transition-transform">
                Test &rarr;
              </span>
            </button>

            <button
              onClick={() => {
                onSelectSampleDoc(SAMPLE_DOCUMENTS.bank_kyc);
                onClose();
              }}
              className="w-full flex items-center justify-between p-2.5 rounded-xl bg-white hover:bg-amber-50/70 border border-slate-200 transition-colors text-left group"
            >
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">
                    SBI Bank Re-KYC Update Notice
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Account freeze warning • RBI Master Direction
                  </span>
                </div>
              </div>
              <span className="text-xs font-semibold text-amber-600 group-hover:translate-x-0.5 transition-transform">
                Test &rarr;
              </span>
            </button>

            <button
              onClick={() => {
                onSelectSampleDoc(SAMPLE_DOCUMENTS.tax_notice);
                onClose();
              }}
              className="w-full flex items-center justify-between p-2.5 rounded-xl bg-white hover:bg-orange-50/70 border border-slate-200 transition-colors text-left group"
            >
              <div className="flex items-center gap-2.5">
                <FileCheck className="w-4 h-4 text-orange-600 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-slate-800 block">
                    Income Tax Clarification Notice
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Interest mismatch inquiry • Section 142(1)
                  </span>
                </div>
              </div>
              <span className="text-xs font-semibold text-orange-600 group-hover:translate-x-0.5 transition-transform">
                Test &rarr;
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};



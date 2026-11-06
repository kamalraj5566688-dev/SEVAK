import React from 'react';

interface RobotIllustrationProps {
  onVoiceClick?: () => void;
  isListening?: boolean;
}

export const RobotIllustration: React.FC<RobotIllustrationProps> = ({
  onVoiceClick,
  isListening,
}) => {
  return (
    <div className="relative w-full max-w-[580px] lg:max-w-[640px] xl:max-w-[700px] mx-auto flex items-center justify-center select-none">
      {/* Background Indian Tricolor Subtle Glow */}
      <div
        className="absolute -left-12 -top-10 w-[90%] h-[90%] rounded-full bg-gradient-to-tr from-orange-200/40 via-amber-100/20 to-emerald-100/30 blur-2xl pointer-events-none -z-10"
        aria-hidden="true"
      />

      {/* Main Pixel-Accurate Hero Robot Composition */}
      <div className="relative w-full aspect-[845/420] overflow-visible">
        <img
          src="/public/assets/images/hero_robot_final.png"
          alt="SEVAK AI Robot Assistant holding a legal document with justice scales and sound wave speech bubble"
          className="w-full h-auto object-contain drop-shadow-md pointer-events-none"
          loading="eager"
        />

        {/* Interactive Speech Bubble Click Affordance */}
        <button
          onClick={onVoiceClick}
          className={`absolute top-[2%] right-[1%] w-[24%] h-[40%] rounded-full opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center cursor-pointer group focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500`}
          title="Click to speak with SEVAK"
          aria-label="Click to ask SEVAK by voice"
        >
          <span className="sr-only">Ask by voice</span>
          <span className="absolute inset-0 rounded-3xl bg-blue-500/10 scale-95 group-hover:scale-105 transition-transform" />
        </button>

        {/* Live Audio Equalizer Overlay on Speech Bubble when listening */}
        {isListening && (
          <div className="absolute top-[8%] right-[4%] w-[18%] h-[32%] flex items-center justify-center gap-1 pointer-events-none">
            <span className="w-1 bg-white rounded-full soundwave-bar" style={{ animationDelay: '0ms' }} />
            <span className="w-1 bg-white rounded-full soundwave-bar" style={{ animationDelay: '150ms' }} />
            <span className="w-1 bg-white rounded-full soundwave-bar" style={{ animationDelay: '300ms' }} />
            <span className="w-1 bg-white rounded-full soundwave-bar" style={{ animationDelay: '450ms' }} />
            <span className="w-1 bg-white rounded-full soundwave-bar" style={{ animationDelay: '200ms' }} />
          </div>
        )}

        {/* Ambient Pulse on Robot's Chest Soundwave */}
        <div
          className="absolute top-[52%] left-[64%] -translate-x-1/2 w-8 h-4 rounded-full bg-cyan-400/20 blur-sm pointer-events-none animate-pulse"
          aria-hidden="true"
        />
      </div>
    </div>
  );
};

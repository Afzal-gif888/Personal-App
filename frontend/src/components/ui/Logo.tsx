import React from 'react';

interface LogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  withText?: boolean;
  subtext?: string;
  className?: string;
}

const SIZE_MAP = {
  xs: { box: 'w-5 h-5', svg: 20 },
  sm: { box: 'w-7 h-7', svg: 28 },
  md: { box: 'w-8 h-8', svg: 32 },
  lg: { box: 'w-10 h-10', svg: 40 },
  xl: { box: 'w-12 h-12', svg: 48 },
};

export const LogoIcon: React.FC<{ size?: number; className?: string }> = ({ size = 28, className = '' }) => {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`shrink-0 select-none ${className}`}
    >
      <defs>
        {/* Background Gradient */}
        <linearGradient id="logo-bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#0B0D14" />
          <stop offset="50%" stopColor="#0E121E" />
          <stop offset="100%" stopColor="#07080D" />
        </linearGradient>

        {/* Academic / Knowledge Vector */}
        <linearGradient id="logo-academic" x1="15%" y1="10%" x2="85%" y2="90%">
          <stop offset="0%" stopColor="#6366F1" />
          <stop offset="100%" stopColor="#8B5CF6" />
        </linearGradient>

        {/* Personal Life & Finance Vector */}
        <linearGradient id="logo-personal" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B5CF6" />
          <stop offset="100%" stopColor="#EC4899" />
        </linearGradient>

        {/* Autonomous AI Kernel */}
        <linearGradient id="logo-ai" x1="0%" y1="100%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#06B6D4" />
          <stop offset="50%" stopColor="#3B82F6" />
          <stop offset="100%" stopColor="#6366F1" />
        </linearGradient>

        <radialGradient id="logo-kernel" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="45%" stopColor="#67E8F9" />
          <stop offset="100%" stopColor="#06B6D4" />
        </radialGradient>

        <filter id="logo-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feColorMatrix type="matrix" values="0 0 0 0 0.02   0 0 0 0 0.71   0 0 0 0 0.83  0 0 0 0.7 0" />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Outer Chassis */}
      <rect width="64" height="64" rx="16" fill="url(#logo-bg)" />
      <rect x="0.75" y="0.75" width="62.5" height="62.5" rx="15.25" stroke="#1F2437" strokeWidth="1.5" />

      {/* Ambient Neural Orbits */}
      <circle cx="32" cy="33" r="23" stroke="#252A40" strokeWidth="1" strokeDasharray="3 3" opacity="0.6" />
      <circle cx="32" cy="33" r="15" stroke="#2C334D" strokeWidth="0.75" opacity="0.4" />

      {/* Tri-loop / 'A' Monogram: Left wing (AI & Reasoning) */}
      <path d="M 32 13 L 16 46 L 24.5 46 L 32 29.5 L 34.5 35 L 39 31.5 Z" fill="url(#logo-ai)" opacity="0.95" />

      {/* Right wing (Academic & Mastery) */}
      <path d="M 32 13 L 48 46 L 39.5 46 L 32 29.5 L 39 31.5 Z" fill="url(#logo-academic)" opacity="0.95" />

      {/* Cross bridge (Personal Life & Finance Integration) */}
      <path d="M 21.5 37.5 C 26 35 38 35 42.5 37.5 L 44 34 C 38 31 26 31 20 34 Z" fill="url(#logo-personal)" />

      {/* Autonomous Agent AI Kernel */}
      <circle cx="32" cy="33" r="4.5" fill="url(#logo-kernel)" filter="url(#logo-glow)" />
      <circle cx="32" cy="33" r="1.75" fill="#FFFFFF" />

      {/* Satellites */}
      <circle cx="48" cy="22" r="1.5" fill="#38BDF8" opacity="0.8" />
      <circle cx="16" cy="25" r="1.25" fill="#A855F7" opacity="0.8" />
      <circle cx="32" cy="51" r="1.5" fill="#EC4899" opacity="0.8" />
    </svg>
  );
};

export const Logo: React.FC<LogoProps> = ({
  size = 'md',
  withText = false,
  subtext,
  className = '',
}) => {
  const { svg } = SIZE_MAP[size];

  if (!withText) {
    return <LogoIcon size={svg} className={className} />;
  }

  return (
    <div className={`flex items-center gap-2.5 overflow-hidden ${className}`}>
      <LogoIcon size={svg} />
      <div className="flex flex-col leading-none">
        <span className="font-semibold text-sm tracking-tight text-[#111111]">AgentOS</span>
        {subtext && <span className="text-[10px] text-[#8A8A8A] mt-0.5">{subtext}</span>}
      </div>
    </div>
  );
};

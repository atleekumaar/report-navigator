import React from "react";

/**
 * 3D-styled Document with Chart & Magnifying Glass Hero Illustration
 */
export const HeroDocMagnifierIllustration: React.FC<{ className?: string }> = ({
  className = "w-36 h-36",
}) => {
  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      {/* Outer subtle glow */}
      <div className="absolute inset-0 bg-[#FF5C93]/20 rounded-full blur-2xl transform scale-110" />

      <svg
        viewBox="0 0 240 220"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10 drop-shadow-[0_12px_24px_rgba(240,80,140,0.35)]"
      >
        <defs>
          <linearGradient id="docGrad" x1="40" y1="20" x2="160" y2="180" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFF2F6" />
            <stop offset="0.6" stopColor="#F9D2DF" />
            <stop offset="1" stopColor="#EAAAC0" />
          </linearGradient>
          <linearGradient id="chartBar1" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#FF7AA8" />
            <stop offset="1" stopColor="#E02875" />
          </linearGradient>
          <linearGradient id="chartBar2" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#FFA6C5" />
            <stop offset="1" stopColor="#F0508C" />
          </linearGradient>
          <linearGradient id="lensGrad" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="rgba(255, 255, 255, 0.7)" />
            <stop offset="0.4" stopColor="rgba(255, 180, 210, 0.3)" />
            <stop offset="1" stopColor="rgba(224, 40, 117, 0.45)" />
          </linearGradient>
          <linearGradient id="rimGrad" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#FFFFFF" />
            <stop offset="0.5" stopColor="#FF75AA" />
            <stop offset="1" stopColor="#9B104E" />
          </linearGradient>
          <linearGradient id="handleGrad" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="#FF8FBA" />
            <stop offset="0.7" stopColor="#C91866" />
            <stop offset="1" stopColor="#60052D" />
          </linearGradient>
        </defs>

        {/* Orbital glow rings */}
        <ellipse
          cx="120"
          cy="110"
          rx="98"
          ry="44"
          transform="rotate(-24 120 110)"
          stroke="#FF7AA8"
          strokeWidth="1.5"
          strokeDasharray="6 4"
          opacity="0.45"
        />
        <circle cx="205" cy="70" r="3" fill="#FFB3CE" opacity="0.8" />
        <circle cx="36" cy="150" r="2.5" fill="#FFA3C5" opacity="0.7" />

        {/* Tilted Document with Folded Corner */}
        <g transform="rotate(-12 110 95)">
          {/* Shadow */}
          <rect x="52" y="24" width="94" height="132" rx="10" fill="#200315" opacity="0.6" />
          {/* Main Paper Sheet */}
          <rect x="48" y="20" width="94" height="132" rx="10" fill="url(#docGrad)" />

          {/* Document Header lines */}
          <rect x="60" y="34" width="46" height="5" rx="2.5" fill="#E02875" opacity="0.75" />
          <rect x="60" y="44" width="70" height="3" rx="1.5" fill="#B56787" opacity="0.4" />

          {/* Bar Chart Visualization on Paper */}
          <g transform="translate(62, 70)">
            {/* Axis */}
            <line x1="0" y1="46" x2="66" y2="46" stroke="#D181A0" strokeWidth="1.5" opacity="0.6" />
            {/* Bars */}
            <rect x="4" y="24" width="9" height="22" rx="2" fill="url(#chartBar1)" />
            <rect x="18" y="14" width="9" height="32" rx="2" fill="url(#chartBar2)" />
            <rect x="32" y="6" width="9" height="40" rx="2" fill="url(#chartBar1)" />
            <rect x="46" y="18" width="9" height="28" rx="2" fill="url(#chartBar2)" />
            {/* Growth Trend line */}
            <path
              d="M 8 20 Q 22 10, 36 4 T 50 14"
              fill="none"
              stroke="#FFF0F5"
              strokeWidth="2"
              strokeLinecap="round"
            />
            <circle cx="36" cy="4" r="2.5" fill="#FFFFFF" />
          </g>

          {/* Summary table lines */}
          <rect x="60" y="126" width="70" height="3" rx="1.5" fill="#B56787" opacity="0.35" />
          <rect x="60" y="134" width="50" height="3" rx="1.5" fill="#B56787" opacity="0.3" />
        </g>

        {/* 3D Magnifying Glass */}
        <g transform="translate(118, 88) rotate(14)">
          {/* Handle shadow */}
          <rect x="36" y="38" width="14" height="48" rx="7" transform="rotate(-45 36 38)" fill="#200315" opacity="0.5" />
          {/* Handle */}
          <rect
            x="34"
            y="34"
            width="12"
            height="46"
            rx="6"
            transform="rotate(-45 34 34)"
            fill="url(#handleGrad)"
            stroke="#FFB3CE"
            strokeWidth="1.2"
          />
          {/* Handle ferrule ring */}
          <rect
            x="24"
            y="24"
            width="14"
            height="5"
            rx="2.5"
            transform="rotate(-45 24 24)"
            fill="#FFFFFF"
          />

          {/* Lens Outer Rim */}
          <circle cx="0" cy="0" r="38" fill="none" stroke="url(#rimGrad)" strokeWidth="5.5" />
          {/* Lens Glass */}
          <circle cx="0" cy="0" r="35" fill="url(#lensGrad)" />
          {/* Lens Glass Highlight arc */}
          <path
            d="M -22 -14 A 28 28 0 0 1 14 -22"
            stroke="#FFFFFF"
            strokeWidth="3"
            strokeLinecap="round"
            opacity="0.8"
          />
        </g>

        {/* Sparkle Stars */}
        <path
          d="M 188 56 Q 192 56, 194 52 Q 196 56, 200 56 Q 196 56, 194 60 Q 192 56, 188 56 Z"
          fill="#FFF"
        />
        <path
          d="M 38 78 Q 41 78, 42 75 Q 43 78, 46 78 Q 43 78, 42 81 Q 41 78, 38 78 Z"
          fill="#FFB8D2"
        />
      </svg>
    </div>
  );
};

/**
 * 3D Folder with Documents & Magnifier Evidence Empty-State Illustration
 */
export const EvidenceFolderIllustration: React.FC<{ className?: string }> = ({
  className = "w-44 h-44",
}) => {
  return (
    <div className={`relative flex items-center justify-center select-none ${className}`}>
      {/* Outer ambient glow */}
      <div className="absolute inset-0 bg-[#FF5C93]/20 rounded-full blur-2xl transform scale-110" />

      <svg
        viewBox="0 0 240 220"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full relative z-10 drop-shadow-[0_12px_28px_rgba(240,80,140,0.3)]"
      >
        <defs>
          <linearGradient id="folderBack" x1="30" y1="40" x2="190" y2="160" gradientUnits="userSpaceOnUse">
            <stop stopColor="#9C1751" />
            <stop offset="1" stopColor="#550A30" />
          </linearGradient>
          <linearGradient id="folderFront" x1="40" y1="80" x2="180" y2="180" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FF7AA8" />
            <stop offset="0.6" stopColor="#E02875" />
            <stop offset="1" stopColor="#8C0D43" />
          </linearGradient>
          <linearGradient id="evDoc" x1="60" y1="30" x2="140" y2="120" gradientUnits="userSpaceOnUse">
            <stop stopColor="#FFFFFF" />
            <stop offset="1" stopColor="#F9D4E2" />
          </linearGradient>
          <linearGradient id="evLens" x1="0" y1="0" x2="1" y2="1">
            <stop stopColor="rgba(255, 255, 255, 0.75)" />
            <stop offset="0.6" stopColor="rgba(255, 175, 205, 0.35)" />
            <stop offset="1" stopColor="rgba(224, 40, 117, 0.5)" />
          </linearGradient>
        </defs>

        {/* Ambient orbital rings */}
        <ellipse
          cx="120"
          cy="120"
          rx="102"
          ry="48"
          transform="rotate(18 120 120)"
          stroke="#FF7AA8"
          strokeWidth="1.2"
          strokeDasharray="5 4"
          opacity="0.35"
        />

        {/* Folder Back Body */}
        <path
          d="M 38 72 C 38 66, 42 62, 48 62 L 82 62 C 88 62, 93 66, 97 71 L 105 80 L 186 80 C 193 80, 198 85, 198 92 L 198 160 C 198 167, 193 172, 186 172 L 48 172 C 41 172, 38 167, 38 160 Z"
          fill="url(#folderBack)"
          stroke="rgba(255, 120, 170, 0.3)"
          strokeWidth="1.5"
        />

        {/* Documents Inside Folder */}
        <g transform="translate(68, 38) rotate(-8)">
          <rect x="0" y="0" width="70" height="90" rx="6" fill="url(#evDoc)" opacity="0.85" />
          <rect x="10" y="14" width="34" height="4" rx="2" fill="#E02875" opacity="0.7" />
          <rect x="10" y="24" width="50" height="3" rx="1.5" fill="#A8557A" opacity="0.35" />
          <rect x="10" y="32" width="46" height="3" rx="1.5" fill="#A8557A" opacity="0.35" />
          <rect x="10" y="40" width="38" height="3" rx="1.5" fill="#A8557A" opacity="0.35" />
        </g>
        <g transform="translate(86, 34) rotate(4)">
          <rect x="0" y="0" width="74" height="95" rx="6" fill="url(#evDoc)" />
          <rect x="12" y="16" width="38" height="4" rx="2" fill="#E02875" opacity="0.8" />
          <rect x="12" y="26" width="50" height="3" rx="1.5" fill="#A8557A" opacity="0.4" />
          <rect x="12" y="34" width="48" height="3" rx="1.5" fill="#A8557A" opacity="0.4" />
          <rect x="12" y="42" width="42" height="3" rx="1.5" fill="#A8557A" opacity="0.4" />
        </g>

        {/* Folder Front Flap (Angled 3D) */}
        <path
          d="M 32 108 C 32 101, 37 96, 44 96 L 192 96 C 199 96, 204 101, 204 108 L 194 168 C 193 174, 187 178, 180 178 L 44 178 C 37 178, 32 173, 31 166 Z"
          fill="url(#folderFront)"
          stroke="#FFA3C5"
          strokeWidth="1.5"
        />

        {/* Small front badge tab */}
        <rect x="46" y="104" width="28" height="6" rx="3" fill="#FFF" opacity="0.4" />

        {/* 3D Magnifying Glass on Folder Front */}
        <g transform="translate(162, 142) rotate(22)">
          {/* Handle */}
          <rect
            x="20"
            y="20"
            width="8"
            height="32"
            rx="4"
            transform="rotate(-45 20 20)"
            fill="#5E062C"
            stroke="#FF94BD"
            strokeWidth="1"
          />
          {/* Outer Lens Rim */}
          <circle cx="0" cy="0" r="26" fill="none" stroke="#FFFFFF" strokeWidth="4" />
          <circle cx="0" cy="0" r="23" fill="url(#evLens)" />
          {/* Glass glare arc */}
          <path
            d="M -15 -8 A 18 18 0 0 1 8 -15"
            stroke="#FFFFFF"
            strokeWidth="2.5"
            strokeLinecap="round"
          />
        </g>

        {/* Decorative sparkle stars */}
        <path d="M 52 46 Q 55 46, 56 43 Q 57 46, 60 46 Q 57 46, 56 49 Q 55 46, 52 46 Z" fill="#FFF" />
        <path d="M 204 82 Q 206 82, 207 80 Q 208 82, 210 82 Q 208 82, 207 84 Q 206 82, 204 82 Z" fill="#FFB3CE" />
      </svg>
    </div>
  );
};

/**
 * Asian Pagoda & Rolling Hills Landscape Silhouette Illustration
 */
export const PagodaLandscapeSilhouette: React.FC<{ className?: string }> = ({
  className = "w-full h-24",
}) => {
  return (
    <div className={`relative overflow-hidden select-none pointer-events-none ${className}`}>
      <svg
        viewBox="0 0 320 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
        preserveAspectRatio="xMidYMax slice"
      >
        <defs>
          <linearGradient id="sunGrad" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#FFA6C5" stopOpacity="0.8" />
            <stop offset="1" stopColor="#E02875" stopOpacity="0.15" />
          </linearGradient>
          <linearGradient id="hillBack" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#550D33" stopOpacity="0.7" />
            <stop offset="1" stopColor="#250316" stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id="hillFront" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#3C0724" />
            <stop offset="1" stopColor="#1C0211" />
          </linearGradient>
        </defs>

        {/* Soft Rising Moon/Sun */}
        <circle cx="85" cy="55" r="28" fill="url(#sunGrad)" />

        {/* Distant Mountain / Hills Ridge */}
        <path
          d="M 0 88 Q 70 70, 140 82 T 280 76 T 320 84 L 320 120 L 0 120 Z"
          fill="url(#hillBack)"
        />

        {/* Pagoda Temple Architecture on Hill */}
        <g transform="translate(42, 38)" fill="#230315">
          {/* Pagoda Spire */}
          <rect x="23" y="0" width="2" height="12" rx="1" fill="#FF8CB5" opacity="0.8" />
          <circle cx="24" cy="2" r="2" fill="#FFA3C5" />

          {/* Roof Tier 1 (Top) */}
          <path d="M 24 10 C 20 12, 14 13, 11 16 L 37 16 C 34 13, 28 12, 24 10 Z" />
          <rect x="21" y="16" width="6" height="5" />

          {/* Roof Tier 2 (Middle) */}
          <path d="M 24 19 C 18 22, 10 23, 6 27 L 42 27 C 38 23, 30 22, 24 19 Z" />
          <rect x="19" y="27" width="10" height="7" />

          {/* Roof Tier 3 (Main Base) */}
          <path d="M 24 32 C 16 35, 6 37, 1 42 L 47 42 C 42 37, 32 35, 24 32 Z" />
          <rect x="16" y="42" width="16" height="12" />

          {/* Temple Base Platform */}
          <rect x="11" y="54" width="26" height="6" rx="2" />
        </g>

        {/* Pine Tree Silhouettes */}
        <g fill="#1F0212">
          {/* Tree 1 */}
          <path d="M 100 70 L 96 76 L 98 76 L 94 83 L 106 83 L 102 76 L 104 76 Z" />
          <rect x="99.5" y="83" width="1.5" height="4" />
          {/* Tree 2 */}
          <path d="M 112 74 L 109 79 L 111 79 L 107 85 L 117 85 L 113 79 L 115 79 Z" />
          <rect x="111.5" y="85" width="1.5" height="3" />
        </g>

        {/* Foreground Rolling Hills */}
        <path
          d="M 0 98 Q 60 88, 120 94 T 240 92 T 320 96 L 320 120 L 0 120 Z"
          fill="url(#hillFront)"
        />
      </svg>
    </div>
  );
};

/**
 * Celestial Astrolabe / Compass Watermark Engraving
 */
export const CelestialCompassWatermark: React.FC<{ className?: string }> = ({
  className = "w-64 h-64",
}) => {
  return (
    <div className={`pointer-events-none select-none opacity-20 ${className}`}>
      <svg
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
      >
        <circle cx="100" cy="100" r="92" stroke="#FF7AA8" strokeWidth="0.75" strokeDasharray="3 3" />
        <circle cx="100" cy="100" r="82" stroke="#FF5C93" strokeWidth="1" />
        <circle cx="100" cy="100" r="62" stroke="#FF7AA8" strokeWidth="0.75" />
        <circle cx="100" cy="100" r="42" stroke="#FF5C93" strokeWidth="0.75" strokeDasharray="4 4" />

        {/* Cardinal Ray Points */}
        <line x1="100" y1="0" x2="100" y2="200" stroke="#FF8CB5" strokeWidth="1" />
        <line x1="0" y1="100" x2="200" y2="100" stroke="#FF8CB5" strokeWidth="1" />
        <line x1="29" y1="29" x2="171" y2="171" stroke="#FF7AA8" strokeWidth="0.75" strokeDasharray="4 2" />
        <line x1="171" y1="29" x2="29" y2="171" stroke="#FF7AA8" strokeWidth="0.75" strokeDasharray="4 2" />

        {/* 8-Point Compass Star in Center */}
        <polygon
          points="100,60 106,94 140,100 106,106 100,140 94,106 60,100 94,94"
          fill="#FF5C93"
          fillOpacity="0.25"
          stroke="#FF8CB5"
          strokeWidth="0.8"
        />
      </svg>
    </div>
  );
};

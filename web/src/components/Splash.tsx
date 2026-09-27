'use client';
import { useEffect, useRef, useState } from 'react';
import { GOLDD } from '@/lib/constants';
import { OrbitGlobe } from './OrbitGlobe';

const MSG = [
  'Preparing the field…',
  'Reading 985,000 plots · 2000–2007',
  'Genotyping 15,968 new lines',
  'Ranking 157 families',
  'Sealing the 2008 answer key',
  'Ready · click anywhere to enter',
];

export function Splash({ onDone }: { onDone: () => void }) {
  const [sp, setSp] = useState(0);
  const spRef = useRef(0);
  spRef.current = sp;

  useEffect(() => {
    const timers = [[250, 1], [1250, 2], [2250, 3], [3050, 4], [3900, 5]].map(([t, p]) => setTimeout(() => setSp(p), t));
    timers.push(setTimeout(onDone, 6400));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleClick() {
    if (spRef.current >= 1) onDone();
  }

  const g1 = sp >= 1, g2 = sp >= 2, g3 = sp >= 3, g4 = sp >= 4;

  return (
    <div onClick={handleClick} className="flex min-h-screen cursor-pointer flex-col items-center justify-center" style={{ background: '#F3EEE2' }}>
      <div className="relative" style={{ width: 320, height: 420 }}>
        <div style={{ position: 'absolute', right: 18, top: 20, width: 74, height: 74, borderRadius: '50%', background: 'oklch(0.86 0.12 85)', opacity: g1 ? 0.9 : 0, transform: g1 ? 'scale(1)' : 'scale(.4)', transition: 'all 1.2s cubic-bezier(.3,1.3,.5,1)' }} />
        <div style={{ position: 'absolute', left: 10, right: 10, bottom: 0, height: 46, borderRadius: '50% 50% 14px 14px / 30% 30% 14px 14px', background: 'oklch(0.55 0.06 60)', transform: g1 ? 'scaleX(1)' : 'scaleX(.2)', transition: 'transform .8s cubic-bezier(.3,1,.4,1)' }} />
        <div style={{ position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', transformOrigin: '160px 400px', animation: g4 ? 'mzSway 4s ease-in-out infinite' : 'none' }}>
          <div style={{ position: 'absolute', left: 154, bottom: 36, width: 12, height: g1 ? 330 : 0, borderRadius: '6px 6px 2px 2px', background: 'oklch(0.56 0.11 135)', transition: 'height 1.5s cubic-bezier(.3,.9,.3,1)' }} />
          {[0, 1, 2, 3, 4, 5].map((k) => {
            const right = k % 2 === 0, L = 128 - k * 9, b = 78 + k * 46, ang = (right ? -1 : 1) * (16 + k * 5);
            return (
              <div key={k} style={{
                position: 'absolute', bottom: b, left: right ? 164 : 156 - L, width: L, height: 22,
                borderRadius: right ? '0 100% 0 100%' : '100% 0 100% 0', background: `oklch(${0.52 + k * 0.035} 0.12 ${132 + k * 2})`,
                transformOrigin: right ? 'left center' : 'right center',
                transform: g2 ? `rotate(${ang}deg) scale(1)` : `rotate(${right ? -80 : 80}deg) scale(0)`,
                transition: `transform .9s cubic-bezier(.3,1.4,.5,1) ${k * 140}ms`,
              }} />
            );
          })}
          {[0, 1, 2, 3, 4, 5, 6].map((j) => (
            <div key={j} style={{
              position: 'absolute', left: 158.5, bottom: 360, width: 3, height: 34 + (3 - Math.abs(j - 3)) * 6,
              borderRadius: 2, background: 'oklch(0.76 0.1 85)', transformOrigin: 'bottom center',
              transform: `rotate(${(j - 3) * 15}deg) scaleY(${g3 ? 1 : 0})`, transition: `transform .6s cubic-bezier(.3,1.4,.5,1) ${j * 50}ms`,
            }} />
          ))}
          <div style={{ position: 'absolute', left: 166, bottom: 196, width: 54, height: 118, transformOrigin: 'bottom left', transform: g3 ? 'rotate(24deg) scale(1)' : 'rotate(24deg) scale(0)', transition: 'transform .9s cubic-bezier(.3,1.4,.5,1)' }}>
            <div style={{ position: 'absolute', left: 8, right: 8, top: 4, bottom: 4, borderRadius: '50% 50% 45% 45% / 42% 42% 58% 58%', background: 'oklch(0.9 0.05 90)', overflow: 'hidden', display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 2, padding: '6px 4px', boxSizing: 'border-box' }}>
              {Array.from({ length: 55 }, (_, i) => {
                const r = Math.floor(i / 5);
                return <div key={i} style={{ borderRadius: '45%', height: 7, background: g4 ? 'oklch(0.78 0.16 76)' : 'oklch(0.9 0.04 90)', boxShadow: 'inset -1px -1px 0 rgba(120,60,0,.2)', transition: `background .4s ease ${(10 - r) * 60}ms` }} />;
              })}
            </div>
            <div style={{ position: 'absolute', left: -2, top: 10, width: 22, height: 112, borderRadius: '100% 0 100% 0', background: 'oklch(0.62 0.12 130)', transformOrigin: 'bottom right', transform: g4 ? 'rotate(-14deg)' : 'rotate(0)', transition: 'transform .8s ease .2s' }} />
            <div style={{ position: 'absolute', right: -2, top: 10, width: 22, height: 112, borderRadius: '0 100% 0 100%', background: 'oklch(0.55 0.12 135)', transformOrigin: 'bottom left', transform: g4 ? 'rotate(14deg)' : 'rotate(0)', transition: 'transform .8s ease .2s' }} />
          </div>
        </div>
      </div>

      <div className="-mt-4 mb-2">
        <OrbitGlobe size={100} visible={g4} />
      </div>

      <div className="flex flex-col items-center gap-3 text-center" style={{ maxWidth: 640, opacity: g4 ? 1 : 0, transform: g4 ? 'none' : 'translateY(14px)', transition: 'all .8s ease' }}>
        <div className="font-mono-data text-xs uppercase tracking-wide" style={{ color: '#4A5C34' }}>Maize Advancement Advisor</div>
        <div className="text-4xl font-extrabold leading-tight">Plant fewer plots.<br />Keep more winners.</div>
        <div className="mt-2 h-px w-40" style={{ background: GOLDD }} />
        <div className="font-mono-data text-sm" style={{ color: '#6B6A5C' }}>
          {sp === 5 ? 'Ready · click anywhere to enter' : MSG[sp]}
        </div>
      </div>

      <div className="mt-6 h-1 w-48 overflow-hidden rounded-full" style={{ background: 'rgba(30,36,24,.12)' }}>
        <div className="h-full" style={{ width: `${(sp / 5) * 100}%`, background: GOLDD, transition: 'width .9s ease' }} />
      </div>
    </div>
  );
}

'use client';
import { GOLD, GOLDD, GREEN } from '@/lib/constants';

/** A small decorative "world" with maize orbiting it — pure CSS/SVG, no 3D
 * dependency. Used as a splash-screen flourish. */
export function OrbitGlobe({ size = 130, visible = true }: { size?: number; visible?: boolean }) {
  const r = size / 2;
  const orbits = [
    { radius: r + 12, duration: 7, reverse: false, delay: 0, emoji: '🌽', scale: 1 },
    { radius: r + 22, duration: 11, reverse: true, delay: -3, emoji: '🌽', scale: 0.75 },
  ];

  return (
    <div
      className="relative"
      style={{ width: size, height: size, opacity: visible ? 1 : 0, transform: visible ? 'scale(1)' : 'scale(.7)', transition: 'all 1s cubic-bezier(.3,1.2,.4,1)' }}
    >
      {/* the globe */}
      <div
        className="absolute inset-0 overflow-hidden rounded-full"
        style={{
          background: `radial-gradient(circle at 32% 28%, ${GOLD} 0%, ${GREEN} 55%, #2b3a20 100%)`,
          boxShadow: `0 0 0 1px rgba(30,36,24,.15), inset -8px -10px 24px rgba(0,0,0,.25)`,
        }}
      >
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'repeating-linear-gradient(100deg, rgba(255,255,255,.16) 0px, rgba(255,255,255,.16) 2px, transparent 2px, transparent 22px)',
            animation: 'mzGlobeSpin 9s linear infinite',
          }}
        />
      </div>

      {/* orbiting maize */}
      {orbits.map((o, i) => (
        <div
          key={i}
          className="absolute inset-0"
          style={{
            animation: `${o.reverse ? 'mzOrbitCounterSpin' : 'mzOrbitSpin'} ${o.duration}s linear infinite`,
            animationDelay: `${o.delay}s`,
          }}
        >
          <div
            className="absolute left-1/2 top-1/2"
            style={{ transform: `translate(-50%,-50%) translateX(${o.radius}px)`, fontSize: 20 * o.scale }}
          >
            <div style={{ animation: `${o.reverse ? 'mzOrbitSpin' : 'mzOrbitCounterSpin'} ${o.duration}s linear infinite`, animationDelay: `${o.delay}s` }}>
              {o.emoji}
            </div>
          </div>
        </div>
      ))}

      {/* faint orbit rings for readability */}
      {orbits.map((o, i) => (
        <div
          key={'ring' + i}
          className="absolute rounded-full"
          style={{
            left: '50%', top: '50%', width: o.radius * 2, height: o.radius * 2,
            transform: 'translate(-50%,-50%)', border: `1px solid ${GOLDD}`, opacity: 0.15, pointerEvents: 'none',
          }}
        />
      ))}

      {/* soft ambient glow so the globe reads as floating, not detached */}
      <div
        className="absolute rounded-full"
        style={{
          left: '50%', top: '50%', width: size * 1.9, height: size * 1.9, transform: 'translate(-50%,-50%)',
          background: `radial-gradient(circle, rgba(30,36,24,.06) 0%, transparent 70%)`, pointerEvents: 'none', zIndex: -1,
        }}
      />
    </div>
  );
}

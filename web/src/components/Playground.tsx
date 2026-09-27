'use client';
import { useRef, useState } from 'react';
import { GOLD, INK } from '@/lib/constants';
import { hash } from '@/lib/format';

interface Plant {
  id: number;
  x: number;
  y: number;
  gs: number;      // 0-4 grow stage
  seed: number;      // 0..1, drives height/hue/star variety
}

const MAX_PLANTS = 80;
const STAGE_MS = 260; // snappy — this is a toy, not the real sim

export function Playground({ onBack }: { onBack: () => void }) {
  const [plants, setPlants] = useState<Plant[]>([]);
  const [planted, setPlanted] = useState(0);
  const nextId = useRef(1);
  const areaRef = useRef<HTMLDivElement>(null);

  function plantAt(clientX: number, clientY: number) {
    const rect = areaRef.current?.getBoundingClientRect();
    if (!rect) return;
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    const id = nextId.current++;
    const seed = hash(id);
    setPlants((p) => {
      const next = [...p, { id, x, y, gs: 0, seed }];
      return next.length > MAX_PLANTS ? next.slice(next.length - MAX_PLANTS) : next;
    });
    setPlanted((n) => n + 1);
    [1, 2, 3, 4].forEach((stage) => {
      setTimeout(() => {
        setPlants((p) => p.map((pl) => (pl.id === id ? { ...pl, gs: stage } : pl)));
      }, stage * STAGE_MS);
    });
  }

  return (
    <div className="flex min-h-screen flex-col" style={{ background: 'linear-gradient(#F3EEE2 0%, #F3EEE2 55%, #C9A876 55%, #B8935F 100%)' }}>
      <header className="flex items-center justify-between px-6 py-4">
        <button onClick={onBack} className="font-mono-data text-sm font-semibold" style={{ color: '#6B6A5C' }}>← Back</button>
        <div className="text-center">
          <div className="font-mono-data text-xs uppercase tracking-wide" style={{ color: '#4A5C34' }}>just for fun</div>
          <div className="text-lg font-bold">Click anywhere to plant a field</div>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono-data text-sm" style={{ color: '#6B6A5C' }}>{planted} planted</span>
          <button
            onClick={() => setPlants([])}
            className="rounded-full px-3 py-1.5 font-mono-data text-xs font-bold"
            style={{ background: INK, color: '#F3EEE2' }}
          >
            Clear field
          </button>
        </div>
      </header>

      <div
        ref={areaRef}
        onClick={(e) => plantAt(e.clientX, e.clientY)}
        className="relative flex-1 cursor-crosshair select-none overflow-hidden"
      >
        {plants.length === 0 && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center font-mono-data text-sm" style={{ color: 'rgba(30,36,24,.35)' }}>
            click anywhere below the fold line
          </div>
        )}
        {plants.map((p) => <ToyPlant key={p.id} {...p} />)}
      </div>
    </div>
  );
}

function ToyPlant({ x, y, gs, seed }: Plant) {
  const H = 70 + seed * 70;
  const hueShift = (seed - 0.5) * 30;
  const star = gs === 4 && seed > 0.82;
  const sway = 2.4 + seed * 2;

  return (
    <div style={{ position: 'absolute', left: x, top: y, width: 0, height: 0, zIndex: Math.round(y) }}>
      <div style={{ position: 'absolute', left: -14, top: -5, width: 28, height: 10, borderRadius: '50%', background: 'oklch(0.56 0.07 55)' }} />
      <div style={{ animation: `mzSway ${sway}s ease-in-out infinite`, transformOrigin: '0 0' }}>
        <div
          style={{
            position: 'absolute', bottom: 0, left: -3, width: 6,
            height: gs === 0 ? 0 : H * [0, .3, .7, 1, 1][gs],
            borderRadius: '3px 3px 1px 1px', background: `oklch(0.54 0.12 ${135 + hueShift})`,
            transition: 'height .4s cubic-bezier(.3,1.1,.4,1)',
          }}
        />
        {[.18, .38, .58].map((fr, j) => {
          const right = j % 2 === 0, L = [30, 26, 20][j];
          const on = gs >= j + 1;
          return (
            <div
              key={j}
              style={{
                position: 'absolute', bottom: H * fr, left: right ? 2 : -2 - L, width: L, height: 8,
                borderRadius: right ? '0 100% 0 100%' : '100% 0 100% 0',
                background: `oklch(${0.55 + j * 0.04} 0.12 ${137 + hueShift + j * 2})`,
                transformOrigin: right ? 'left center' : 'right center',
                transform: `rotate(${(right ? -1 : 1) * (18 + j * 6)}deg) scale(${on ? 1 : 0})`,
                transition: `transform .35s cubic-bezier(.3,1.5,.5,1) ${j * 70}ms`,
              }}
            />
          );
        })}
        <div
          style={{
            position: 'absolute', bottom: H * .4, left: 3, width: 9, height: 20, borderRadius: '50% 50% 45% 45%',
            background: gs >= 3 ? GOLD : 'oklch(0.9 0.06 100)',
            transformOrigin: 'bottom left', transform: `rotate(22deg) scale(${gs >= 3 ? 1 : 0})`,
            transition: 'transform .4s cubic-bezier(.3,1.5,.5,1)',
          }}
        />
        <div
          style={{
            position: 'absolute', left: -11, bottom: H + 20, width: 20, height: 20, borderRadius: '50%',
            background: INK, color: GOLD, fontSize: 12, lineHeight: '20px', textAlign: 'center', fontWeight: 700,
            transform: `scale(${star ? 1 : 0})`, transition: 'transform .4s cubic-bezier(.3,1.8,.5,1) .3s',
            boxShadow: '0 2px 6px rgba(0,0,0,.25)',
          }}
        >
          ★
        </div>
      </div>
    </div>
  );
}

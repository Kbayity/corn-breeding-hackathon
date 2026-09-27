'use client';
import { pos } from '@/lib/geometry';
import { NK, GOLD } from '@/lib/constants';

/** Story step 1: a static DNA-helix sample of the 15,968 lines by family. */
export function DnaHelix() {
  const dots = Array.from({ length: NK }, (_, i) => {
    const p = pos(i, 'helix');
    const dim = 1 - p.z;
    const bg = p.s ? `oklch(${0.8 - 0.14 * dim} 0.15 78)` : `oklch(${0.58 - 0.12 * dim} 0.11 140)`;
    const op = 0.45 + 0.55 * p.z;
    return (
      <div
        key={i}
        style={{
          position: 'absolute', left: -10, top: -10, width: 20, height: 20, borderRadius: '50%',
          background: bg, opacity: op,
          transform: `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) scale(${(p.w / 20).toFixed(3)},${(p.h / 20).toFixed(3)})`,
        }}
      />
    );
  });

  return (
    <div className="w-full max-w-[440px]">
      <div className="relative overflow-hidden rounded-2xl" style={{ width: 440, height: 540, background: '#F7F2E7', border: '1px solid rgba(30,36,24,.08)' }}>
        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>
          <span className="h-2 w-2 rounded-full" style={{ background: GOLD }} />
          Line genotypes
        </div>
        {dots}
      </div>
      <div className="mt-3 text-sm" style={{ color: '#6B6A5C' }}>320 dots sample the 15,968 lines by family.</div>
    </div>
  );
}

'use client';
import { CSSProperties, useMemo, useState } from 'react';
import { pos, Layout } from '@/lib/geometry';
import { hash, sgn } from '@/lib/format';
import { NK, GOLD, GOLDD, INK } from '@/lib/constants';
import type { Prepped, PlanResult } from '@/lib/types';
import type { SourceToggles } from '@/lib/plan';

export type ColorMode = 'plan' | 'strand' | 'neutral' | 'allgreen';
export type View = 'grow' | 'field' | 'cob';

interface Props {
  D: Prepped;
  P: PlanResult | null;
  layout: Layout;
  colorMode: ColorMode;
  src: SourceToggles;
  tech?: boolean;      // pinned-kernel mode (Geneticist tab)
  pin?: number | null;
  hov?: number | null;                    // controlled hover (lifted so panels can show a "why this line" inspector)
  onHoverChange?: (i: number | null) => void;
  gs?: number;           // grow stage 0-4 (only used when layout==='grow')
  playing?: boolean;
  onStageClick?: (k: number) => void;
  onPlayToggle?: () => void;
  onKernelClick?: (i: number) => void;
}

const STG = ['Planting', 'Emergence', 'V10', 'Tassel', 'Harvest'];

export function FieldScene({ D, P, layout, colorMode, src, tech, pin, hov: hovProp, onHoverChange, gs = 4, playing, onStageClick, onPlayToggle, onKernelClick }: Props) {
  const [hovLocal, setHovLocal] = useState<number | null>(null);
  const hov = onHoverChange ? (hovProp ?? null) : hovLocal;
  const setHov = onHoverChange ?? setHovLocal;

  const kernels = useMemo(() => {
    const out: { i: number; st: CSSProperties }[] = [];
    for (let i = 0; i < NK; i++) {
      const p = pos(i, layout);
      const row = Math.floor(i / 16);
      const lit = P ? !!P.klit[i] : (colorMode === 'plan' && hash(i) < 0.15);
      const z = p.z, dim = 1 - z;
      let bg: string, sh = 'none', op = 1;
      if (colorMode === 'strand') { bg = p.s ? `oklch(${0.8 - 0.14 * dim} 0.15 78)` : `oklch(${0.58 - 0.12 * dim} 0.11 140)`; op = 0.45 + 0.55 * z; }
      else if (colorMode === 'neutral') { bg = `oklch(${0.84 - 0.16 * dim} 0.13 84)`; sh = 'inset -1px -2px 0 rgba(90,60,0,.14)'; }
      else if (colorMode === 'allgreen') { bg = `oklch(${0.62 - 0.1 * dim} 0.12 135)`; }
      else if (layout === 'cob') { bg = lit ? `oklch(${0.78 - 0.14 * dim} 0.17 72)` : `oklch(${0.9 - 0.08 * dim} 0.045 88)`; sh = lit ? 'inset -2px -3px 0 rgba(120,60,0,.25)' : 'inset -2px -3px 0 rgba(90,60,0,.08)'; }
      else { bg = lit ? `oklch(${0.6 - 0.08 * dim} 0.13 135)` : `oklch(${0.87 - 0.04 * dim} 0.03 75)`; sh = lit ? 'inset 0 -2px 0 rgba(0,40,0,.18)' : 'none'; }
      const sel = hov === i || (tech && pin === i);
      out.push({
        i,
        st: {
          position: 'absolute', left: -10, top: -10, width: 20, height: 20, borderRadius: p.r,
          background: bg, opacity: layout === 'grow' ? 0 : op, pointerEvents: layout === 'grow' ? 'none' : 'auto',
          boxShadow: sel ? `0 0 0 3px ${INK}` : sh, zIndex: Math.round(z * 10) + (sel ? 20 : 0), cursor: 'pointer',
          transform: `translate(${p.x.toFixed(1)}px,${p.y.toFixed(1)}px) scale(${(p.w / 20).toFixed(3)},${(p.h / 20).toFixed(3)})`,
          transition: `transform 1.1s cubic-bezier(.7,0,.2,1) ${Math.round(i * 2.2)}ms, background-color .5s ease ${row * 22}ms`,
        },
      });
    }
    return out;
  }, [layout, colorMode, P, hov, tech, pin]);

  const growOn = layout === 'grow';
  const ROWS = 8, COLS = 7;
  const rowY = (r: number) => 512 - r * 50 + r * r * 2;
  const rowS = (r: number) => 1 - r * 0.08;

  const { plants, plantPos, litCount, harvestText } = useMemo(() => {
    if (!growOn) return { plants: [] as ReturnType<typeof buildPlant>[], plantPos: {} as Record<number, { x: number; y: number }>, litCount: 0, harvestText: '' };
    const litK: number[] = [];
    for (let i = 0; i < NK; i++) if (P ? P.klit[i] : hash(i) < 0.15) litK.push(i);
    const nSlots = ROWS * COLS;
    const shown = litK.slice(0, nSlots);
    const pv = shown.map((i) => {
      if (!P) return hash(i);
      const L = P.kline[i], c = D.c;
      return P.Ff[c.f[L]] + (src.ldna ? c.d[L] : 0) + (src.tester ? c.t[L] : 0);
    });
    const mn = Math.min(...pv, 0), mx = Math.max(...pv, 1);
    const adv = new Set(shown.map((i, k) => [pv[k], i] as const).sort((a, b) => b[0] - a[0]).slice(0, Math.max(1, Math.round(shown.length * 0.05))).map((x) => x[1]));
    const pPos: Record<number, { x: number; y: number }> = {};
    const built = Array.from({ length: nSlots }, (_, k) => {
      const r = Math.floor(k / COLS), c = k % COLS, s = rowS(r), x = 220 + (c - 3) * 58 * s, y = rowY(r);
      const ki = shown[k], has = ki !== undefined;
      const n = has ? (pv[k] - mn) / ((mx - mn) || 1) : 0;
      const H = 150 * (0.78 + 0.45 * n);
      if (has) pPos[ki] = { x, y: y - H * s * 0.7 };
      return buildPlant({ r, c, s, x, y, ki, has, H, gs, adv });
    });
    return { plants: built, plantPos: pPos, litCount: litK.length, harvestText: `★ ${adv.size} lines advance · top 5% at harvest` };
  }, [growOn, P, D, src, gs]);

  const hoverInfo = useMemo(() => {
    if (hov == null || !P) return null;
    const i = P.kline[hov], c = D.c;
    const fam = D.fams[c.f[i]];
    const tc = P.Ff[c.f[i]] + (src.ldna ? c.d[i] : 0) + (src.tester ? c.t[i] : 0);
    const on = !!P.plant[i];
    const sibIdx = D.byD[c.f[i]].indexOf(i) + 1;
    const p = (layout === 'grow' && plantPos[hov]) || pos(hov, layout);
    return {
      key: 'Family ' + fam.pop,
      sib: `sibling #${sibIdx} of ${D.fl[c.f[i]].length}`,
      tier: (['low', 'medium', 'high'] as const)[c.tier[i]],
      tc: sgn(tc) + ' bu/ac',
      status: on ? '● PLANTED' : '○ not planted',
      col: on ? GOLD : '#B9B4A4',
      x: p.x, y: p.y,
    };
  }, [hov, P, D, src, layout, plantPos]);

  const stageTag = growOn
    ? 'Your field · ' + ['planting', 'emergence', 'V10', 'tassel & silk', 'harvest'][gs]
    : layout === 'cob' ? (colorMode === 'plan' ? 'Planted lines light up' : '2008 candidate lines')
    : colorMode === 'plan' ? 'Field plots · planted' : 'Field plots · plant everything';

  const more = Math.max(0, litCount - ROWS * COLS);
  const stageCaption = growOn
    ? `${Math.min(litCount, ROWS * COLS)} plants in view · each ≈ 50 lines · taller = higher predicted yield${more ? ` · +${more} more rows beyond the field` : ''}. Hover a plant.`
    : layout === 'cob' ? 'Each kernel ≈ 50 lines. Rows ordered by predicted family value, best at the tip. Hover a kernel.'
    : 'Each plot ≈ 50 lines. Best families at the back, weakest at the front.';

  return (
    <div className="w-full max-w-[440px]">
      <div className="relative overflow-hidden rounded-2xl" style={{ width: 440, height: 540, background: '#F7F2E7', border: '1px solid rgba(30,36,24,.08)' }}>
        <div className="absolute left-4 top-4 z-10 flex items-center gap-2 font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>
          <span className="h-2 w-2 rounded-full" style={{ background: GOLD }} />
          {stageTag}
        </div>

        {growOn && (
          <div className="absolute inset-0" style={{ opacity: 1, zIndex: 5 }}>
            <div style={{ position: 'absolute', left: -60, right: -60, top: 205, height: 80, borderRadius: '50%', background: gs === 4 ? 'oklch(0.84 0.07 90)' : 'oklch(0.86 0.06 130)', transition: 'background 1s' }} />
            <div style={{ position: 'absolute', left: 0, right: 0, top: 236, bottom: 0, background: 'oklch(0.74 0.06 65)' }} />
            {Array.from({ length: ROWS }, (_, r) => {
              const s = rowS(r), w = COLS * 58 * s + 30;
              return <div key={r} style={{ position: 'absolute', left: 220 - w / 2, top: rowY(r) - 6 * s, width: w, height: 12 * s, borderRadius: '50%', background: 'oklch(0.62 0.07 55)' }} />;
            })}
            {plants.map((pl, k) => <PlantView key={k} {...pl} />)}
            <div style={{ position: 'absolute', left: '50%', top: 44, transform: `translateX(-50%) translateY(${gs === 4 ? 0 : -60}px)`, padding: '8px 14px', borderRadius: 999, background: INK, color: '#F3EEE2', fontSize: 12, fontWeight: 600, whiteSpace: 'nowrap', transition: 'transform .6s cubic-bezier(.3,1.4,.5,1) 1.2s', zIndex: 200 }}>
              {harvestText}
            </div>
          </div>
        )}

        {!growOn && kernels.map(({ i, st }) => (
          <div key={i} style={st} onMouseEnter={() => setHov(i)} onMouseLeave={() => hov === i && setHov(null)} onClick={() => onKernelClick?.(i)} />
        ))}

        {hoverInfo && (
          <div style={{
            position: 'absolute', left: Math.min(440 - 196, Math.max(8, hoverInfo.x + 14)), top: Math.min(540 - 110, Math.max(8, hoverInfo.y - 40)),
            width: 180, padding: '10px 12px', borderRadius: 10, background: INK, color: '#F3EEE2', zIndex: 50, pointerEvents: 'none', boxShadow: '0 8px 24px rgba(0,0,0,.25)',
          }}>
            <div className="text-sm font-semibold">{hoverInfo.key}</div>
            <div className="text-xs opacity-80">{hoverInfo.sib} · {hoverInfo.tier} confidence</div>
            <div className="mt-1 font-mono-data font-bold">{hoverInfo.tc}</div>
            <div className="text-xs" style={{ color: hoverInfo.col }}>{hoverInfo.status}</div>
          </div>
        )}
      </div>

      <div className="mt-3 text-sm" style={{ color: '#6B6A5C' }}>{stageCaption}</div>

      {growOn && (
        <div className="mt-3 flex items-center gap-3">
          <button onClick={onPlayToggle} aria-label={playing ? 'Pause' : 'Play'} style={{ all: 'unset', cursor: 'pointer', width: 32, height: 32, borderRadius: '50%', background: INK, color: '#F3EEE2', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12 }}>
            {playing ? '❚❚' : '▶'}
          </button>
          <div className="flex-1 flex gap-3">
            {STG.map((label, k) => (
              <button key={label} onClick={() => onStageClick?.(k)} style={{ all: 'unset', cursor: 'pointer', flex: 1, textAlign: 'center' }}>
                <span style={{ display: 'block', height: 3, borderRadius: 2, marginBottom: 6, background: k <= gs ? GOLDD : '#DCD3BF', transition: 'background .4s' }} />
                <span className="font-mono-data" style={{ fontSize: 11, fontWeight: k === gs ? 700 : 500, color: k === gs ? INK : '#6B6A5C' }}>{label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function buildPlant({ r, c, s, x, y, ki, has, H, gs, adv }: { r: number; c: number; s: number; x: number; y: number; ki: number | undefined; has: boolean; H: number; gs: number; adv: Set<number> }) {
  const d = (r * 7 + c) * 16;
  const sh = [0, .28, .74, 1, 1][gs];
  const leafOn = [[0, 0, 0, 0], [.55, .45, 0, 0], [1, 1, 1, .9], [1, 1, 1, 1], [1, 1, 1, 1]][gs];
  const tan = gs === 4;
  const lc = (j: number) => (tan ? `oklch(${0.72 + j * 0.02} 0.09 ${80 + j * 3})` : `oklch(${0.52 + j * 0.04} 0.13 ${136 + j * 2})`);
  const parts = [.16, .32, .48, .64].map((fr, j) => {
    const right = j % 2 === 0, L = [36, 33, 29, 23][j];
    return {
      position: 'absolute' as const, bottom: H * fr, left: right ? 2 : -2 - L, width: L, height: 9,
      borderRadius: right ? '0 100% 0 100%' : '100% 0 100% 0', background: lc(j), transformOrigin: right ? 'left center' : 'right center',
      transform: `rotate(${(right ? -1 : 1) * (20 + j * 6)}deg) scale(${leafOn[j]})`,
      transition: `transform .8s cubic-bezier(.3,1.5,.5,1) ${d + j * 90}ms, background 1s ease ${d}ms`,
    };
  });
  const star = has && ki !== undefined && adv.has(ki);
  return {
    x, y, s, has, wrapZ: 100 - r * 10, d,
    mound: { position: 'absolute' as const, left: -14, top: -5, width: 28, height: 10, borderRadius: '50%', background: 'oklch(0.56 0.07 55)' },
    stalk: { position: 'absolute' as const, bottom: 0, left: -3, width: 6, height: H * sh, borderRadius: '3px 3px 1px 1px', background: tan ? 'oklch(0.7 0.08 82)' : 'oklch(0.54 0.12 135)', transition: `height .9s cubic-bezier(.3,.9,.3,1) ${d}ms, background 1s ease ${d}ms` },
    parts,
    cob: { position: 'absolute' as const, bottom: H * .42, left: 3, width: 10, height: 24, borderRadius: '50% 50% 45% 45%', background: tan ? 'oklch(0.78 0.16 74)' : 'oklch(0.9 0.06 100)', borderLeft: `3px solid ${tan ? 'oklch(0.68 0.09 82)' : 'oklch(0.6 0.13 132)'}`, boxShadow: tan ? '0 0 10px oklch(0.8 0.16 76 / .7)' : 'none', transformOrigin: 'bottom left', transform: `rotate(22deg) scale(${[0, 0, 0, .75, 1][gs]})`, transition: `transform .7s cubic-bezier(.3,1.5,.5,1) ${d + 300}ms, background .8s ease ${d}ms` },
    star: { position: 'absolute' as const, left: -11, bottom: H + 24, width: 22, height: 22, borderRadius: '50%', background: INK, color: GOLD, fontWeight: 700, fontSize: 13, lineHeight: '22px', textAlign: 'center' as const, transform: `scale(${gs === 4 && star ? 1 : 0})`, transition: `transform .5s cubic-bezier(.3,1.8,.5,1) ${gs === 4 ? 700 + d : 0}ms`, boxShadow: '0 2px 8px rgba(0,0,0,.25)' },
    swayDur: (3 + hash(ki ?? 0) * 2).toFixed(2), swayDelay: (-hash((ki ?? 0) + 9) * 3).toFixed(2),
  };
}

function PlantView(p: ReturnType<typeof buildPlant>) {
  return (
    <div style={{ position: 'absolute', left: p.x, top: p.y, width: 0, height: 0, zIndex: p.wrapZ, transform: `scale(${p.has ? p.s : 0})`, transformOrigin: '0 0', transition: `transform .6s cubic-bezier(.3,1.5,.5,1) ${p.has ? p.d : 0}ms`, cursor: 'pointer' }}>
      <div style={p.mound} />
      <div style={{ position: 'absolute', left: 0, top: 0, width: 0, height: 0, transformOrigin: '0 0', animation: `mzSway ${p.swayDur}s ease-in-out ${p.swayDelay}s infinite` }}>
        <div style={p.stalk} />
        {p.parts.map((st, j) => <div key={j} style={st} />)}
        <div style={p.cob} />
        <div style={p.star}>★</div>
      </div>
    </div>
  );
}

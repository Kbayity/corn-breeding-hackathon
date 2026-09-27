'use client';
import { useEffect, useState } from 'react';
import { fmt } from '@/lib/format';
import { YEARS, POST, GOLD, GOLDD, GREEN, RUST, INK } from '@/lib/constants';
import type { Prepped, PlanResult } from '@/lib/types';
import { FieldScene } from './FieldScene';
import { DnaHelix } from './DnaHelix';
import { useTween } from '@/lib/useTween';

const STEPS = [
  {
    tag: '01 · THE INPUT', title: 'A 2008 line arrives as nothing but DNA.',
    desc: 'New families, hundreds of offspring each, and no field record yet — only markers, the two parent inbreds and a tester. Can that alone say which lines will yield best?',
    stats: [['15,968', 'new lines'], ['157', 'families (2 clusters)'], ['2,911', 'parent SNP markers']] as [string, string][],
  },
  {
    tag: '02 · THE HISTORY', title: 'Before DNA, the model already knows 8 seasons.',
    desc: 'Every earlier trial season feeds the pedigree model — which families a parent came from, and how those families performed. The 2008 candidates arrive into a field that already has a track record.',
    stats: null,
  },
  {
    tag: '03 · THE BASELINE', title: 'Planting every candidate costs $13.09M.',
    desc: "At $150 a plot, testing all 15,968 lines across every location is the expensive default. That's the number the decision has to beat.",
    stats: null,
  },
  {
    tag: '04 · THE DECISION', title: 'Family value + own DNA decide what gets planted.',
    desc: 'Keep every good family, tilt plots toward the best-predicted ones, and fill each family’s quota with its best-DNA siblings. The field fills in — starred plants are the ones that advance.',
    stats: null,
  },
  {
    tag: '05 · THE HARVEST', title: 'Was the sealed decision worth it?',
    desc: 'The 2008 yields were sealed until the list was final, then opened once. Reveal them to compare the plan against planting everything, the traditional parents’ record, and random chance.',
    stats: null,
  },
];

export function StoryPanel({ D, P, onExit }: { D: Prepped; P: PlanResult | null; onExit: () => void }) {
  const [step, setStep] = useState(0);
  const [sealed, setSealed] = useState(true);
  const [grown, setGrown] = useState(false);
  const [gs, setGs] = useState(0);
  const tw = useTween();

  useEffect(() => {
    if (step === 3) {
      setGs(0);
      const timers = [1, 2, 3, 4].map((s) => setTimeout(() => setGs(s), 350 + s * 1300));
      return () => timers.forEach(clearTimeout);
    }
  }, [step]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step]);

  function go(dir: number) {
    const s = step + dir;
    if (s > 4) { onExit(); return; }
    if (s < 0) return;
    setStep(s);
  }

  const layout = (['helix', 'cob', 'field', 'grow', 'cob'] as const)[step];
  const colorMode = (['strand', 'neutral', 'allgreen', 'plan', 'plan'] as const)[step];
  const ymax = 223.1;
  const costNow = '$' + tw('cost', step === 2 ? 13.09 : 0, 0).toFixed(1) + 'M';
  const pickLines = fmt(tw('pl', step === 3 ? 2395 : 0, 0));
  const pickPlots = fmt(tw('pp', step === 3 ? 74361 : 0, 0));
  const pickCost = '$' + tw('pc', step === 3 ? 11.2 : 0, 0).toFixed(1) + 'M';

  const RB: [string, number, string][] = [
    ['Our plan · 15% of plots', POST.tilt, GOLDD],
    ['Plant everything', POST.all, INK],
    ["Parents' record", POST.parent, RUST],
    ['Random 15%', POST.random, '#8C8A7C'],
  ];

  const s = STEPS[step];

  return (
    <div className="grid gap-10 lg:grid-cols-[440px_1fr]">
      {layout === 'helix' ? (
        <DnaHelix />
      ) : (
        <FieldScene D={D} P={P} layout={layout} colorMode={colorMode} src={{ history: true, pdna: true, ldna: true, tester: true }} gs={gs} />
      )}

      <div className="flex flex-col gap-6">
        <div className="flex gap-2">
          {[0, 1, 2, 3, 4].map((k) => (
            <button
              key={k} onClick={() => setStep(k)}
              className="rounded-lg border px-2.5 py-1.5 font-mono-data text-xs font-semibold"
              style={{ background: k === step ? INK : k < step ? '#DDD5C3' : 'transparent', color: k === step ? '#F3EEE2' : INK, borderColor: 'rgba(30,36,24,.2)' }}
            >
              0{k + 1}
            </button>
          ))}
        </div>

        <div>
          <div className="font-mono-data text-xs uppercase" style={{ color: GREEN }}>{s.tag}</div>
          <h1 className="mt-1 text-4xl font-extrabold leading-tight">{s.title}</h1>
          <p className="mt-3 max-w-xl text-sm" style={{ color: '#6B6A5C' }}>{s.desc}</p>
        </div>

        {s.stats && (
          <div className="grid grid-cols-3 gap-4">
            {s.stats.map(([v, l]) => (
              <div key={l} className="rounded-2xl p-4" style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}>
                <div className="font-mono-data text-2xl font-bold">{v}</div>
                <div className="text-sm" style={{ color: '#6B6A5C' }}>{l}</div>
              </div>
            ))}
          </div>
        )}

        {step === 1 && (
          <div className="rounded-2xl p-4" style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}>
            <div className="mb-2 text-sm font-semibold">Trial plots recorded per season</div>
            <div className="flex items-end gap-3" style={{ height: 110 }}>
              {YEARS.map(([yr, k], j) => (
                <div key={yr} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t transition-[height] duration-700" style={{ height: `${(k / ymax) * 110}px`, background: j === 7 ? GREEN : GOLD, transitionDelay: `${j * 70}ms` }} />
                  <div className="font-mono-data text-xs">&apos;{String(yr).slice(2)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="rounded-2xl p-6" style={{ background: INK, color: '#F3EEE2' }}>
            <div className="text-sm opacity-70">Cost to plant every candidate</div>
            <div className="font-mono-data text-5xl font-bold">{costNow}</div>
          </div>
        )}

        {step === 3 && (
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-2xl p-4" style={{ background: GREEN, color: '#FBF8F1' }}>
              <div className="text-xs opacity-80">Lines to plant</div>
              <div className="font-mono-data text-2xl font-bold">{pickLines}</div>
            </div>
            <div className="rounded-2xl p-4" style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}>
              <div className="text-xs" style={{ color: '#6B6A5C' }}>Plots saved</div>
              <div className="font-mono-data text-2xl font-bold">{pickPlots}</div>
            </div>
            <div className="rounded-2xl p-4" style={{ background: GOLD, color: INK }}>
              <div className="text-xs opacity-80">Cost saved</div>
              <div className="font-mono-data text-2xl font-bold">{pickCost}</div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="rounded-2xl p-6" style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}>
            <div className="mb-4 flex items-center justify-between">
              <div className="font-semibold">2008 field replay</div>
              <button
                onClick={() => { setSealed(!sealed); if (sealed) setTimeout(() => setGrown(true), 60); }}
                className="rounded-full px-4 py-2 font-mono-data text-sm font-bold"
                style={{ background: GOLD, color: INK }}
              >
                {sealed ? 'Reveal 2008' : 'Seal again'}
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {RB.map(([label, v, color], j) => (
                <div key={label} className="flex items-center gap-3 text-sm">
                  <div className="w-44 shrink-0">{label}</div>
                  <div className="h-3 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                    <div className="h-full rounded transition-[width] duration-700" style={{ width: `${grown ? v / 6 * 100 : 0}%`, background: color, transitionDelay: `${j * 180}ms` }} />
                  </div>
                  <div className="w-12 shrink-0 text-right font-mono-data font-bold">{v.toFixed(2)}</div>
                </div>
              ))}
            </div>
            {grown && (
              <div className="mt-4 border-t pt-3 text-sm" style={{ borderColor: 'rgba(30,36,24,.1)' }}>
                This was one season, scored once. The same pipeline runs again for 2027 crosses today, and for every season after — 17 minutes from raw data, 9 seconds in judge mode.
              </div>
            )}
          </div>
        )}

        <div className="mt-2 flex gap-3">
          <button onClick={() => go(-1)} disabled={step === 0} className="rounded-full px-4 py-2 font-mono-data text-sm font-semibold disabled:opacity-30" style={{ border: '1px solid rgba(30,36,24,.2)' }}>← Back</button>
          <button onClick={() => go(1)} className="rounded-full px-4 py-2 font-mono-data text-sm font-bold" style={{ background: INK, color: '#F3EEE2' }}>
            {step === 4 ? 'Choose your view →' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
}

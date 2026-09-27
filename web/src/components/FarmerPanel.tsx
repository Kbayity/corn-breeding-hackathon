'use client';
import { interp, fmt, sgn } from '@/lib/format';
import { CURVE, PPL, GREEN, GOLD, GOLDD, STRATS } from '@/lib/constants';
import type { Prepped, PlanResult } from '@/lib/types';
import type { AppState } from '@/lib/appState';
import { FieldScene } from './FieldScene';
import { Pill, StatCard, Eyebrow, SectionCard } from './atoms';

interface Props {
  D: Prepped;
  P: PlanResult | null;
  state: AppState;
  update: (patch: Partial<AppState>) => void;
}

export function FarmerPanel({ D, P, state, update }: Props) {
  const noGen = !state.src.history && !state.src.pdna && !state.src.ldna;
  const curveKey = noGen ? 'random' : !state.src.ldna ? 'parent' : state.strat;
  const b = state.budget / 100;
  const cv = CURVE[curveKey];
  const gain = interp(cv.g, b);
  const lines = P ? P.lines : Math.round(b * 15968);
  const plotsUsed = lines * PPL;
  const saved = 87286 - plotsUsed;
  const vsAll = (gain / 4.464 - 1) * 100;

  const farmStats = [
    { label: 'Lines to plant', v: fmt(lines), sub: 'of 15,968 candidates', bg: GREEN, color: '#FBF8F1' },
    { label: 'Genetic gain', v: gain.toFixed(2), sub: `bu/ac · ${vsAll >= 0 ? '+' : ''}${vsAll.toFixed(0)}% vs planting everything`, bg: GOLD, color: '#1E2418' },
    { label: 'Plots saved', v: fmt(saved), sub: `${(saved / 87286 * 100).toFixed(0)}% of the field budget`, bg: '#FBF8F1', color: '#1E2418' },
    { label: 'Plot cost saved', v: '$' + (saved * 150 / 1e6).toFixed(1) + 'M', sub: 'at $150 per plot (assumed)', bg: '#FBF8F1', color: '#1E2418' },
  ];

  const steps = [
    { n: 1, t: `Plant the ${fmt(lines)} recommended lines`, d: P ? `Drawn from ${P.fams} of 157 families. ${state.strat === 'top' ? 'Only the top-predicted lines — weaker families get none.' : 'Every good family keeps some plots; better-predicted families get more.'}` : '' },
    { n: 2, t: 'Test each planted line at every location', d: 'Extra locations are worth more than extra lines — about 1.8× the gain at equal cost.' },
    { n: 3, t: 'At harvest, advance the top 5%', d: 'Rank on field yield; the DNA prediction only decides what gets planted.' },
    { n: 4, t: 'Plan next crosses from the shortlist', d: 'Pairs of parents predicted to give the best families (see Data science).' },
  ];

  const topFams = P
    ? Object.entries(P.famN).map(([j, n]) => ({ j: +j, n })).sort((a, b2) => b2.n - a.n).slice(0, 8)
    : [];
  const maxFam = topFams[0]?.n ?? 1;

  return (
    <div className="grid gap-10 lg:grid-cols-[440px_1fr]">
      <FieldScene
        D={D} P={P} layout={state.view === 'grow' ? 'grow' : state.view} colorMode="plan" src={state.src}
        gs={state.gs} playing={state.playing}
        onStageClick={(k) => update({ gs: k, playing: false })}
        onPlayToggle={() => update({ playing: !state.playing })}
      />

      <div className="flex flex-col gap-6">
        <div>
          <Eyebrow>FARMER · THE PLAN</Eyebrow>
          <h1 className="mt-1 text-4xl font-extrabold leading-tight">What to plant this season, and what it saves.</h1>
          <p className="mt-3 max-w-xl text-sm" style={{ color: '#6B6A5C' }}>
            Drag the share of lines and watch your field fill or empty. Press ▶ to grow the season from planting to harvest — starred plants are the lines you advance.
          </p>
        </div>

        <div className="flex gap-2">
          {(['grow', 'field', 'cob'] as const).map((v) => (
            <Pill key={v} on={state.view === v} small onClick={() => update({ view: v })}>{v[0].toUpperCase() + v.slice(1)}</Pill>
          ))}
        </div>

        <SectionCard>
          <div className="flex items-baseline justify-between">
            <div className="font-semibold">Share of lines to plant</div>
            <div className="font-mono-data text-2xl font-bold">{state.budget}%</div>
          </div>
          <input
            type="range" min={5} max={50} value={state.budget}
            onChange={(e) => update({ budget: +e.target.value })}
            className="mt-3 w-full accent-[var(--gold-d)]"
          />
          <div className="mt-1 flex justify-between font-mono-data text-xs" style={{ color: '#6B6A5C' }}>
            <span>5%</span><span>sealed plan: 15%</span><span>50%</span>
          </div>

          <div className="mt-4 font-semibold">Strategy</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {STRATS.map((s) => (
              <Pill key={s.k} on={state.strat === s.k} small onClick={() => update({ strat: s.k })} extraStyle={{ border: '1px solid rgba(30,36,24,.25)' }}>{s.label}</Pill>
            ))}
          </div>
          <div className="mt-2 text-sm" style={{ color: '#6B6A5C' }}>{STRATS.find((s) => s.k === state.strat)?.desc}</div>
        </SectionCard>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {farmStats.map((s) => <StatCard key={s.label} label={s.label} value={s.v} sub={s.sub} bg={s.bg} color={s.color} />)}
        </div>

        <div>
          <div className="mb-3 text-xl font-bold">What to do this season</div>
          <div className="flex flex-col divide-y" style={{ borderColor: 'rgba(30,36,24,.08)' }}>
            {steps.map((s) => (
              <div key={s.n} className="flex gap-4 py-3">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full font-mono-data text-sm font-bold" style={{ background: GOLD, color: '#1E2418' }}>{s.n}</div>
                <div>
                  <div className="font-semibold">{s.t}</div>
                  <div className="text-sm" style={{ color: '#6B6A5C' }}>{s.d}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <SectionCard>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="font-semibold">This is the real sealed decision, not a mockup</div>
              <div className="text-sm" style={{ color: '#6B6A5C' }}>
                +45% genetic gain vs. traditional parent-record selection · 7.7× the gain per plot vs. planting everything · full pipeline runs in 17.4 min from raw data, 9s in judge mode.
              </div>
            </div>
            <a
              href="/data/advancement_list.csv"
              download
              className="shrink-0 rounded-full px-4 py-2 font-mono-data text-sm font-bold"
              style={{ background: '#1E2418', color: '#F3EEE2' }}
            >
              ↓ Download the 2,395-line list (CSV)
            </a>
          </div>
        </SectionCard>

        {topFams.length > 0 && (
          <SectionCard>
            <div className="mb-3 font-semibold">Families getting the most plots</div>
            <div className="flex flex-col gap-2">
              {topFams.map((f, k) => (
                <div key={f.j} className="flex items-center gap-3 text-sm">
                  <div className="w-20 shrink-0 font-mono-data">{D.fams[f.j].pop}</div>
                  <div className="h-3 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                    <div className="h-full rounded transition-[width] duration-500" style={{ width: `${(f.n / maxFam) * 100}%`, background: k < 3 ? GOLDD : GOLD }} />
                  </div>
                  <div className="w-14 shrink-0 text-right font-mono-data">{sgn(P!.Ff[f.j])}</div>
                </div>
              ))}
            </div>
          </SectionCard>
        )}
      </div>
    </div>
  );
}

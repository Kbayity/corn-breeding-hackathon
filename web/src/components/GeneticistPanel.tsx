'use client';
import { interp, fmt, sgn } from '@/lib/format';
import { CURVE, POST, SITE, GEN, ENV, GREEN, GOLD, GOLDD, RUST, STRATS } from '@/lib/constants';
import type { Prepped, PlanResult } from '@/lib/types';
import type { AppState } from '@/lib/appState';
import { FieldScene } from './FieldScene';
import { Pill, Toggle, SectionCard, Eyebrow } from './atoms';

interface Props {
  D: Prepped;
  P: PlanResult | null;
  state: AppState;
  update: (patch: Partial<AppState>) => void;
}

export function GeneticistPanel({ D, P, state, update }: Props) {
  const src = state.src;
  const noGen = !src.history && !src.pdna && !src.ldna;
  const curveKey = noGen ? 'random' : !src.ldna ? 'parent' : state.strat;
  const b = state.budget / 100;
  const gain = interp(CURVE[curveKey].g, b);
  const p10 = interp(CURVE[curveKey].p10, b);
  const p90 = interp(CURVE[curveKey].p90, b);
  const lines = P ? P.lines : Math.round(b * 15968);

  const eOn = ENV.filter((g) => state.env[g.k]).map((g) => g.k);
  const siteR = (eOn.length === 0 ? SITE.base : eOn.length === 1 ? SITE[eOn[0]] : SITE.all).toFixed(2);

  const techStats = [
    { label: 'Lines planted', v: fmt(lines), sub: `of 15,968 · ${state.budget}%` },
    { label: 'Families kept', v: P ? String(P.fams) : '—', sub: 'of 157' },
    { label: 'Same as sealed list', v: P ? (P.overlap * 100).toFixed(0) + '%' : '—', sub: 'of the 2,395 sealed lines' },
    { label: 'Expected gain', v: gain.toFixed(2), sub: `P10 ${p10.toFixed(2)} · P90 ${p90.toFixed(2)} · replay` },
  ];

  const tl = P ? P.tiers : [0, 0, 0];
  const tt = tl[0] + tl[1] + tl[2] || 1;
  const tierText = `high ${(tl[2] / tt * 100).toFixed(0)}% · medium ${(tl[1] / tt * 100).toFixed(0)}% · low ${(tl[0] / tt * 100).toFixed(0)}%`;

  const at15 = state.budget === 15;
  const TB: [string, number | null, string][] = [
    ['Your plan', at15 ? POST[curveKey] : null, GOLD],
    ['Plant everything', POST.all, '#F3EEE2'],
    ["Parents' record", POST.parent, RUST],
    ['Random 15%', POST.random, '#8C8A7C'],
  ];
  const truthNote = !state.truth
    ? 'Sealed before the 2008 results were opened. Click Reveal 2008 to compare your plan against the real yields.'
    : at15
    ? `Your settings map to the "${{ tilt: 'recommended', even: 'even spread', top: 'top lines only', parent: "parents' record", random: 'random' }[curveKey]}" strategy, which was scored on the real 2008 yields.`
    : '2008 was scored only at the sealed 15% budget. Set the slider to 15% to compare against the answer key.';

  const ii = state.pin ?? state.hov;
  let insp: { key: string; status: string; col: string; total: string; drivers: string; sealedReason: string | null; bars: { label: string; v: string; left: number; width: number; neg: boolean }[] } | null = null;
  if (ii != null && P) {
    const i = P.kline[ii], c = D.c;
    const p = (src.history ? 1 : 0) + (src.pdna ? 1 : 0);
    const k = p ? 2 / p : 0;
    const on = !!P.plant[i];
    const parts: [string, number][] = [
      ["Parents' track record", src.history ? c.rec[i] * k : 0],
      ['Parent DNA', src.pdna ? c.dna[i] * k : 0],
      ['Own DNA vs siblings', src.ldna ? c.d[i] : 0],
      ['Tester', src.tester ? c.t[i] : 0],
    ];
    const tot = parts.reduce((s, x) => s + x[1], 0);
    const fm = D.fams[c.f[i]];
    insp = {
      key: `Family ${fm.pop} · sibling #${D.byD[c.f[i]].indexOf(i) + 1} of ${D.fl[c.f[i]].length}`,
      status: on ? '● planted' : '○ not planted',
      col: on ? GOLDD : '#6B6A5C',
      total: sgn(tot) + ' bu/ac',
      drivers: `${fm.gen} cross ${fm.p1} × ${fm.p2} · ${fm.seen === 2 ? 'both parents' : fm.seen === 1 ? 'one parent' : 'no parent'} tested before · P(family beats avg) ${Math.round(fm.prob * 100)}%`,
      sealedReason: D.reasons[i] ?? null,
      bars: parts.map(([label, v]) => {
        const w = Math.min(50, Math.abs(v) / 20 * 50);
        return { label, v: sgn(v), left: v < 0 ? 50 - w : 50, width: w, neg: v < 0 };
      }),
    };
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[440px_1fr]">
      <FieldScene
        D={D} P={P} layout={state.view === 'grow' ? 'grow' : state.view} colorMode="plan" src={src}
        tech pin={state.pin} hov={state.hov} onHoverChange={(i) => update({ hov: i })}
        onKernelClick={(i) => update({ pin: i })}
        gs={state.gs} playing={state.playing}
        onStageClick={(k) => update({ gs: k, playing: false })}
        onPlayToggle={() => update({ playing: !state.playing })}
      />

      <div className="flex flex-col gap-6">
        <div>
          <Eyebrow>GENETICIST · UNDER THE HOOD</Eyebrow>
          <h1 className="mt-1 text-4xl font-extrabold leading-tight">Switch data sources. See why each line made the cut.</h1>
          <p className="mt-3 max-w-xl text-sm" style={{ color: '#6B6A5C' }}>
            Every prediction is family value + own DNA vs siblings + tester. Click a kernel to break it down.
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
          <input type="range" min={5} max={50} value={state.budget} onChange={(e) => update({ budget: +e.target.value })} className="mt-3 w-full accent-[var(--gold-d)]" />
          <div className="mt-4 font-semibold">Strategy</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {STRATS.map((s) => (
              <Pill key={s.k} on={state.strat === s.k} small onClick={() => update({ strat: s.k })} extraStyle={{ border: '1px solid rgba(30,36,24,.25)' }}>{s.label}</Pill>
            ))}
          </div>
        </SectionCard>

        <div className="grid gap-4 sm:grid-cols-2">
          <SectionCard>
            <div className="mb-3 flex items-center gap-2">
              <span className="rounded-full px-2 py-0.5 font-mono-data text-[10px] uppercase" style={{ background: GREEN, color: '#FBF8F1' }}>Hackathon</span>
              <span className="font-semibold">Genetic sources</span>
            </div>
            <div className="flex flex-col gap-3">
              {GEN.map((g) => (
                <div key={g.k} className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold">{g.label}</div>
                    <div className="text-xs" style={{ color: '#6B6A5C' }}>{g.note}</div>
                  </div>
                  <Toggle on={src[g.k]} onClick={() => update({ src: { ...src, [g.k]: !src[g.k] } })} />
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard>
            <div className="mb-3 flex items-center gap-2">
              <span className="rounded-full px-2 py-0.5 font-mono-data text-[10px] uppercase" style={{ background: '#E9CBB0', color: '#5C3A1E' }}>Public</span>
              <span className="font-semibold">Site-forecast add-ons</span>
            </div>
            <p className="text-xs" style={{ color: '#6B6A5C' }}>On top of NASA POWER crop model + USDA NASS county history. Snaps to the closest validated configuration.</p>
            <div className="mt-3 flex flex-col gap-3">
              {ENV.map((g) => (
                <div key={g.k} className="flex items-center justify-between gap-3">
                  <div className="text-sm font-semibold">{g.label}</div>
                  <Toggle on={state.env[g.k]} onClick={() => update({ env: { ...state.env, [g.k]: !state.env[g.k] } })} />
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-baseline justify-between border-t pt-3 text-sm" style={{ borderColor: 'rgba(30,36,24,.1)' }}>
              <span>Site yield r · end of August</span>
              <span className="font-mono-data text-xl font-bold">{siteR}</span>
            </div>
          </SectionCard>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {techStats.map((s) => (
            <div key={s.label} className="rounded-2xl p-4" style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}>
              <div className="text-xs" style={{ color: '#6B6A5C' }}>{s.label}</div>
              <div className="font-mono-data text-2xl font-bold">{s.v}</div>
              <div className="text-xs" style={{ color: '#6B6A5C' }}>{s.sub}</div>
            </div>
          ))}
        </div>

        <SectionCard>
          <div className="flex items-baseline justify-between">
            <div className="font-semibold">Confidence of planted lines</div>
            <div className="font-mono-data text-xs" style={{ color: '#6B6A5C' }}>{tierText}</div>
          </div>
          <div className="mt-2 flex h-2 overflow-hidden rounded-full">
            <div style={{ width: `${tl[2] / tt * 100}%`, background: GREEN }} />
            <div style={{ width: `${tl[1] / tt * 100}%`, background: GOLD }} />
            <div style={{ width: `${tl[0] / tt * 100}%`, background: '#C9BFA8' }} />
          </div>
        </SectionCard>

        <SectionCard dark>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold">2008 answer key</div>
              <div className="text-xs opacity-70">post-hoc · scored once, at the sealed 15% budget</div>
            </div>
            <button onClick={() => update({ truth: !state.truth })} className="rounded-full px-4 py-2 font-mono-data text-sm font-bold transition-colors" style={{ background: GOLD, color: '#1E2418' }}>
              {state.truth ? 'Seal again' : 'Reveal 2008'}
            </button>
          </div>
          <div className="mt-4 flex flex-col gap-2">
            {TB.map(([label, v, color], j) => (
              <div key={label} className="flex items-center gap-3 text-sm">
                <div className="w-32 shrink-0">{label}</div>
                <div className="h-3 flex-1 rounded" style={{ background: 'rgba(255,255,255,.12)' }}>
                  <div
                    className="h-full rounded transition-[width] duration-700 ease-out"
                    style={{ width: state.truth && v != null ? `${v / 6 * 100}%` : 0, background: color, transitionDelay: `${j * 120}ms` }}
                  />
                </div>
                <div className="w-14 shrink-0 text-right font-mono-data font-bold">
                  {state.truth ? (v == null ? '—' : v.toFixed(2)) : '🔒'}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs opacity-70">{truthNote}</div>
        </SectionCard>

        <SectionCard>
          <div className="flex items-baseline justify-between">
            <div className="font-semibold">Why this line?</div>
            <div className="text-xs" style={{ color: '#6B6A5C' }}>click a kernel to pin</div>
          </div>
          {insp ? (
            <>
              <div className="mt-2 text-sm font-semibold">{insp.key}</div>
              <div className="text-xs" style={{ color: insp.col }}>{insp.status}</div>
              <div className="mt-1 text-xs" style={{ color: '#6B6A5C' }}>{insp.drivers}</div>
              {insp.sealedReason && (
                <div className="mt-3 rounded-xl p-3" style={{ background: 'rgba(98,142,45,.08)', border: '1px solid rgba(98,142,45,.25)' }}>
                  <div className="font-mono-data text-[10px] uppercase tracking-wide" style={{ color: GREEN }}>verbatim · sealed 2008 decision</div>
                  <div className="mt-1 text-sm italic">&ldquo;{insp.sealedReason}&rdquo;</div>
                </div>
              )}
              <div className="mt-3 flex flex-col gap-2">
                {insp.bars.map((bar) => (
                  <div key={bar.label} className="flex items-center gap-3 text-sm">
                    <div className="w-40 shrink-0">{bar.label}</div>
                    <div className="relative h-2 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                      <div className="absolute inset-y-0 rounded" style={{ left: `${bar.left}%`, width: `${bar.width}%`, background: bar.neg ? RUST : GREEN }} />
                    </div>
                    <div className="w-12 shrink-0 text-right font-mono-data">{bar.v}</div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <div className="mt-2 font-semibold">Hover or click a kernel</div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span>Predicted testcross vs avg</span><span>—</span>
              </div>
            </>
          )}
        </SectionCard>
      </div>
    </div>
  );
}

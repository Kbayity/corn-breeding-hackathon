'use client';
import { useEffect, useState } from 'react';
import { fmt } from '@/lib/format';
import { POST, FW, MO, SAT, GREEN, GOLD, GOLDD, RUST, INK } from '@/lib/constants';
import type { Prepped } from '@/lib/types';
import { useTween } from '@/lib/useTween';
import { SectionCard, Eyebrow, StatCard } from './atoms';
import { BudgetCurveChart } from './charts/BudgetCurveChart';
import { HorizonChart } from './charts/HorizonChart';

const LD: [string, number, string][] = [
  ['Random 15%', POST.random, '#8C8A7C'],
  ["Parents' record only", POST.parent, RUST],
  ['Top-predicted lines only', POST.top, 'oklch(0.7 0.08 100)'],
  ['Plant everything', POST.all, INK],
  ['DNA within every family', POST.even, GREEN],
  ['Recommended: DNA + family tilt', POST.tilt, GOLDD],
];

export function DataScientistPanel({ D }: { D: Prepped }) {
  const [entered, setEntered] = useState(false);
  useEffect(() => { const t = setTimeout(() => setEntered(true), 90); return () => clearTimeout(t); }, []);
  const tw = useTween();
  const E = entered ? 1 : 0;

  const dsHero = [
    { v: '+' + tw('h1', E ? 14 : 0, 0).toFixed(0) + '%', label: 'more genetic gain', sub: 'on 15% of the plots · 2008', bg: GOLD, color: INK },
    { v: tw('h2', E ? 0.56 : 0, 0).toFixed(2), label: 'line accuracy (r)', sub: 'C1 0.562 · C2 0.566', bg: INK, color: '#F3EEE2' },
    { v: tw('h3', E ? 38 : 0, 0).toFixed(0) + '%', label: 'true top-10% caught', sub: 'C1 · chance would be 10%', bg: GREEN, color: '#FBF8F1' },
    { v: fmt(tw('h4', E ? 74361 : 0, 0)), label: 'plots never planted', sub: '85% of the field budget', bg: '#FBF8F1', color: INK },
  ];

  const crosses = D.crosses.slice().sort((a, b) => b.prob - a.prob).slice(0, 8);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Eyebrow>DATA SCIENTIST · VALIDATION &amp; WHAT&apos;S NEXT</Eyebrow>
        <h1 className="mt-1 text-4xl font-extrabold leading-tight">Did the model beat the breeder&apos;s record?</h1>
        <p className="mt-3 max-w-2xl text-sm" style={{ color: '#6B6A5C' }}>
          Trained on 2000–2007 only. The 2008 yields stayed sealed until the list was final, then were opened once.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {dsHero.map((s) => <StatCard key={s.label} label={s.label} value={s.v} sub={s.sub} bg={s.bg} color={s.color} valueFirst />)}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard>
          <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>What mattered most</div>
          <div className="mt-1 mb-4 font-semibold">Spreading DNA picks across families beats chasing the top.</div>
          <div className="flex flex-col gap-2">
            {LD.map(([label, v, color], j) => (
              <div key={label} className="flex items-center gap-3 text-sm">
                <div className="w-48 shrink-0">{label}</div>
                <div className="h-3 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                  <div className="h-full rounded transition-[width] duration-700" style={{ width: `${E * v / 6 * 100}%`, background: color, transitionDelay: `${200 + j * 110}ms` }} />
                </div>
                <div className="w-12 shrink-0 text-right font-mono-data font-bold">{v.toFixed(2)}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs" style={{ color: '#6B6A5C' }}>
            Genetic gain, bu/ac, 2008 post-hoc. Parent DNA + record choose families; line DNA alone is weak, but applied inside every family it adds +1.6 bu/ac over the traditional parents&apos; record.
          </p>
        </SectionCard>

        <SectionCard>
          <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>Budget curve · replay 2004–07</div>
          <div className="mt-1 mb-2 font-semibold">Gain peaks near 15–20% of plots.</div>
          <BudgetCurveChart curveKey="tilt" budget={0.15} gain={POST.tilt} />
          <div className="mt-1 flex gap-4 text-xs" style={{ color: '#6B6A5C' }}>
            <span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: GOLDD }} />Recommended (P10–P90 band)</span>
            <span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: '#B0503B' }} />Parents&apos; record</span>
            <span><span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: '#8C8A7C' }} />Random</span>
          </div>
          <p className="mt-1 text-xs" style={{ color: '#6B6A5C' }}>marker = your plan · change it in Farmer or Technical</p>
        </SectionCard>

        <SectionCard>
          <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>Horizon · how stale can the data be?</div>
          <div className="mt-1 mb-2 font-semibold">2008 held r ≈ 0.55 even with data three seasons old.</div>
          <HorizonChart />
          <p className="mt-1 text-xs" style={{ color: '#6B6A5C' }}>
            Line accuracy (r, mean of C1/C2) by seasons between last training year and target. Only 3% of 2008 families had a parent seen 3 seasons earlier — parent DNA carried the prediction.
          </p>
        </SectionCard>

        <SectionCard>
          <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>Family vs within-family</div>
          <div className="mt-1 mb-4 font-semibold">Easy to rank families, hard to rank siblings.</div>
          <div className="flex flex-col gap-4">
            {FW.map(([cl, n, f, l, w], gi) => (
              <div key={cl}>
                <div className="mb-1 text-xs" style={{ color: '#6B6A5C' }}>{cl} · {n} families</div>
                {[['Family value', f, GOLDD], ['Single line', l, GREEN], ['Sibling vs sibling', w, RUST]].map(([label, v, color], j) => (
                  <div key={label as string} className="mb-1 flex items-center gap-3 text-sm">
                    <div className="w-32 shrink-0">{label}</div>
                    <div className="h-3 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                      <div className="h-full rounded transition-[width] duration-700" style={{ width: `${E * (v as number) * 100}%`, background: color as string, transitionDelay: `${200 + (gi * 3 + j) * 110}ms` }} />
                    </div>
                    <div className="w-12 shrink-0 text-right font-mono-data font-bold">{(v as number).toFixed(2)}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs" style={{ color: '#6B6A5C' }}>2008 post-hoc, r with observed. 80% family intervals covered 70% (C1) and 80% (C2) of families.</p>
        </SectionCard>

        <SectionCard>
          <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>Near future · in-season site forecasts</div>
          <div className="mt-1 mb-4 font-semibold">Site forecasts peak by end of July, then hold through harvest.</div>
          <div className="flex items-end gap-3" style={{ height: 120 }}>
            {(() => {
              const peak = MO.reduce((best, [, v], j) => (v > MO[best][1] ? j : best), 0);
              return MO.map(([l, v], j) => (
                <div key={l} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t transition-[height] duration-700" style={{ height: `${E * v / .5 * 110}px`, background: j === peak ? GOLDD : j === MO.length - 1 ? '#C9BFA8' : GOLD, transitionDelay: `${300 + j * 120}ms` }} />
                  <div className="font-mono-data text-xs font-bold">{v.toFixed(2)}</div>
                  <div className="text-xs" style={{ color: '#6B6A5C' }}>{l}</div>
                </div>
              ));
            })()}
          </div>
          <div className="mt-4 text-xs font-semibold">Satellite (post-hoc): NDVI correlation with yield, and the forecast-skill lift from combining sources</div>
          <div className="mt-2 flex flex-col gap-1">
            {SAT.map(([label, v], j) => (
              <div key={label} className="flex items-center gap-3 text-sm">
                <div className="w-56 shrink-0 text-xs">{label}</div>
                <div className="h-3 flex-1 rounded" style={{ background: 'rgba(30,36,24,.08)' }}>
                  <div className="h-full rounded transition-[width] duration-700" style={{ width: `${E * v / .35 * 100}%`, background: GREEN, transitionDelay: `${400 + j * 110}ms` }} />
                </div>
                <div className="w-14 shrink-0 text-right font-mono-data font-bold">{j === SAT.length - 1 ? `+${Math.round(v * 100)}%` : v.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard dark>
          <div className="font-mono-data text-xs uppercase" style={{ color: GOLD }}>Near future · next crosses to make</div>
          <div className="mt-1 mb-3 font-semibold">Parent pairs predicted to give the best families.</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs opacity-60">
                <th className="text-left font-normal">CL</th>
                <th className="text-left font-normal">Parents</th>
                <th className="text-right font-normal">family</th>
                <th className="text-right font-normal">best 5%</th>
                <th className="text-right font-normal">P(&gt;avg)</th>
              </tr>
            </thead>
            <tbody className="font-mono-data">
              {crosses.map((x, i) => (
                <tr key={i} className="border-t" style={{ borderColor: 'rgba(255,255,255,.08)' }}>
                  <td className="py-1">{x.cl}</td>
                  <td>{x.p1} × {x.p2}</td>
                  <td className="text-right">{x.fam >= 0 ? '+' : ''}{x.fam.toFixed(1)}</td>
                  <td className="text-right">{x.best >= 0 ? '+' : ''}{x.best.toFixed(1)}</td>
                  <td className="text-right font-bold" style={{ color: GOLD }}>{Math.round(x.prob * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs opacity-60">Ranked from all data through 2008. A relative ranking, not a yield guarantee.</p>
        </SectionCard>
      </div>

      <SectionCard>
        <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>Honest limits</div>
        <div className="mt-1 mb-4 font-semibold">Where this still needs work — we'd rather you hear it from us.</div>
        <div className="grid gap-4 sm:grid-cols-2">
          {LIMITS.map((l) => (
            <div key={l.t} className="flex gap-3">
              <div className="mt-0.5 shrink-0 font-mono-data text-xs" style={{ color: RUST }}>▲</div>
              <div>
                <div className="text-sm font-semibold">{l.t}</div>
                <div className="text-xs" style={{ color: '#6B6A5C' }}>{l.d}</div>
              </div>
            </div>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}

const LIMITS = [
  { t: 'Sibling ranking is weak (r 0.16–0.20)', d: 'Siblings differ little and are measured on few plots. The family call carries the decision — the DNA-vs-siblings part inside a family is the least reliable piece.' },
  { t: 'Intervals run overconfident', d: '2008 line 80% intervals covered only 68–73%, not 80%; C1’s high-confidence tier covered just 54% (C2 was 76%). Widening and recalibrating per tier is the next fix.' },
  { t: 'Yield selection drifts wetter', d: 'Planted lines are +1.6–1.9 moisture points wetter at harvest — a real drying-cost trade-off with no finished economic index yet.' },
  { t: '2008 is the only true out-of-sample test', d: 'One held-out season, and ~40% of its locations hold a single family — thin ground for some of these numbers to stand on.' },
];

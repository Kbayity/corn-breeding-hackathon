'use client';
import { GREEN, GOLDD, RUST, GOLD } from '@/lib/constants';
import type { Tab } from '@/lib/appState';

const RC: { k: Tab; n: string; title: string; desc: string; chips: string[]; col: string; bg: string }[] = [
  { k: 'farmer', n: '01 · Farmer', title: 'Farmer', desc: 'The plan in plain language: which lines to plant, how many plots it saves, and what to do this season.', chips: ['plots saved', '$ saved', 'what to do'], col: GREEN, bg: 'oklch(0.93 0.04 130)' },
  { k: 'tech', n: '02 · Geneticist', title: 'Geneticist', desc: 'Switch data sources and strategies, and see why each line was picked — parents, DNA and tester.', chips: ['data sources', 'line breakdown', '2008 check'], col: GOLDD, bg: 'oklch(0.94 0.05 85)' },
  { k: 'ds', n: '03 · Data scientist', title: 'Data scientist', desc: "What mattered most, how stale data can be, budget curves, and what to test next.", chips: ['ablation', 'horizon', 'next crosses'], col: RUST, bg: 'oklch(0.93 0.035 50)' },
];

export function RoleSelect({ onPick, onStory, onPlayground }: { onPick: (k: Tab) => void; onStory: () => void; onPlayground: () => void }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center gap-10 px-6 py-16">
      <div className="flex flex-col items-center gap-2 text-center">
        <div className="flex items-center gap-2 font-mono-data text-sm uppercase tracking-wide" style={{ color: '#4A5C34' }}>
          <span className="inline-block h-3 w-3 rounded-full" style={{ background: GOLD }} />
          Maize Advancement Advisor
        </div>
        <div className="text-3xl font-extrabold">Choose how you want to look at the 2008 decision.</div>
        <div className="mt-2 flex gap-4">
          <button onClick={onStory} className="font-mono-data text-sm underline underline-offset-4" style={{ color: '#6B6A5C' }}>
            or walk through the story →
          </button>
          <button onClick={onPlayground} className="font-mono-data text-sm underline underline-offset-4" style={{ color: '#6B6A5C' }}>
            or plant a field just for fun 🌽
          </button>
        </div>
      </div>

      <div className="grid w-full gap-6 sm:grid-cols-3">
        {RC.map((r) => (
          <button
            key={r.k}
            onClick={() => onPick(r.k)}
            className="flex flex-col overflow-hidden rounded-2xl text-left transition-transform hover:-translate-y-1"
            style={{ background: '#FBF8F1', border: '1px solid rgba(30,36,24,.1)' }}
          >
            <div className="flex h-[190px] items-center justify-center" style={{ background: r.bg, borderBottom: '1px solid rgba(30,36,24,.08)' }}>
              <RoleIllustration k={r.k} />
            </div>
            <div className="flex flex-col gap-2 p-5">
              <div className="font-mono-data text-xs uppercase" style={{ color: '#8C8A7C' }}>{r.n}</div>
              <div className="text-xl font-bold">{r.title}</div>
              <div className="text-sm" style={{ color: '#6B6A5C' }}>{r.desc}</div>
              <div className="mt-1 flex flex-wrap gap-2">
                {r.chips.map((c) => (
                  <span key={c} className="rounded-full px-2 py-1 font-mono-data text-[11px]" style={{ background: 'rgba(30,36,24,.06)', color: '#6B6A5C' }}>{c}</span>
                ))}
              </div>
              <div className="mt-2 font-bold" style={{ color: r.col }}>Open {r.title} →</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function RoleIllustration({ k }: { k: Tab }) {
  if (k === 'farmer') {
    return (
      <div className="grid grid-cols-8 gap-1 p-4">
        {Array.from({ length: 32 }, (_, i) => (
          <div key={i} style={{ width: 22, height: 14, borderRadius: 4, background: '#DCD3BF', animation: `mzPlot 3.4s ease-in-out ${((i % 8) + Math.floor(i / 8)) * 0.16}s infinite` }} />
        ))}
      </div>
    );
  }
  if (k === 'tech') {
    return (
      <div className="relative" style={{ width: 60, height: 90 }}>
        {Array.from({ length: 14 }, (_, j) => (
          <div key={j}>
            <div style={{ position: 'absolute', left: 0, top: 45, width: 10, height: 10, borderRadius: '50%', background: GREEN, animation: `mzHelixA 1.3s ease-in-out ${-j * 0.19}s infinite alternate` }} />
            <div style={{ position: 'absolute', left: 0, top: 45, width: 10, height: 10, borderRadius: '50%', background: GOLD, animation: `mzHelixB 1.3s ease-in-out ${-j * 0.19}s infinite alternate` }} />
          </div>
        ))}
      </div>
    );
  }
  return (
    <div className="flex items-end gap-1" style={{ height: 110 }}>
      {[.5, .8, .62, 1, .74, .9, .56].map((h, j) => (
        <div key={j} style={{ width: 20, height: h * 110, borderRadius: '4px 4px 0 0', background: j === 3 ? GOLDD : j % 2 ? RUST : 'oklch(0.7 0.1 50)', transformOrigin: 'bottom', animation: `mzBar 1.6s ease-in-out ${j * 0.17}s infinite alternate` }} />
      ))}
    </div>
  );
}

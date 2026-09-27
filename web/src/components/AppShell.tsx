'use client';
import { ReactNode } from 'react';
import { GOLD } from '@/lib/constants';
import type { Tab } from '@/lib/appState';
import { Pill } from './atoms';

const MODES: { k: Tab | 'story'; label: string }[] = [
  { k: 'farmer', label: 'Farmer' },
  { k: 'tech', label: 'Geneticist' },
  { k: 'ds', label: 'Data scientist' },
  { k: 'story', label: 'Story' },
];

export function AppShell({ active, onSelect, children }: { active: Tab | 'story'; onSelect: (k: Tab | 'story') => void; children: ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 border-b px-6 py-4" style={{ borderColor: 'rgba(30,36,24,.1)' }}>
        <div className="flex items-center gap-3">
          <span className="inline-block h-4 w-4 rounded-full" style={{ background: GOLD }} />
          <div>
            <div className="font-mono-data text-sm font-bold uppercase tracking-wide">Maize Advancement Advisor</div>
            <div className="font-mono-data text-xs" style={{ color: '#6B6A5C' }}>2008 field season · sealed forecast · evaluated once</div>
          </div>
        </div>
        <nav className="flex gap-1 rounded-full p-1" style={{ background: 'rgba(30,36,24,.05)' }}>
          {MODES.map((m) => (
            <Pill key={m.k} on={active === m.k} small onClick={() => onSelect(m.k)}>{m.label}</Pill>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      <footer className="mx-auto max-w-6xl px-6 pb-10 pt-4 text-xs" style={{ color: '#8C8A7C', borderTop: '1px solid rgba(30,36,24,.08)' }}>
        Decision sealed before the 2008 results were opened; evaluated once. Plot cost ($150) is an assumption. Gains shown in the simulator come from the 2004–07 replay unless marked 2008.
      </footer>
    </div>
  );
}

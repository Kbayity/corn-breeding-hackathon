'use client';
import { CSSProperties, ReactNode } from 'react';
import { GREEN, INK } from '@/lib/constants';

export function Pill({ on, small, children, onClick, extraStyle }: { on: boolean; small?: boolean; children: ReactNode; onClick?: () => void; extraStyle?: CSSProperties }) {
  return (
    <button
      onClick={onClick}
      style={{
        all: 'unset', cursor: 'pointer', padding: small ? '7px 14px' : '9px 18px',
        borderRadius: '999px', fontFamily: 'var(--font-hanken), sans-serif',
        fontWeight: 600, fontSize: small ? 12 : 13, lineHeight: 1,
        background: on ? INK : 'transparent', color: on ? '#F3EEE2' : INK,
        transition: 'background .25s, color .25s', ...extraStyle,
      }}
    >
      {children}
    </button>
  );
}

export function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      style={{
        all: 'unset', cursor: 'pointer', position: 'relative', width: 36, height: 20,
        borderRadius: 999, background: on ? GREEN : '#D6CFBF', transition: 'background .25s', display: 'block',
      }}
    >
      <span style={{
        position: 'absolute', top: 2, left: on ? 18 : 2, width: 16, height: 16,
        borderRadius: '50%', background: '#FBF8F1', boxShadow: '0 1px 2px rgba(0,0,0,.2)',
        transition: 'left .25s cubic-bezier(.5,0,.2,1.4)',
      }} />
    </button>
  );
}

export function BarRow({ label, value, width, color, dark }: { label: string; value: string; width: number; color: string; dark?: boolean }) {
  return (
    <div className="flex items-center gap-3 text-sm" style={{ color: dark ? '#F3EEE2' : INK }}>
      <div className="w-40 shrink-0 truncate">{label}</div>
      <div className="flex-1 h-3 rounded" style={{ background: dark ? 'rgba(255,255,255,.12)' : 'rgba(30,36,24,.08)' }}>
        <div className="h-full rounded transition-[width] duration-700" style={{ width: `${Math.max(0, Math.min(100, width))}%`, background: color }} />
      </div>
      <div className="w-14 shrink-0 text-right font-mono-data font-bold">{value}</div>
    </div>
  );
}

export function StatCard({ label, value, sub, bg, color, valueFirst }: { label: string; value: string; sub: string; bg: string; color: string; valueFirst?: boolean }) {
  const labelEl = <div className="text-sm opacity-80" key="l">{label}</div>;
  const valueEl = <div className="font-mono-data font-bold text-4xl" key="v">{value}</div>;
  return (
    <div className="flex flex-col gap-2 rounded-2xl px-[18px] py-4" style={{ background: bg, color }}>
      {valueFirst ? [valueEl, labelEl] : [labelEl, valueEl]}
      <div className="text-xs opacity-70">{sub}</div>
    </div>
  );
}

export function SectionCard({ children, dark, className }: { children: ReactNode; dark?: boolean; className?: string }) {
  return (
    <div
      className={`rounded-2xl p-6 ${className ?? ''}`}
      style={{ background: dark ? INK : '#FBF8F1', color: dark ? '#F3EEE2' : INK, border: dark ? 'none' : '1px solid rgba(30,36,24,.08)' }}
    >
      {children}
    </div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="font-mono-data text-xs tracking-wide uppercase" style={{ color: GREEN }}>
      {children}
    </div>
  );
}

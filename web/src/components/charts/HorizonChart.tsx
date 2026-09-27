'use client';
import { HZ, GOLDD, GREEN } from '@/lib/constants';

const HX = (g: number) => 70 + (g - 1) * 170;
const HY = (v: number) => 200 - v / 0.7 * 188;

const YEAR_COLOR: Record<string, string> = { '2008': GOLDD, '2007': GREEN, '2006': 'oklch(0.65 0.08 140)', '2005': '#A8A493' };

export function HorizonChart() {
  const lines = Object.entries(HZ).map(([y, a]) => ({
    y,
    d: a.map((v, j) => (j ? 'L' : 'M') + HX(j + 1) + ' ' + HY(v).toFixed(1)).join(' '),
    c: YEAR_COLOR[y] ?? '#A8A493',
    w: y === '2008' ? 4 : 2,
    ly: HY(a[2]) + 4 + (y === '2006' ? 4 : y === '2005' ? -2 : 0),
  }));

  return (
    <svg viewBox="0 0 520 230" className="w-full">
      {[0, .2, .4, .6].map((v) => (
        <line key={v} x1={40} x2={510} y1={HY(v)} y2={HY(v)} stroke="rgba(30,36,24,.08)" />
      ))}
      {[0, .2, .4, .6].map((v) => (
        <text key={v} x={32} y={HY(v) + 4} textAnchor="end" className="font-mono-data" fontSize={11} fill="#6B6A5C">{v.toFixed(1)}</text>
      ))}
      {[1, 2, 3].map((g) => (
        <text key={g} x={HX(g)} y={218} textAnchor="middle" className="font-mono-data" fontSize={11} fill="#6B6A5C">{g}{g === 1 ? ' season back' : ' seasons back'}</text>
      ))}
      {lines.map((l) => <path key={l.y} d={l.d} fill="none" stroke={l.c} strokeWidth={l.w} />)}
      {lines.map((l) => (
        <text key={l.y} x={452} y={l.ly - 4} className="font-mono-data" fontSize={12} fontWeight={700} fill={l.c}>{l.y}</text>
      ))}
    </svg>
  );
}

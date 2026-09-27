'use client';
import { BUD, CURVE, GOLDD, INK, type CurveKey } from '@/lib/constants';

const X = (v: number) => 40 + (v - 0.05) / (0.5 - 0.05) * 470;
const Y = (v: number) => 226 - (v / 6.5) * 214;

const CUR_LABEL: Record<CurveKey, string> = {
  tilt: 'Recommended', even: 'Even spread', top: 'Top lines only',
  parent: "Parents' record (no line DNA)", random: 'Random (no genetics)',
};

export function BudgetCurveChart({ curveKey, budget, gain }: { curveKey: CurveKey; budget: number; gain: number }) {
  const bs = BUD.filter((x) => x <= 0.5);
  const cc = CURVE[curveKey];
  const pth = (a: number[]) => bs.map((x, j) => (j ? 'L' : 'M') + X(x).toFixed(1) + ' ' + Y(a[j]).toFixed(1)).join(' ');
  const band = pth(cc.p90) + ' ' + bs.slice().reverse().map((x, j) => 'L' + X(x).toFixed(1) + ' ' + Y(cc.p10[bs.length - 1 - j]).toFixed(1)).join(' ') + ' Z';
  const allY = Y(4.464);
  const mx = X(Math.min(budget, 0.5)), my = Y(gain);

  return (
    <svg viewBox="0 0 520 250" className="w-full">
      {[0, 2, 4, 6].map((v) => (
        <line key={v} x1={40} x2={510} y1={Y(v)} y2={Y(v)} stroke="rgba(30,36,24,.08)" />
      ))}
      {[0, 2, 4, 6].map((v) => (
        <text key={v} x={32} y={Y(v) + 4} textAnchor="end" className="font-mono-data" fontSize={11} fill="#6B6A5C">{v}</text>
      ))}
      {[.05, .1, .2, .3, .4, .5].map((v) => (
        <text key={v} x={X(v)} y={240} textAnchor="middle" className="font-mono-data" fontSize={11} fill="#6B6A5C">{Math.round(v * 100)}%</text>
      ))}
      <line x1={40} x2={510} y1={allY} y2={allY} stroke={INK} strokeDasharray="3 3" />
      <text x={508} y={allY - 9} textAnchor="end" className="font-mono-data" fontSize={11} fill={INK}>plant everything 4.46</text>
      <path d={band} fill={GOLDD} opacity={0.18} />
      <path d={pth(CURVE.random.g)} fill="none" stroke="#8C8A7C" strokeWidth={2} />
      <path d={pth(CURVE.parent.g)} fill="none" stroke="#B0503B" strokeWidth={2} />
      <path d={pth(cc.g)} fill="none" stroke={GOLDD} strokeWidth={3} />
      <circle cx={mx} cy={my} r={5} fill={GOLDD} stroke={INK} strokeWidth={1.5} />
      <text x={44} y={20} className="font-mono-data" fontSize={12} fontWeight={700} fill={INK}>{CUR_LABEL[curveKey]}</text>
    </svg>
  );
}

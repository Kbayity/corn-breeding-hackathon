'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { loadMaizeData, prep } from '@/lib/data';
import { plan } from '@/lib/plan';
import type { Prepped, PlanResult } from '@/lib/types';
import { initialAppState, type AppState, type Tab } from '@/lib/appState';
import { Splash } from '@/components/Splash';
import { RoleSelect } from '@/components/RoleSelect';
import { AppShell } from '@/components/AppShell';
import { FarmerPanel } from '@/components/FarmerPanel';
import { GeneticistPanel } from '@/components/GeneticistPanel';
import { DataScientistPanel } from '@/components/DataScientistPanel';
import { StoryPanel } from '@/components/StoryPanel';
import { Playground } from '@/components/Playground';

export default function Home() {
  const [D, setD] = useState<Prepped | null>(null);
  const [state, setState] = useState<AppState>(initialAppState);
  const memo = useRef(new Map<string, PlanResult>());

  useEffect(() => {
    loadMaizeData().then((raw) => setD(prep(raw))).catch((e) => console.warn('maize data', e));
  }, []);

  function update(patch: Partial<AppState>) {
    setState((s) => ({ ...s, ...patch }));
  }

  const P = useMemo(() => {
    if (!D) return null;
    return plan(D, memo.current, state.budget, state.strat, state.src);
  }, [D, state.budget, state.strat, state.src]);

  if (state.screen === 'splash') {
    return <Splash onDone={() => update({ screen: 'roles' })} />;
  }

  if (state.screen === 'roles') {
    return (
      <RoleSelect
        onPick={(k: Tab) => update({ screen: 'app', mode: 'sim', tab: k })}
        onStory={() => update({ screen: 'app', mode: 'story', step: 0 })}
        onPlayground={() => update({ screen: 'playground' })}
      />
    );
  }

  if (state.screen === 'playground') {
    return <Playground onBack={() => update({ screen: 'roles' })} />;
  }

  if (!D) {
    return (
      <div className="flex min-h-screen items-center justify-center font-mono-data text-sm" style={{ color: '#6B6A5C' }}>
        Loading 2008 field data…
      </div>
    );
  }

  const active = state.mode === 'story' ? 'story' : state.tab;

  return (
    <AppShell
      active={active}
      onSelect={(k) => (k === 'story' ? update({ mode: 'story', step: 0 }) : update({ mode: 'sim', tab: k as Tab }))}
    >
      {state.mode === 'story' ? (
        <StoryPanel D={D} P={P} onExit={() => update({ screen: 'roles', mode: 'sim' })} />
      ) : state.tab === 'farmer' ? (
        <FarmerPanel D={D} P={P} state={state} update={update} />
      ) : state.tab === 'tech' ? (
        <GeneticistPanel D={D} P={P} state={state} update={update} />
      ) : (
        <DataScientistPanel D={D} />
      )}
    </AppShell>
  );
}

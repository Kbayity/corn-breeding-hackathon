# Data + logic layer for the app (no Streamlit here, so it can be tested on its own).
# Everything the app shows comes from forward-validated tables: app/precompute.py (line/family predictions at data
# cutoffs), cache/results/report_2008 (explanations), final_2008 (sealed decision + its one evaluation),
# inseason/ (site forecasts through the season), satellite/ (NDVI-augmented site forecasts), budget_ablation (plan risk).
import os, sys, math, datetime as dt, importlib, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import hackdata as H, famodels as F, gp
from paths import S
A50 = importlib.import_module('50_allocation')
APP = f'{S}/app'; RES = f'{S}/results'
TC = 'pop_eff_YLD'
HARVEST_DONE = (11, 1)                         # a season's trial results are usable from 1 Nov of that season
LEADS = [('jan', 1, 1, 'January (pre-season)'), ('jun', 6, 30, 'End of June'), ('jul', 7, 31, 'End of July'),
         ('aug', 8, 31, 'End of August'), ('harvest', 10, 31, 'Full season (hindcast)')]
COL = dict(ours='#56B4E9', base='#E69F00', trad='#D55E00', rand='#CC79A7', all='#9AA5B1', good='#009E73', warn='#F0E442', ink='#E8EDF2')


def _read(path, kind='csv'):
    return (pd.read_parquet(path) if kind == 'pq' else pd.read_csv(path)) if os.path.exists(path) else None


class Store:
    def __init__(self):
        self.lp = _read(f'{APP}/line_preds.parquet', 'pq'); self.fp = _read(f'{APP}/family_preds.parquet', 'pq')
        self.tl = _read(f'{APP}/truth_lines.parquet', 'pq'); self.tf = _read(f'{APP}/truth_families.parquet', 'pq')
        self.counts = _read(f'{APP}/season_counts.csv'); self.fit = _read(f'{APP}/fit_info.csv')
        self.betas = np.load(f'{APP}/betas.npz') if os.path.exists(f'{APP}/betas.npz') else None
        self.rep_lines = _read(f'{RES}/report_2008/lines.csv'); self.rep_fams = _read(f'{RES}/report_2008/families.csv')
        self.eval_strat = _read(f'{ROOT}/final_2008/eval_strategies.csv'); self.eval_acc = _read(f'{ROOT}/final_2008/eval_accuracy.csv')
        self.adv = _read(f'{ROOT}/final_2008/advancement_list.csv'); self.abl = _read(f'{RES}/budget_ablation_real.csv')
        self.site = _read(f'{RES}/inseason/s6a_preds.csv'); self.sat = _read(f'{RES}/satellite/s3_preds.csv')
        self.crosses = _read(f'{RES}/forecast/future_2027/crosses.csv'); self.horizon = _read(f'{RES}/horizon.csv')
        self.pops = pd.read_parquet(f'{S}/model/pops.parquet')
        self.slopes = {}
        for f in os.listdir(RES):
            if f.startswith('scores_meta_'):
                m = pd.read_csv(f'{RES}/{f}')
                for r in m.itertuples(): self.slopes[(r.cl, int(r.year))] = float(r.fam_slope)
        self.years = sorted(self.lp.YEAR.unique()) if self.lp is not None else []

    @property
    def ready(self): return self.lp is not None and self.fp is not None


# ------------------------------------------------------------------ date -> what is known
def cutoff(Y, d, best=False):
    """k = seasons between the newest usable trial season and Y; lead = in-season site information for season Y."""
    if best: return dict(k=1, lead='aug', note=f'Best prediction: all trial seasons before {Y}, genotypes, pedigree, and season {Y} weather '
                                            f'to Aug 31 (the earliest date at which the site forecast reaches its full-season accuracy). No later season is used.')
    last = d.year if (d.month, d.day) >= HARVEST_DONE else d.year - 1
    k = Y - last
    note = ''
    if k < 1: k, note = 1, f'Season {Y} is already harvested on this date; showing the prediction made from data before its harvest.'
    lead = 'jan'
    if d.year == Y:
        for key, mth, day, _ in LEADS[1:4]:
            if (d.month, d.day) >= (mth, day): lead = key
    elif d.year > Y: lead = 'aug'
    if k > 3: note = f'Only {Y - k} and earlier seasons were available on this date; predictions are precomputed up to 3 seasons back, showing the 3-season-back model.'; k = 3
    return dict(k=k, lead=lead, note=note)


# ------------------------------------------------------------------ genetics
GEN_SOURCES = {
    'history': ('Hackathon', 'Field-trial history + pedigree (parents\' earlier families)'),
    'parent_dna': ('Hackathon', 'Parent genotypes (2,911 SNPs)'),
    'line_dna': ('Hackathon', 'Line genotypes (HMM-imputed from 49-123 SNPs)'),
    'tester': ('Hackathon', 'Tester effects'),
}
ENV_SOURCES = {
    'cropmodel': ('Public', 'NASA POWER weather + SSURGO soil (crop model)'),
    'nass': ('Public', 'USDA NASS county yield history'),
    'gridmet': ('Public', 'gridMET 4 km weather (instead of POWER)'),
    'drought': ('Public', 'US Drought Monitor to date'),
    'storms': ('Public', 'NOAA storm events to date'),
    'modis': ('Public', 'MODIS 250 m NDVI to date'),
    'landsat': ('Public', 'Landsat 30 m NDVI to date'),
}


def line_table(st, Y, k, use):
    """Per-line prediction for season Y with data through Y-k and the chosen genetic sources."""
    lp = st.lp[(st.lp.YEAR == Y) & (st.lp.k == k)]; fp = st.fp[(st.fp.YEAR == Y) & (st.fp.k == k)].copy()
    parts = [c for c, on in [('ped', 'history' in use), ('dna', 'parent_dna' in use)] if on]
    for cl in ['C1', 'C2']:
        s = st.slopes.get((cl, Y), 1.0) if k == 1 else 1.0
        m = fp.CL == cl
        fp.loc[m, 'F'] = s * fp.loc[m, [f'gca_{p}' for p in parts]].mean(1) if parts else 0.0
        fp.loc[m, 'T'] = s * fp.loc[m, [f'tst_{p}' for p in parts]].mean(1) if parts else 0.0
        fp.loc[m, 'F_ped'] = s * fp.loc[m, 'gca_ped'] / max(len(parts), 1) if 'ped' in parts else 0.0
        fp.loc[m, 'F_dna'] = s * fp.loc[m, 'gca_dna'] / max(len(parts), 1) if 'dna' in parts else 0.0
    d = lp.merge(fp[['POP', 'F', 'T', 'F_ped', 'F_dna', 'P1', 'P2', 'TESTER', 'GEN', 'n_par_seen', 'tester_seen', 'gca_parent_history', 'train_last']], on='POP')
    d['D'] = d.D if 'line_dna' in use else 0.0
    d['gca'] = d.F + d.D; d['testcross'] = d.gca + (d['T'] if 'tester' in use else 0.0)
    d['tier'] = np.select([(d.n_par_seen == 2) & d.tester_seen, d.n_par_seen >= 1], ['high', 'medium'], 'low')
    if Y == 2008 and k == 1 and st.rep_lines is not None:
        d = d.merge(st.rep_lines[['LINE_KEY', 'sd', 'explanation', 'P1_evidence', 'P2_evidence', 'tester_evidence', 'D_drivers']], on='LINE_KEY', how='left')
    return d


def plan(d, budget, strategy, tau=0.5):
    """Which lines get plots. strategy: 'recommended' (tilt tau), 'conservative' (even spread), 'aggressive' (top predicted)."""
    d = d.copy(); d['plant'] = False
    for cl in ['C1', 'C2']:
        idx = d.index[d.CL == cl]; s = d.loc[idx]; N = len(s)
        if N == 0: continue
        codes, fam = np.unique(s.POP.values, return_inverse=True); sizes = np.bincount(fam)
        fz = s.groupby('POP').F.first(); fz = ((fz - fz.mean()) / (fz.std() or 1)).reindex(codes).fillna(0).values
        n = max(int(round(budget * N)), 1)
        if strategy == 'aggressive': sel = A50.select(s.gca.values, fam, n, None)
        elif strategy == 'conservative': sel = A50.select(s.D.values, fam, n, A50.quota('even', sizes, budget, fz))
        else: sel = A50.select(s.D.values if s.D.abs().sum() > 0 else s.gca.values, fam, n, A50.quota(('tilt', tau), sizes, budget, fz))
        d.loc[idx[sel], 'plant'] = True
    return d


def evaluate(st, d, Y):
    """Selection quality against season Y's observed line testcross yield (the standard ranking metric), vs the
    traditional baseline (parents' record + the same tester estimate) and random. Evaluation only; nothing is tuned on it."""
    t = st.tl[st.tl.YEAR == Y][['LINE_KEY', 'y_tot_YLD']]
    e = d.merge(t, on='LINE_KEY').dropna(subset=['y_tot_YLD'])
    if not len(e): return None
    e['pred'] = e.gca + e['T']; e['trad'] = e.gca_parent_history + e['T'] + np.random.default_rng(0).normal(0, 1e-6, len(e))
    out = {}
    for cl, g in e.groupby('CL'):
        k10 = max(int(round(.1 * len(g))), 1); top = set(g.nlargest(k10, 'y_tot_YLD').LINE_KEY)
        out[cl] = dict(line_r=np.corrcoef(g.pred, g.y_tot_YLD)[0, 1] if g.pred.std() > 0 else np.nan,
                       line_r_parent_history=np.corrcoef(g.trad, g.y_tot_YLD)[0, 1],
                       top10_hit=len(set(g.nlargest(k10, 'pred').LINE_KEY) & top) / k10,
                       top10_hit_parent_history=len(set(g.nlargest(k10, 'trad').LINE_KEY) & top) / k10,
                       planted_value=g[g.plant].y_tot_YLD.mean() - g.y_tot_YLD.mean() if 'plant' in g else np.nan, n=len(g))
    return pd.DataFrame(out).T


def data_used(st, Y, k, lead, gen_use, env_use, d=None):
    """Human-readable list of every data source behind a prediction, tagged Hackathon / Public."""
    last = Y - k; c = st.counts; rows = []
    h = c[c.YEAR <= last] if c is not None else None
    if 'history' in gen_use and h is not None:
        rows.append(('Hackathon', f'Field trials {int(h.YEAR.min())}-{last}', f'{int(h.plots.sum()):,} plots, {int(h.families.sum()):,} family-seasons, {int(h.locations.sum()):,} location-seasons'))
        rows.append(('Hackathon', 'Pedigree', 'parents of every family, recurrent parent for backcrosses, generation'))
    if 'parent_dna' in gen_use: rows.append(('Hackathon', 'Parent genotypes', '518 genotyped parents x 2,911 SNPs'))
    if 'line_dna' in gen_use:
        fi = st.fit[(st.fit.year == Y) & (st.fit.k == k)] if st.fit is not None else None
        rows.append(('Hackathon', 'Line genotypes (HMM-imputed)', f'{int(fi.n_train_lines.sum()):,} training lines' if fi is not None and len(fi) else 'training lines of earlier seasons'))
    if 'tester' in gen_use: rows.append(('Hackathon', 'Tester', 'tester identity and its earlier families'))
    lead_txt = dict(LEADS_TXT)[lead]
    if 'cropmodel' in env_use: rows.append(('Public', 'NASA POWER daily weather + SSURGO soil', f'climatology of earlier seasons' + ('' if lead == 'jan' else f' + season {Y} weather to {lead_txt}')))
    if 'nass' in env_use: rows.append(('Public', 'USDA NASS county corn yields', f'county history to {Y - 1}'))
    for key in ['gridmet', 'drought', 'storms', 'modis', 'landsat']:
        if key in env_use: rows.append(('Public', ENV_SOURCES[key][1], f'to {lead_txt}' if lead != 'jan' else 'earlier seasons only (January)'))
    return pd.DataFrame(rows, columns=['source', 'data', 'what was used'])


LEADS_TXT = [(k, t) for k, _, _, t in LEADS]


# ------------------------------------------------------------------ sites (environment-specific)
def site_config(env_use, lead):
    """Map selected environment sources to the closest validated precomputed configuration."""
    sat = [s for s in ['modis', 'landsat'] if s in env_use]
    if sat and lead in ('jun', 'jul', 'aug'):
        cfg = {('modis',): '+modis', ('landsat',): '+ls_all', ('modis', 'landsat'): 'wx+modis+ls_all'}[tuple(sat)]
        return 'sat', cfg
    extra = [s for s in ['gridmet', 'drought', 'storms'] if s in env_use]
    cfg = 'all' if len(extra) > 1 else ({'gridmet': 'gridmet', 'drought': '+drought', 'storms': '+storms'}[extra[0]] if extra else 'base')
    return 'site', cfg


def site_table(st, Y, lead, env_use):
    src, cfg = site_config(env_use, lead)
    if 'cropmodel' not in env_use and 'nass' not in env_use:
        return None, 'Select at least the crop model or county history for site forecasts.'
    if src == 'sat':
        m = {'jun': 'end_Jun', 'jul': 'end_Jul', 'aug': 'end_Aug'}[lead]
        p = st.sat[(st.sat.target == 'YLD') & (st.sat.year == Y) & (st.sat.lead == m) & (st.sat.config == cfg)][['cl', 'ENV', 'pred', 'truth']]
        return p.rename(columns={'truth': 'observed'}), f'site model: crop model + county history + {cfg} (validated in satellite Exp 3)'
    p = st.site[(st.site.year == Y) & (st.site.lead == lead) & (st.site.cfg == cfg)][['cl', 'ENV', 'pred', 'y']]
    return p.rename(columns={'y': 'observed'}), f'site model: {cfg} (validated in inseason Exp 6a)'


# ------------------------------------------------------------------ custom cross (scored live)
def score_cross(st, cl, P1, P2, gen, tester, Y, k, n=200, seed=0):
    last = Y - k
    PG = H.load_parent_geno(cl); PG = PG.fillna(PG.mean()).fillna(0.0)
    hist = st.pops[(st.pops.CL == cl) & (st.pops.YEAR <= last)].dropna(subset=[TC]).reset_index(drop=True)
    rp = P1 if gen == 'BC' else None
    tgt = pd.DataFrame([dict(POP='custom', CL=cl, P1=P1, P2=P2, RP=rp, TESTER=tester, GEN=gen, YEAR=Y)])
    res = {}
    for m, tag in [('ped_gca', 'ped'), ('par_genomic', 'dna')]:
        o = F.fit(m, hist, tgt, TC, PG, **F.tune(m, hist, TC, last + 1, PG)); res[tag] = (float(o.gca.iloc[0]), float(o.tester.iloc[0]))
    s = st.slopes.get((cl, Y), 1.0) if k == 1 else 1.0
    Fv = s * np.mean([res['ped'][0], res['dna'][0]]); Tv = s * np.mean([res['ped'][1], res['dna'][1]])
    spread = best5 = np.nan
    key = f'{cl}_{Y}_{k}'
    if st.betas is not None and key in st.betas and P1 in PG.index and P2 in PG.index:
        beta = st.betas[key].astype(float); sim = gp.FamilySimulator(seed=seed)
        G = sim.progeny(np.rint(PG.loc[P1].values), np.rint(PG.loc[P2].values), gen, 'a' if gen == 'BC' else None, n=n)
        fi = st.fit[(st.fit.cl == cl) & (st.fit.year == Y) & (st.fit.k == k)]; sl = float(fi.slope_D.iloc[0]) if len(fi) else 1.0
        v = sl * (G @ beta); v = v - v.mean(); spread = float(v.std()); best5 = float(np.mean(np.sort(v)[-max(n // 20, 1):]))
    seen = set(hist.P1) | set(hist.P2)
    ev = []
    for p in [P1, P2]:
        h = hist[(hist.P1 == p) | (hist.P2 == p)]
        ev.append(f'{p}: ' + (f'{len(h)} earlier families (mean observed {h[TC].mean():+.1f}), last {int(h.YEAR.max())}' if len(h) else 'never tested') +
                  ('; genotyped' if p in PG.index else '; not genotyped'))
    th = hist[hist.TESTER == tester]
    return dict(family_value=Fv, tester=Tv, family_testcross=Fv + Tv, from_pedigree=s * res['ped'][0] / 2, from_dna=s * res['dna'][0] / 2,
                line_spread_sd=spread, best5pct_line=Fv + best5 if best5 == best5 else np.nan,
                prob_beats_average=0.5 * (1 + math.erf(Fv / (11.0 * math.sqrt(2)))), evidence=ev,
                tester_evidence=f'{tester}: {len(th)} earlier families' + (f' (mean observed {th[TC].mean():+.1f})' if len(th) else ''),
                parents_seen=int(P1 in seen) + int(P2 in seen))


# ------------------------------------------------------------------ timelines (analytics)
def line_timeline(st, key, Y, gen_use):
    rows = []
    for k in [3, 2, 1]:
        d = line_table(st, Y, k, gen_use); r = d[d.LINE_KEY == key]
        if not len(r): continue
        r = r.iloc[0]
        rows.append(dict(date=dt.date(Y - k, *HARVEST_DONE), k=k, gca=r.gca, family=r.F, own_dna=r.D, n_par_seen=int(r.n_par_seen),
                         rank_pct=float((d[d.CL == r.CL].gca < r.gca).mean() * 100), event=f'season {Y - k} trials become available'))
    return pd.DataFrame(rows)


def family_timeline(st, pop, Y, gen_use):
    rows = []
    for k in [3, 2, 1]:
        d = line_table(st, Y, k, gen_use); r = d[d.POP == pop]
        if not len(r): continue
        r = r.iloc[0]; cl = r.CL; fam = d[d.CL == cl].groupby('POP').F.first()
        rows.append(dict(date=dt.date(Y - k, *HARVEST_DONE), k=k, F=r.F, from_pedigree=r.F_ped, from_dna=r.F_dna, n_par_seen=int(r.n_par_seen),
                         rank_pct=float((fam < r.F).mean() * 100), event=f'season {Y - k} trials become available'))
    return pd.DataFrame(rows)


def site_timeline(st, env):
    Y = int(env.rsplit('_', 1)[1]); rows = []
    for key, m, dd, lab in LEADS:
        p = st.site[(st.site.ENV == env) & (st.site.lead == key) & (st.site.cfg == 'base')]
        if len(p): rows.append(dict(date=dt.date(Y, m, dd), lead=lab, series='Crop model + county history', pred=p.pred.mean(), observed=p.y.mean()))
        if key in ('jun', 'jul', 'aug') and st.sat is not None:
            q = st.sat[(st.sat.ENV == env) & (st.sat.target == 'YLD') & (st.sat.lead == {'jun': 'end_Jun', 'jul': 'end_Jul', 'aug': 'end_Aug'}[key]) & (st.sat.config == '+modis')]
            if len(q): rows.append(dict(date=dt.date(Y, m, dd), lead=lab, series='+ MODIS NDVI', pred=q.pred.mean(), observed=q.truth.mean()))
        if key == 'jan' and st.sat is not None:
            q = st.sat[(st.sat.ENV == env) & (st.sat.target == 'YLD') & (st.sat.lead == 'end_Jun') & (st.sat.config == 'base')]
            if len(q) and len(p): rows.append(dict(date=dt.date(Y, m, dd), lead=lab, series='+ MODIS NDVI', pred=p.pred.mean(), observed=p.y.mean()))
    return pd.DataFrame(rows)


def accuracy_over_time(st, Y, gen_use):
    """Cluster-level accuracy of the line and site forecasts at each data-availability date (validation view)."""
    rows = []
    for k in [3, 2, 1]:
        d = line_table(st, Y, k, gen_use); e = evaluate(st, d.assign(plant=False), Y)
        if e is not None: rows.append(dict(date=dt.date(Y - k, *HARVEST_DONE), what='Line value (DNA + pedigree)', r=float(e.line_r.mean())))
    if st.site is not None:
        for key, m, dd, lab in LEADS:
            p = st.site[(st.site.year == Y) & (st.site.lead == key) & (st.site.cfg == 'base')]
            if len(p): rows.append(dict(date=dt.date(Y, m, dd), what='Site yield level', r=float(p.groupby('cl').apply(lambda g: np.corrcoef(g.pred, g.y)[0, 1]).mean())))
    return pd.DataFrame(rows)

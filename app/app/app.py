# Maize line-advancement advisor — three faces:
#   Farmer view   the recommended 2008 plan in plain language, a few charts, what improves
#   Advanced      choose data sources, budget/strategy, a custom cross, and the prediction date (custom or best)
#   Analytics     how a prediction for a line / family / location changed as each new data point arrived
#   streamlit run app/app.py
import datetime as dt, numpy as np, pandas as pd, plotly.graph_objects as go, plotly.express as px, streamlit as st
import core as C

st.set_page_config(page_title='Maize advancement advisor', layout='wide', initial_sidebar_state='collapsed')
st.markdown("""<style>
div[data-testid="stMetric"] {background:#161B22;border:1px solid #2A313C;border-radius:12px;padding:14px 16px;}
div[data-testid="stMetricValue"] {font-size:1.9rem;}
.pill {display:inline-block;padding:2px 9px;border-radius:999px;font-size:.78rem;margin-right:6px;font-weight:600}
.hk {background:#12324a;color:#56B4E9}.pb {background:#3a2c0e;color:#E69F00}
.step {background:#161B22;border-left:4px solid #56B4E9;border-radius:8px;padding:10px 14px;margin:6px 0}
.small {color:#9AA5B1;font-size:.85rem}
</style>""", unsafe_allow_html=True)
TPL = dict(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(size=13), margin=dict(l=10, r=10, t=40, b=10))


@st.cache_resource
def store(): return C.Store()


@st.cache_data(show_spinner=False)
def lines_cached(Y, k, use): return C.line_table(store(), Y, k, list(use))


S = store()
if not S.ready:
    st.error('Precomputed tables not found. Run `python app/precompute.py` first (about 40 minutes).'); st.stop()
tab1, tab2, tab3 = st.tabs(['Farmer view', 'Advanced', 'Analytics'])

# ======================================================================= FARMER VIEW
with tab1:
    ev = S.eval_strat.set_index('strategy'); gain, full = ev.loc['tilt0.5', 'gain'], 4.74
    n_all, n_adv = 15968, len(S.adv); plots_all, plots_used = 87286, 87286 - 74361
    st.markdown('## The 2008 plan: plant fewer lines, get more genetic gain')
    st.markdown(f"Use DNA to choose **{n_adv:,} of {n_all:,} new lines** (15% of plots), test each at every location, "
                f"and advance the best 5% at harvest. Validated on the real 2008 results.")
    c = st.columns(4)
    c[0].metric('Lines to plant', f'{n_adv:,}', f'of {n_all:,} candidates', delta_color='off')
    c[1].metric('Genetic gain', f'{gain:.2f} bu/ac', f'+{(gain / full - 1) * 100:.0f}% vs planting everything')
    c[2].metric('Plots saved', f'{87286 - plots_used:,}', f'{(1 - plots_used / plots_all) * 100:.0f}% of the field budget', delta_color='off')
    c[3].metric('Plot cost saved', f'${(87286 - plots_used) * 150 / 1e6:.1f}M', 'at $150 per plot (assumed)', delta_color='off')
    a, b = st.columns([1.35, 1])
    with a:
        names = [('tilt0.5', 'Our plan (15% of plots)', C.COL['ours']), ('plant_all', 'Plant everything (100%)', C.COL['all']),
                 ('parent_history', 'Traditional: parents\' record', C.COL['trad']), ('random', 'Random 15%', C.COL['rand'])]
        vals = [gain, full, ev.loc['parent_history', 'gain'], ev.loc['random', 'gain']]
        fig = go.Figure(go.Bar(x=vals, y=[n for _, n, _ in names], orientation='h', marker_color=[c_ for _, _, c_ in names],
                               text=[f'{v:.2f}' for v in vals], textposition='outside'))
        fig.update_layout(title='Genetic gain of the lines advanced (bu/ac, 2008)', xaxis=dict(range=[0, max(vals) * 1.2], showgrid=False),
                          yaxis=dict(autorange='reversed'), height=300, **TPL)
        st.plotly_chart(fig, use_container_width=True)
    with b:
        fig = go.Figure(go.Pie(labels=['Plots used', 'Plots saved'], values=[plots_used, plots_all - plots_used], hole=.62,
                               marker=dict(colors=[C.COL['ours'], '#2A313C']), textinfo='percent', sort=False))
        fig.update_layout(title='Field plots', height=300, showlegend=True, legend=dict(orientation='h'), **TPL)
        fig.add_annotation(text=f'{plots_used:,}<br>plots', showarrow=False, font=dict(size=16))
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('### What to do this season')
    for i, t in enumerate([f'**Plant the {n_adv:,} recommended lines**, drawn from {S.adv.POP.nunique()} of 157 families. Every good family keeps some plots; better-predicted families get more.',
                           '**Test each planted line at every location** its family goes to. Extra locations are worth more than extra lines (about 1.8x the gain at equal cost).',
                           '**At harvest, advance the top 5%** of lines on field yield.',
                           '**Plan next crosses** from the shortlist below: pairs of parents predicted to give the best families.'], 1):
        st.markdown(f'<div class="step">{i}. {t}</div>', unsafe_allow_html=True)
    a, b = st.columns([1.2, 1])
    with a:
        f = S.rep_fams.sort_values('lines_planted_recommended', ascending=False).head(12) if S.rep_fams is not None else None
        if f is not None:
            fig = go.Figure(go.Bar(x=f.lines_planted_recommended, y=f.POP, orientation='h', marker=dict(color=f.F, colorscale='Blues', showscale=True, colorbar=dict(title='family<br>value')),
                                   text=[f'{v:+.1f}' for v in f.F], textposition='outside'))
            fig.update_layout(title='Families getting the most plots (colour = predicted family value, bu/ac)', yaxis=dict(autorange='reversed'), height=420, **TPL)
            st.plotly_chart(fig, use_container_width=True)
    with b:
        st.markdown('#### Next crosses to make')
        if S.crosses is not None:
            x = S.crosses[S.crosses.shortlist].groupby('CL').head(5)[['CL', 'P1', 'P2', 'family_gca', 'best5pct_line_gca', 'prob_family_beats_avg']]
            st.dataframe(x.rename(columns={'family_gca': 'family value', 'best5pct_line_gca': 'best lines', 'prob_family_beats_avg': 'P(beats avg)'}).round(2), hide_index=True, use_container_width=True)
            st.markdown('<span class="small">Ranked from all data through 2008; a relative ranking, not a yield guarantee.</span>', unsafe_allow_html=True)
        st.download_button('Download the 2008 advancement list (CSV)', S.adv.to_csv(index=False), 'advancement_list_2008.csv', use_container_width=True)
    st.markdown('<span class="small">Decision sealed before the 2008 results were opened; evaluated once. Plot cost is an assumption from the course slides.</span>', unsafe_allow_html=True)

# ======================================================================= ADVANCED
with tab2:
    left, right = st.columns([1, 2.6], gap='large')
    with left:
        st.markdown('#### Prediction')
        Y = st.selectbox('Target season', S.years[::-1], index=0)
        mode = st.radio('Prediction date', ['Best prediction date', 'Custom date'], horizontal=True)
        d = st.date_input('Date', dt.date(Y, 1, 15), min_value=dt.date(2001, 1, 1), max_value=dt.date(Y, 12, 31)) if mode == 'Custom date' else None
        cut = C.cutoff(Y, d, best=(mode == 'Best prediction date'))
        st.markdown('#### Data sources')
        st.markdown('<span class="pill hk">Hackathon</span>', unsafe_allow_html=True)
        gen_use = [k for k, (_, lab) in C.GEN_SOURCES.items() if st.checkbox(lab, True, key=f'g_{k}')]
        st.markdown('<span class="pill pb">Public</span>', unsafe_allow_html=True)
        env_default = {'cropmodel', 'nass'}
        env_use = [k for k, (_, lab) in C.ENV_SOURCES.items() if st.checkbox(lab, k in env_default, key=f'e_{k}')]
        st.markdown('#### Plan')
        budget = st.slider('Share of plots', 0.05, 0.50, 0.15, 0.01, format='%.2f')
        strategy = st.radio('Selection', ['recommended', 'conservative', 'aggressive'], horizontal=True,
                            help='recommended: keep every family, tilt toward predicted-good ones | conservative: even spread | aggressive: top predicted lines only')
        tau = st.slider('Tilt strength (recommended)', 0.0, 2.0, 0.5, 0.25) if strategy == 'recommended' else 0.5
        cost = st.number_input('Cost per plot ($)', 10, 1000, 150, 10)
    with right:
        k, lead = cut['k'], cut['lead']; last = Y - k
        st.markdown(f"#### Season {Y} · trial data through **{last}** · in-season information: **{dict(C.LEADS_TXT)[lead]}**")
        if cut['note']: st.info(cut['note'])
        dl = lines_cached(Y, k, tuple(sorted(gen_use)))
        pl = C.plan(dl, budget, strategy, tau)
        ev_ = C.evaluate(S, pl, Y)
        base = C.plan(dl.assign(gca=dl.gca_parent_history + dl['T'], D=0.0, F=dl.gca_parent_history), budget, 'aggressive')
        evb = C.evaluate(S, base, Y)
        m = st.columns(4)
        m[0].metric('Lines planted', f'{int(pl.plant.sum()):,}', f'of {len(pl):,}', delta_color='off')
        m[1].metric('Families kept', f'{pl[pl.plant].POP.nunique()}', f'of {pl.POP.nunique()}', delta_color='off')
        m[2].metric('Plot cost saved', f'${(1 - budget) * len(pl) * 5 * cost / 1e6:.1f}M', 'about 5 plots per line', delta_color='off')
        if ev_ is not None:
            ph = ' (2008: post-hoc)' if Y == 2008 else ''
            v, vb = ev_.planted_value.mean(), evb.planted_value.mean()
            m[3].metric('Value of planted lines' + ph, f'{v:+.2f} bu/ac', f'{v - vb:+.2f} vs traditional parent record')
            m2 = st.columns(3)
            m2[0].metric('Line accuracy (r)' + ph, f'{ev_.line_r.mean():.2f}', f'{ev_.line_r.mean() - ev_.line_r_parent_history.mean():+.2f} vs traditional')
            m2[1].metric('True top-10% caught' + ph, f'{ev_.top10_hit.mean():.0%}', f'{(ev_.top10_hit.mean() - ev_.top10_hit_parent_history.mean()) * 100:+.0f} pts vs traditional (random 10%)')
            g = S.abl[(S.abl.strategy == {'recommended': 'tilt0.5', 'conservative': 'markers_within', 'aggressive': 'kappa+0'}[strategy])] if S.abl is not None else None
            if g is not None and len(g):
                r_ = g.iloc[(g.budget - budget).abs().argsort()[:1]].iloc[0]
                m2[2].metric('Field-stage gain, replay 2004-07', f'{r_.gain:.2f} bu/ac', f'{(r_.vs_full - 1) * 100:+.0f}% vs planting everything; P10 {r_.p10:.2f}')
        st.markdown('##### Recommended lines')
        show = pl[pl.plant].sort_values('gca', ascending=False).head(30).copy()
        if 'explanation' not in show or show.explanation.isna().all():
            show['explanation'] = [f'family {r.F:+.1f} [pedigree/record {r.F_ped:+.1f}, parent DNA {r.F_dna:+.1f}] + own DNA vs siblings {r.D:+.1f}'
                                   + (f' + tester {r.T:+.1f}' if 'tester' in gen_use else '') for r in show.itertuples()]
        st.dataframe(show[['LINE_KEY', 'POP', 'gca', 'testcross', 'tier', 'n_par_seen', 'explanation']].round(2), hide_index=True, use_container_width=True, height=300)
        st.download_button('Download the full plan (CSV)', pl[pl.plant].to_csv(index=False), f'plan_{Y}.csv')
        if True:
            st.markdown('##### Site forecasts (environment-specific)')
            sp, msg = C.site_table(S, Y, lead, env_use)
            if sp is None: st.warning(msg)
            else:
                st.markdown(f'<span class="small">{msg}</span>', unsafe_allow_html=True)
                fig = px.scatter(sp, x='pred', y='observed', color='cl', color_discrete_sequence=[C.COL['ours'], C.COL['base']], opacity=.75)
                lo, hi = sp[['pred', 'observed']].min().min(), sp[['pred', 'observed']].max().max()
                fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode='lines', line=dict(color='#5A6472', dash='dot'), showlegend=False))
                r = sp.groupby('cl').apply(lambda g: np.corrcoef(g.pred, g.observed)[0, 1]).mean()
                fig.update_layout(title=f'Predicted vs observed site yield (r {r:.2f}{", post-hoc" if Y == 2008 else ""})', height=330, xaxis_title='predicted bu/ac', yaxis_title='observed bu/ac', **TPL)
                st.plotly_chart(fig, use_container_width=True)
        with st.expander('Custom cross: predict any pair of parents', expanded=False):
            cl = st.selectbox('Cluster', ['C1', 'C2'], key='xcl')
            fam_c = S.pops[(S.pops.CL == cl) & (S.pops.YEAR <= last)]
            pars = sorted(set(fam_c.P1) | set(fam_c.P2)); testers = fam_c.TESTER.value_counts().index.tolist()
            x1, x2 = st.columns(2)
            P1 = x1.selectbox('Parent 1', pars, key='xp1'); P2 = x2.selectbox('Parent 2', pars, index=min(1, len(pars) - 1), key='xp2')
            x1, x2 = st.columns(2)
            gen = x1.selectbox('Generation', ['F2', 'BC', 'DH'], key='xg'); tester = x2.selectbox('Tester', testers, key='xt')
            if st.button('Predict this cross', use_container_width=True):
                with st.spinner('scoring...'):
                    r = C.score_cross(S, cl, P1, P2, gen, tester, Y, k)
                q = st.columns(3)
                q[0].metric('Family value', f'{r["family_value"]:+.1f}'); q[1].metric('Best 5% of lines', f'{r["best5pct_line"]:+.1f}' if r['best5pct_line'] == r['best5pct_line'] else 'n/a')
                q[2].metric('P(beats average)', f'{r["prob_beats_average"]:.0%}')
                st.markdown(f"<span class='small'>from parents' record {r['from_pedigree']:+.1f} · from parent DNA {r['from_dna']:+.1f} · tester {r['tester']:+.1f}<br>"
                            + '<br>'.join(r['evidence']) + f"<br>{r['tester_evidence']}</span>", unsafe_allow_html=True)
        st.markdown('##### Data points used for these predictions')
        du = C.data_used(S, Y, k, lead, gen_use, env_use)
        st.dataframe(du, hide_index=True, use_container_width=True)

# ======================================================================= ANALYTICS
with tab3:
    a, b, c_ = st.columns([1, 1, 2])
    kind = a.radio('Query', ['Line', 'Family', 'Location'], horizontal=True)
    Y3 = b.selectbox('Season', S.years[::-1], key='y3')
    gen_all = list(C.GEN_SOURCES)
    d1 = lines_cached(Y3, 1, tuple(sorted(gen_all)))
    if kind == 'Line':
        default = d1.sort_values('gca', ascending=False).LINE_KEY.iloc[0]
        key = c_.selectbox('Line', d1.sort_values('gca', ascending=False).LINE_KEY.tolist(), index=0)
        tl = C.line_timeline(S, key, Y3, gen_all)
        obs = S.tl[(S.tl.LINE_KEY == key)]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tl.date, y=tl.family, name='family part', marker_color=C.COL['base'], opacity=.85))
        fig.add_trace(go.Bar(x=tl.date, y=tl.own_dna, name='own DNA vs siblings', marker_color=C.COL['good'], opacity=.85))
        fig.add_trace(go.Scatter(x=tl.date, y=tl.gca, name='predicted GCA', mode='lines+markers+text', line=dict(color=C.COL['ours'], width=3),
                                 marker=dict(size=11), text=[f'{v:+.1f}' for v in tl.gca], textposition='top center'))
        fig.update_layout(barmode='relative', title=f'{key}: prediction as each season of trial data arrived', yaxis_title='bu/ac vs program average', height=420, **TPL)
        st.plotly_chart(fig, use_container_width=True)
        tl['change'] = tl.gca.diff(); tl['what changed'] = [('first prediction' if i == 0 else
            ('a parent was tested for the first time' if r.n_par_seen > tl.n_par_seen.iloc[i - 1] else 'more relatives tested; DNA model retrained'))
            for i, r in enumerate(tl.itertuples())]
        st.dataframe(tl[['date', 'event', 'gca', 'change', 'family', 'own_dna', 'n_par_seen', 'rank_pct', 'what changed']].round(2).rename(columns={'rank_pct': 'percentile in cluster', 'n_par_seen': 'parents seen'}), hide_index=True, use_container_width=True)
        if len(obs): st.markdown(f"<span class='small'>Observed at harvest {Y3}: within-family deviation {obs.y_w_YLD.iloc[0]:+.1f}, testcross total {obs.y_tot_YLD.iloc[0]:+.1f} bu/ac{' (post-hoc)' if Y3 == 2008 else ''}.</span>", unsafe_allow_html=True)
    elif kind == 'Family':
        fams = d1.groupby('POP').F.first().sort_values(ascending=False)
        pop = c_.selectbox('Family', fams.index.tolist())
        tf = C.family_timeline(S, pop, Y3, gen_all); obs = S.tf[S.tf.POP == pop]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=tf.date, y=tf.from_pedigree, name="parents' track record", marker_color=C.COL['base']))
        fig.add_trace(go.Bar(x=tf.date, y=tf.from_dna, name='parent DNA', marker_color=C.COL['good']))
        fig.add_trace(go.Scatter(x=tf.date, y=tf.F, name='predicted family value', mode='lines+markers+text', line=dict(color=C.COL['ours'], width=3), marker=dict(size=11),
                                 text=[f'{v:+.1f}' for v in tf.F], textposition='top center'))
        if len(obs) and obs[C.TC].notna().any():
            fig.add_trace(go.Scatter(x=[dt.date(Y3, 10, 31)], y=[obs[C.TC].iloc[0]], name='observed' + (' (post-hoc)' if Y3 == 2008 else ''), mode='markers',
                                     marker=dict(symbol='star', size=18, color=C.COL['warn'])))
        fig.update_layout(barmode='relative', title=f'{pop}: family prediction over time', yaxis_title='bu/ac vs program average', height=420, **TPL)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(tf.round(2), hide_index=True, use_container_width=True)
    else:
        envs = sorted(S.site[S.site.year == Y3].ENV.unique())
        env = c_.selectbox('Location', envs)
        ts = C.site_timeline(S, env)
        fig = go.Figure()
        for sname, colr in [('Crop model + county history', C.COL['ours']), ('+ MODIS NDVI', C.COL['good'])]:
            g = ts[ts.series == sname]
            if len(g): fig.add_trace(go.Scatter(x=g.date, y=g.pred, name=sname, mode='lines+markers', line=dict(color=colr, width=3), marker=dict(size=10)))
        if len(ts): fig.add_hline(y=ts.observed.iloc[0], line=dict(color=C.COL['warn'], dash='dash'), annotation_text='observed at harvest' + (' (post-hoc)' if Y3 == 2008 else ''))
        fig.update_layout(title=f'{env}: site yield forecast through the season', yaxis_title='bu/ac', height=420, **TPL)
        st.plotly_chart(fig, use_container_width=True)
        g = ts[ts.series == 'Crop model + county history'][['lead', 'pred']].copy(); g['change'] = g.pred.diff()
        nd = {'January (pre-season)': 'crop-model climatology + county yield history', 'Full season (hindcast)': 'full-season weather (hindcast, not a forecast)'}
        g['new data point'] = [nd.get(l_, 'NASA POWER weather up to this date') for l_ in g.lead]
        st.dataframe(g.round(1), hide_index=True, use_container_width=True)
    st.markdown('##### How accurate the forecasts were at each date (this season, all lines / all locations)')
    acc = C.accuracy_over_time(S, Y3, gen_all)
    if len(acc):
        fig = px.line(acc, x='date', y='r', color='what', markers=True, color_discrete_sequence=[C.COL['ours'], C.COL['good']])
        fig.update_traces(line=dict(width=3), marker=dict(size=10))
        fig.update_layout(yaxis=dict(range=[0, 1], title='r with observed'), height=340, title='Accuracy vs date' + (' (2008: post-hoc)' if Y3 == 2008 else ''), **TPL)
        st.plotly_chart(fig, use_container_width=True)

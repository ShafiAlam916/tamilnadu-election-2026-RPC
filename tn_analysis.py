import pandas as pd
import numpy as np
from tabulate import tabulate
import warnings
warnings.filterwarnings('ignore')

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
df26_raw = pd.read_csv('/mnt/user-data/uploads/1779679097032_tn_2026_results.csv')
df21_raw = pd.read_csv('/mnt/user-data/uploads/1779679097034_tn_2021_results.csv')
electors = pd.read_csv('/mnt/user-data/uploads/1779679097034_tn_2026_electors.csv')
master   = pd.read_csv('/mnt/user-data/uploads/1779679097033_constituency_master.csv')

df26 = df26_raw.copy()
df21 = df21_raw.copy()

# ─── TOP-3 PARTIES (by total votes) ───────────────────────────────────────────
TOP3_26 = ['TVK', 'DMK', 'AIADMK']
TOP3_21 = ['DMK', 'AIADMK', 'BJP']    # 2021 top 3 by seats / vote share

# ─── COMPUTE 2026 TURNOUT ─────────────────────────────────────────────────────
# electors has total registered voters per constituency
electors_clean = electors[['ac_number','total']].dropna(subset=['ac_number'])
electors_clean['ac_number'] = electors_clean['ac_number'].astype(int)

# total votes cast per constituency in 2026 = sum of all candidate votes incl NOTA
votes_cast_26 = (df26.groupby('ac_number')['votes']
                      .sum()
                      .reset_index()
                      .rename(columns={'votes':'total_votes_cast'}))
votes_cast_26 = votes_cast_26.merge(electors_clean, on='ac_number', how='left')
votes_cast_26['turnout_26'] = (votes_cast_26['total_votes_cast'] / votes_cast_26['total'] * 100).round(2)

# merge turnout back to df26
df26 = df26.merge(votes_cast_26[['ac_number','turnout_26']], on='ac_number', how='left')

# total votes cast per constituency 2021 (derive from turnout col which is constituency-level)
votes_cast_21 = (df21.groupby(['ac_number','constituency','region','reserved'])
                      .agg(total_votes_cast=('votes','sum'), turnout_21=('turnout','first'))
                      .reset_index())

# ─── WINNER DERIVATION ────────────────────────────────────────────────────────
def get_winners(df, turnout_col=None):
    """Return one row per constituency: winner candidate, party, votes, margin."""
    df = df.copy()
    df['rank'] = df.groupby('ac_number')['votes'].rank(method='first', ascending=False)
    winners = df[df['rank'] == 1][['ac_number','constituency','region','reserved','candidate','party','votes']].copy()
    runners = df[df['rank'] == 2][['ac_number','votes']].rename(columns={'votes':'runner_votes'})
    winners = winners.merge(runners, on='ac_number', how='left')
    winners['margin'] = winners['votes'] - winners['runner_votes']
    # total valid votes per constituency
    totals = df.groupby('ac_number')['votes'].sum().reset_index().rename(columns={'votes':'total_valid'})
    winners = winners.merge(totals, on='ac_number', how='left')
    winners['win_pct'] = (winners['votes'] / winners['total_valid'] * 100).round(2)
    if turnout_col:
        t = df[['ac_number', turnout_col]].drop_duplicates()
        winners = winners.merge(t, on='ac_number', how='left')
    return winners

winners26 = get_winners(df26, 'turnout_26')
winners21 = get_winners(df21, 'turnout')

# merge region/reserved into votes_cast_21 if not present
votes_cast_21 = votes_cast_21.merge(
    master[['ac_number','region','reserved']], on='ac_number', how='left'
)

def pprint(title, df, idx=False):
    print(f"\n{'═'*70}")
    print(f"  {title}")
    print(f"{'═'*70}")
    print(tabulate(df, headers='keys', tablefmt='rounded_outline',
                   showindex=idx, floatfmt='.2f'))

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 2 — Top & Bottom 5 individual candidate vote shares by party
# ══════════════════════════════════════════════════════════════════════════════
def cand_vote_share(df, year, turnout_col):
    totals = df.groupby('ac_number')['votes'].sum().reset_index().rename(columns={'votes':'total_valid'})
    d = df.merge(totals, on='ac_number')
    d['vote_pct'] = (d['votes'] / d['total_valid'] * 100).round(2)
    d = d[d['party'].isin(TOP3_26 if year == 2026 else ['DMK','AIADMK','BJP','INC','NTK'])]
    d = d[~d['candidate'].str.upper().str.contains('NOTA', na=False)]
    return d[['candidate','party','constituency','votes','vote_pct']]

cand26 = cand_vote_share(df26, 2026, 'turnout_26')
cand21 = cand_vote_share(df21, 2021, 'turnout')

def top_bottom5(df, year):
    rows = []
    parties = df['party'].unique()
    for p in sorted(parties):
        sub = df[df['party'] == p].sort_values('vote_pct', ascending=False)
        top5 = sub.head(5).assign(rank_type='Top 5')
        bot5 = sub.tail(5).assign(rank_type='Bottom 5')
        rows.append(pd.concat([top5, bot5]))
    return pd.concat(rows, ignore_index=True)

tb26 = top_bottom5(cand26, 2026)[['party','rank_type','candidate','constituency','votes','vote_pct']]
tb21 = top_bottom5(cand21, 2021)[['party','rank_type','candidate','constituency','votes','vote_pct']]
tb26.columns = ['Party','Rank Type','Candidate','Constituency','Votes','Vote Share %']
tb21.columns = ['Party','Rank Type','Candidate','Constituency','Votes','Vote Share %']

pprint("METRIC 2 — Top & Bottom 5 Candidate Vote Shares — 2026 (Top 3 Parties)", tb26)
pprint("METRIC 2 — Top & Bottom 5 Candidate Vote Shares — 2021 (Key Parties)", tb21)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 3 — Region-wise vote share of top 3 parties (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
def region_voteshare(df, parties, year):
    totals = df.groupby('region')['votes'].sum().rename('region_total')
    party_votes = df[df['party'].isin(parties)].groupby(['region','party'])['votes'].sum()
    result = (party_votes / totals * 100).round(2).reset_index()
    result.columns = ['Region','Party',f'{year} Vote Share %']
    return result.pivot(index='Region', columns='Party', values=f'{year} Vote Share %').reset_index()

rv26 = region_voteshare(df26, TOP3_26, 2026)
rv21 = region_voteshare(df21, ['DMK','AIADMK','NTK'], 2021)

pprint("METRIC 3 — Region-wise Vote Share of Top 3 Parties — 2026", rv26)
pprint("METRIC 3 — Region-wise Vote Share of Top 3 Parties — 2021", rv21)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 4 — State-wide vote share of parties (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
def state_voteshare(df, year, top_n=12):
    total = df['votes'].sum()
    vs = (df.groupby('party')['votes'].sum() / total * 100).round(2).reset_index()
    vs.columns = ['Party', f'{year} Vote Share %']
    vs = vs[~vs['Party'].isin(['NOTA'])].sort_values(f'{year} Vote Share %', ascending=False).head(top_n)
    return vs

sv26 = state_voteshare(df26, 2026)
sv21 = state_voteshare(df21, 2021)
sv_combined = sv26.merge(sv21, on='Party', how='outer').sort_values('2026 Vote Share %', ascending=False)
sv_combined = sv_combined.fillna('-')

pprint("METRIC 4 — State-wide Party Vote Share (2021 vs 2026)", sv_combined)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 6 — Region-wise Won Seats of Top 3 Parties (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
def region_seats(winners, parties, year):
    w = winners[winners['party'].isin(parties)]
    tbl = w.groupby(['region','party']).size().reset_index(name=f'{year} Seats')
    pivot = tbl.pivot(index='region', columns='party', values=f'{year} Seats').fillna(0).astype(int).reset_index()
    pivot.columns.name = None
    # add total seats per region
    total_per_region = winners.groupby('region').size().rename('Total Seats')
    pivot = pivot.merge(total_per_region, on='region')
    return pivot

rs26 = region_seats(winners26, TOP3_26, 2026)
rs21 = region_seats(winners21, ['DMK','AIADMK','INC'], 2021)
rs21_full = region_seats(winners21, winners21['party'].unique(), 2021)

pprint("METRIC 6 — Region-wise Seats Won by Top 3 Parties — 2026", rs26)
pprint("METRIC 6 — Region-wise Seats Won by Top 3 Parties — 2021", rs21)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 7 — Flipped Seats
# ══════════════════════════════════════════════════════════════════════════════
merged_winners = winners21[['ac_number','constituency','party','region']].rename(
    columns={'party':'party_21','constituency':'constituency_21'}).merge(
    winners26[['ac_number','party','constituency']].rename(
        columns={'party':'party_26','constituency':'constituency_26'}),
    on='ac_number', how='inner'
)
merged_winners['flipped'] = merged_winners['party_21'] != merged_winners['party_26']
flipped = merged_winners[merged_winners['flipped']].copy()

# Summary table: lost party, seats lost, captured by TVK, captured by others
def flip_summary(flipped):
    rows = []
    for lost_party in flipped['party_21'].unique():
        sub = flipped[flipped['party_21'] == lost_party]
        seats_lost = len(sub)
        by_tvk = len(sub[sub['party_26'] == 'TVK'])
        by_dmk = len(sub[sub['party_26'] == 'DMK'])
        by_aiadmk = len(sub[sub['party_26'] == 'AIADMK'])
        by_others = seats_lost - by_tvk - by_dmk - by_aiadmk
        rows.append({
            'Lost Party': lost_party,
            'Seats Lost': seats_lost,
            'Captured by TVK': by_tvk,
            'Captured by DMK': by_dmk,
            'Captured by AIADMK': by_aiadmk,
            'Captured by Others': by_others
        })
    df = pd.DataFrame(rows).sort_values('Seats Lost', ascending=False)
    return df[df['Seats Lost'] > 0]

flip_tbl = flip_summary(flipped)
pprint("METRIC 7 — Flipped Seats Summary", flip_tbl)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 8 — Net Seats Lost/Gained per Party (2021 vs 2026)
# ══════════════════════════════════════════════════════════════════════════════
seats21 = winners21.groupby('party').size().rename('Seats 2021')
seats26 = winners26.groupby('party').size().rename('Seats 2026')
net = pd.concat([seats21, seats26], axis=1).fillna(0).astype(int)
net['Net Change'] = net['Seats 2026'] - net['Seats 2021']
net = net[net[['Seats 2021','Seats 2026']].sum(axis=1) > 0].sort_values('Seats 2021', ascending=False)
net = net.reset_index().rename(columns={'party':'Party'})
pprint("METRIC 8 — Net Seats Won/Lost by Party (2021 → 2026)", net)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 9 — Average State Turnout (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
avg_to_21 = df21.groupby('ac_number')['turnout'].first().mean()
avg_to_26 = votes_cast_26['turnout_26'].mean()
to_state = pd.DataFrame({
    'Metric': ['Average State Turnout'],
    '2021 (%)': [round(avg_to_21, 2)],
    '2026 (%)': [round(avg_to_26, 2)],
    'Increase (pp)': [round(avg_to_26 - avg_to_21, 2)]
})
pprint("METRIC 9 — Average State Turnout (2021 vs 2026)", to_state)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 10 — Region-wise Average Turnout (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
# 2021 region turnout — one turnout value per constituency
region_to21 = (df21.groupby(['ac_number','region'])['turnout'].first()
               .reset_index().groupby('region')['turnout'].mean().round(2).rename('Avg Turnout 2021 (%)'))

# 2026 region turnout
df26_to = votes_cast_26[['ac_number','turnout_26']].merge(
    master[['ac_number','region']], on='ac_number', how='left')
region_to26 = df26_to.groupby('region')['turnout_26'].mean().round(2).rename('Avg Turnout 2026 (%)')

region_to = pd.concat([region_to21, region_to26], axis=1).reset_index()
region_to.columns = ['Region','Avg Turnout 2021 (%)','Avg Turnout 2026 (%)']
region_to['Increase (pp)'] = (region_to['Avg Turnout 2026 (%)'] - region_to['Avg Turnout 2021 (%)']).round(2)
region_to['Increase (%)'] = ((region_to['Increase (pp)'] / region_to['Avg Turnout 2021 (%)']) * 100).round(2)
pprint("METRIC 10 — Region-wise Average Turnout (2021 vs 2026)", region_to)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 11 — Top & Bottom 5 Turnout Constituencies (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
to21_c = df21.groupby(['ac_number','constituency','region'])['turnout'].first().reset_index()
to21_c.columns = ['ac_number','Constituency','Region','Turnout 2021 (%)']

to26_c = votes_cast_26[['ac_number','turnout_26']].merge(
    master[['ac_number','constituency','region']], on='ac_number', how='left')
to26_c.columns = ['ac_number','Turnout 2026 (%)','Constituency','Region']

top5_to21 = to21_c.nlargest(5,'Turnout 2021 (%)')[['Constituency','Region','Turnout 2021 (%)']].assign(Rank='Top 5')
bot5_to21 = to21_c.nsmallest(5,'Turnout 2021 (%)')[['Constituency','Region','Turnout 2021 (%)']].assign(Rank='Bottom 5')
top5_to26 = to26_c.nlargest(5,'Turnout 2026 (%)')[['Constituency','Region','Turnout 2026 (%)']].assign(Rank='Top 5')
bot5_to26 = to26_c.nsmallest(5,'Turnout 2026 (%)')[['Constituency','Region','Turnout 2026 (%)']].assign(Rank='Bottom 5')

pprint("METRIC 11 — Top 5 Turnout Constituencies 2021", top5_to21)
pprint("METRIC 11 — Bottom 5 Turnout Constituencies 2021", bot5_to21)
pprint("METRIC 11 — Top 5 Turnout Constituencies 2026", top5_to26)
pprint("METRIC 11 — Bottom 5 Turnout Constituencies 2026", bot5_to26)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 14 — Seats Won by Party in SC & ST Reserved Constituencies (2021 & 2026)
# ══════════════════════════════════════════════════════════════════════════════
def reserved_seats(winners, year):
    w = winners[winners['reserved'].isin(['SC','ST'])].copy()
    tbl = w.groupby(['party','reserved']).size().reset_index(name='seats')
    pivot = tbl.pivot(index='party', columns='reserved', values='seats').fillna(0).astype(int)
    if 'SC' not in pivot.columns: pivot['SC'] = 0
    if 'ST' not in pivot.columns: pivot['ST'] = 0
    pivot['Total Reserved'] = pivot['SC'] + pivot['ST']
    pivot = pivot.reset_index().rename(columns={'party':'Party'})
    pivot = pivot[pivot['Total Reserved'] > 0].sort_values('Total Reserved', ascending=False)
    pivot.columns.name = None
    return pivot

res26 = reserved_seats(winners26, 2026)
res21 = reserved_seats(winners21, 2021)
pprint("METRIC 14 — Party Seats in SC/ST Reserved Constituencies — 2026", res26)
pprint("METRIC 14 — Party Seats in SC/ST Reserved Constituencies — 2021", res21)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 15 — Reserved Seats Turnout Stats (SC & ST)
# ══════════════════════════════════════════════════════════════════════════════
res_to = master[['ac_number','reserved']].merge(
    votes_cast_26[['ac_number','turnout_26']], on='ac_number').merge(
    df21.groupby('ac_number')['turnout'].first().reset_index().rename(columns={'turnout':'turnout_21'}),
    on='ac_number', how='left')

def reserved_turnout_stats(res_to):
    rows = []
    for cat in ['SC','ST','GEN']:
        sub = res_to[res_to['reserved'] == cat]
        rows.append({
            'Category': cat,
            'Count': len(sub),
            'Avg Turnout 2021 (%)': round(sub['turnout_21'].mean(), 2),
            'Avg Turnout 2026 (%)': round(sub['turnout_26'].mean(), 2),
            'Min Turnout 2026 (%)': round(sub['turnout_26'].min(), 2),
            'Max Turnout 2026 (%)': round(sub['turnout_26'].max(), 2),
        })
    return pd.DataFrame(rows)

res_stats = reserved_turnout_stats(res_to)
pprint("METRIC 15 — Turnout Stats by Reservation Category (2021 & 2026)", res_stats)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 16 — 10 Minimum Margin Seats (2026)
# ══════════════════════════════════════════════════════════════════════════════
def build_margin_table(df, year, n=10, ascending=True):
    df = df.copy()
    totals = df.groupby('ac_number')['votes'].sum().rename('total_valid')
    df['rank'] = df.groupby('ac_number')['votes'].rank(method='first', ascending=False)
    winner = df[df['rank'] == 1][['ac_number','constituency','region','candidate','party','votes']].rename(
        columns={'candidate':'Winner','party':'Win Party','votes':'Winner Votes'})
    runner = df[df['rank'] == 2][['ac_number','candidate','party','votes']].rename(
        columns={'candidate':'Runner-Up','party':'Runner Party','votes':'Runner Votes'})
    tbl = winner.merge(runner, on='ac_number').merge(totals, on='ac_number')
    tbl['Margin'] = tbl['Winner Votes'] - tbl['Runner Votes']
    tbl = tbl.sort_values('Margin', ascending=ascending).head(n)
    tbl = tbl[['constituency','region','Winner','Win Party','Winner Votes','Runner-Up','Runner Party','Runner Votes','Margin']]
    tbl.columns = ['Constituency','Region','Winner','Win Party','Winner Votes','Runner-Up','Runner Party','Runner Votes','Margin']
    return tbl

min_margin_26 = build_margin_table(df26, 2026, n=10, ascending=True)
pprint("METRIC 16 — 10 Minimum Margin Seats 2026", min_margin_26)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 17 — 10 Maximum Margin Seats (2026)
# ══════════════════════════════════════════════════════════════════════════════
max_margin_26 = build_margin_table(df26, 2026, n=10, ascending=False)
pprint("METRIC 17 — 10 Maximum Margin Seats 2026", max_margin_26)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 18 — Candidates with >50% Vote Share in their Constituency
# ══════════════════════════════════════════════════════════════════════════════
def over50(df, year):
    totals = df.groupby('ac_number')['votes'].sum().rename('total_valid')
    d = df.merge(totals, on='ac_number')
    d['pct'] = d['votes'] / d['total_valid'] * 100
    over = d[d['pct'] > 50]
    return over[['constituency','candidate','party','votes','pct']].rename(
        columns={'constituency':'Constituency','candidate':'Candidate',
                 'party':'Party','votes':'Votes','pct':'Vote Share %'}).sort_values('Vote Share %', ascending=False)

o50_26 = over50(df26, 2026)
o50_21 = over50(df21, 2021)
print(f"\n{'═'*70}")
print(f"  METRIC 18 — Candidates with >50% Vote Share")
print(f"{'═'*70}")
print(f"  2021: {len(o50_21)} candidates crossed 50%")
print(f"  2026: {len(o50_26)} candidates crossed 50%")
pprint("METRIC 18 — All Candidates >50% Vote Share — 2021", o50_21.head(20))
pprint("METRIC 18 — All Candidates >50% Vote Share — 2026", o50_26)

# ══════════════════════════════════════════════════════════════════════════════
# METRIC 19 — Winners with <35% Vote Share in their Constituency
# ══════════════════════════════════════════════════════════════════════════════
def winners_under35(winners_df, df_raw, year):
    # total_valid already computed in get_winners; use win_pct directly
    w = winners_df.copy()
    under = w[w['win_pct'] < 35]
    return under[['constituency','candidate','party','votes','win_pct']].rename(
        columns={'constituency':'Constituency','candidate':'Candidate',
                 'party':'Party','votes':'Votes','win_pct':'Winner Vote Share %'}).sort_values('Winner Vote Share %')

u35_26 = winners_under35(winners26, df26, 2026)
u35_21 = winners_under35(winners21, df21, 2021)
print(f"\n{'═'*70}")
print(f"  METRIC 19 — Winners with <35% Vote Share (fragmented contests)")
print(f"{'═'*70}")
print(f"  2021: {len(u35_21)} winners had <35% vote share")
print(f"  2026: {len(u35_26)} winners had <35% vote share")
pprint("METRIC 19 — Winners <35% Vote Share — 2021 (sample 20)", u35_21.head(20))
pprint("METRIC 19 — Winners <35% Vote Share — 2026 (sample 20)", u35_26.head(20))

print("\n\n✅ All metrics computed successfully.\n")

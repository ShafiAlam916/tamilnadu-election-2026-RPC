import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & CUSTOM THEME (Bloomberg / War Room Aesthetics)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TN Assembly Election Analytics (2021 vs 2026)",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern political war-room aesthetics
st.markdown("""
<style>
    /* Main Background & Text Color */
    .stApp {
        background-color: #0E1117;
        color: #E2E8F0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Metrics Card Styling */
    div[data-testid="stMetric"] {
        background-color: #1A1C23;
        border: 1px solid #2D3748;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetric"] label {
        font-size: 14px !important;
        color: #A0AEC0 !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #F7FAFC !important;
        font-weight: 700 !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #11141D !important;
        border-right: 1px solid #2D3748 !important;
    }
    
    /* Interactive Button Grid Cell Styling */
    .stButton > button {
        background-color: #1A1C23 !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D3748 !important;
        border-radius: 4px !important;
        width: 100% !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button:hover {
        background-color: #3182CE !important;
        color: #FFFFFF !important;
        border-color: #4299E1 !important;
        box-shadow: 0 0 10px rgba(66, 153, 225, 0.5) !important;
    }
    
    /* Custom divider line */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, #E53E3E, #3182CE, #48BB78);
        margin: 20px 0;
    }
    
    /* Tabs styling */
    button[data-baseweb="tab"] {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #718096 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #3182CE !important;
        border-bottom-color: #3182CE !important;
    }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTS & PARTY COLORS
# ──────────────────────────────────────────────────────────────────────────────
PARTY_COLORS = {
    'TVK': '#D32F2F',      # Deep Crimson Red
    'DMK': '#1E88E5',      # Bright Blue
    'AIADMK': '#4CAF50',   # Emerald Green
    'INC': '#FF9800',      # Orange
    'BJP': '#FF5722',      # Saffron/Dark Orange
    'VCK': '#9C27B0',      # Purple
    'PMK': '#E91E63',      # Deep Pink
    'CPI(M)': '#E57373',   # Light Red
    'CPI': '#81C784',      # Light Green
    'NTK': '#FFEB3B',      # Yellow
    'IUML': '#009688',     # Teal
    'AMMK': '#8BC34A',     # Light Green
    'DMDK': '#3F51B5',     # Indigo
    'IND': '#718096',      # Slate Grey
    'Others': '#A0AEC0'    # Light Grey
}

TOP3_26 = ['TVK', 'DMK', 'AIADMK']
TOP3_21 = ['DMK', 'AIADMK', 'BJP']

def hex_to_rgba(hex_str, alpha=0.4):
    hex_str = hex_str.lstrip('#')
    rgb = tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})"

# ──────────────────────────────────────────────────────────────────────────────
# DATA PIPELINE (Cached Loaders)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_and_preprocess_data():
    # Load raw data
    df21_raw = pd.read_csv('tn_2021_results.csv')
    df26_raw = pd.read_csv('tn_2026_results.csv')
    electors = pd.read_csv('tn_2026_electors.csv')
    master = pd.read_csv('constituency_master.csv')
    
    df21 = df21_raw.copy()
    df26 = df26_raw.copy()
    
    # 2026 Turnout Computation
    electors_clean = electors[['ac_number','total']].dropna(subset=['ac_number'])
    electors_clean['ac_number'] = electors_clean['ac_number'].astype(int)
    
    votes_cast_26 = (df26.groupby('ac_number')['votes']
                          .sum()
                          .reset_index()
                          .rename(columns={'votes':'total_votes_cast'}))
    votes_cast_26 = votes_cast_26.merge(electors_clean, on='ac_number', how='left')
    votes_cast_26['turnout_26'] = (votes_cast_26['total_votes_cast'] / votes_cast_26['total'] * 100).round(2)
    
    # Merge turnout back into raw df26
    df26 = df26.merge(votes_cast_26[['ac_number','turnout_26']], on='ac_number', how='left')
    
    # 2021 Turnout Cleanup (already in df21 but keep consistency)
    df21['turnout'] = df21['turnout'].round(2)
    
    # Helper to derive winners
    def get_winners(df, turnout_col=None):
        d = df.copy()
        d['rank'] = d.groupby('ac_number')['votes'].rank(method='first', ascending=False)
        winners = d[d['rank'] == 1][['ac_number','constituency','region','reserved','candidate','party','votes']].copy()
        
        # Merge runners
        runners = d[d['rank'] == 2][['ac_number','candidate','party','votes']].rename(
            columns={'candidate':'runner_candidate','party':'runner_party','votes':'runner_votes'}
        )
        winners = winners.merge(runners, on='ac_number', how='left')
        winners['margin'] = winners['votes'] - winners['runner_votes']
        
        # Total valid votes
        totals = d.groupby('ac_number')['votes'].sum().reset_index().rename(columns={'votes':'total_valid'})
        winners = winners.merge(totals, on='ac_number', how='left')
        winners['win_pct'] = (winners['votes'] / winners['total_valid'] * 100).round(2)
        
        if turnout_col:
            t = d[['ac_number', turnout_col]].drop_duplicates()
            winners = winners.merge(t, on='ac_number', how='left')
            
        return winners

    winners26 = get_winners(df26, 'turnout_26')
    winners21 = get_winners(df21, 'turnout')
    
    # Merge district names into winners
    winners21 = winners21.merge(master[['ac_number', 'district']], on='ac_number', how='left')
    winners26 = winners26.merge(master[['ac_number', 'district']], on='ac_number', how='left')
    
    # Merge winners to find seat flips
    merged_winners = winners21[['ac_number','constituency','party','region','district','reserved']].rename(
        columns={'party':'party_21','constituency':'constituency_21'}).merge(
        winners26[['ac_number','party','constituency','candidate','votes','runner_candidate','runner_party','runner_votes','margin','win_pct','turnout_26']].rename(
            columns={'party':'party_26','constituency':'constituency_26'}),
        on='ac_number', how='inner'
    )
    merged_winners['flipped'] = merged_winners['party_21'] != merged_winners['party_26']
    
    return df21, df26, electors_clean, master, votes_cast_26, winners21, winners26, merged_winners

df21, df26, electors_clean, master, votes_cast_26, winners21, winners26, merged_winners = load_and_preprocess_data()

# ──────────────────────────────────────────────────────────────────────────────
# MODAL DRILLDOWN DIALOG FUNCTION
# ──────────────────────────────────────────────────────────────────────────────
@st.dialog("Constituency Drilldown", width="large")
def show_constituency_list_modal(title, df_filtered):
    st.markdown(f"#### {title}")
    st.markdown(f"**Found {len(df_filtered)} constituencies**")
    
    st.dataframe(
        df_filtered,
        column_config={
            "ac_number": st.column_config.NumberColumn("AC No.", format="%d"),
            "constituency": "Constituency",
            "region": "Region",
            "reserved": "Category",
            "winner": "Winner Candidate",
            "party_winner": "Winner Party",
            "votes_winner": st.column_config.NumberColumn("Winner Votes", format="%d"),
            "runner_up": "Runner Candidate",
            "party_runner": "Runner Party",
            "votes_runner": st.column_config.NumberColumn("Runner Votes", format="%d"),
            "margin": "Margin",
            "turnout": st.column_config.NumberColumn("Turnout %", format="%.2f%%")
        },
        width="stretch",
        hide_index=True
    )
    st.button("Close Modal")

# Centralized function to fetch drilldown constituency list
def get_constituency_list(year=2026, region=None, party=None, reserved=None, lost_party=None, filter_type=None):
    if year == 2026:
        w = winners26.copy()
        w = w.rename(columns={
            'candidate': 'winner',
            'party': 'party_winner',
            'votes': 'votes_winner',
            'runner_candidate': 'runner_up',
            'runner_party': 'party_runner',
            'runner_votes': 'votes_runner',
            'turnout_26': 'turnout'
        })
    else:
        w = winners21.copy()
        w = w.rename(columns={
            'candidate': 'winner',
            'party': 'party_winner',
            'votes': 'votes_winner',
            'runner_candidate': 'runner_up',
            'runner_party': 'party_runner',
            'runner_votes': 'votes_runner',
            'turnout': 'turnout'
        })
        
    # Apply filters
    if region and region != 'TOTAL' and region != 'All':
        w = w[w['region'] == region]
        
    if party and party != 'All':
        if party == 'Others':
            w = w[~w['party_winner'].isin(['TVK', 'DMK', 'AIADMK'])]
        else:
            w = w[w['party_winner'] == party]
            
    if reserved and reserved != 'TOTAL' and reserved != 'All':
        w = w[w['reserved'] == reserved]
        
    # Flip logic (Metric 7)
    if filter_type == 'flipped':
        flip_ids = merged_winners[merged_winners['flipped']]['ac_number']
        w = w[w['ac_number'].isin(flip_ids)]
        if lost_party:
            lost_ids = merged_winners[(merged_winners['party_21'] == lost_party) & (merged_winners['flipped'])]['ac_number']
            w = w[w['ac_number'].isin(lost_ids)]
            if party and party != 'Others':
                w = w[w['party_winner'] == party]
            elif party == 'Others':
                w = w[~w['party_winner'].isin(['TVK', 'DMK', 'AIADMK'])]
    elif filter_type == 'held':
        held_ids = merged_winners[~merged_winners['flipped']]['ac_number']
        w = w[w['ac_number'].isin(held_ids)]
        if lost_party:
            held_ids_party = merged_winners[(merged_winners['party_21'] == lost_party) & (~merged_winners['flipped'])]['ac_number']
            w = w[w['ac_number'].isin(held_ids_party)]
            
    if filter_type == 'over50':
        w = w[w['win_pct'] > 50]
    elif filter_type == 'under35':
        w = w[w['win_pct'] < 35]
        
    w = w[['ac_number', 'constituency', 'region', 'reserved', 'winner', 'party_winner', 'votes_winner', 'runner_up', 'party_runner', 'votes_runner', 'margin', 'turnout']]
    return w.sort_values('ac_number')

# ──────────────────────────────────────────────────────────────────────────────
# SIDEBAR CONTROLS
# ──────────────────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/000000/ballot-box.png", width=70)
st.sidebar.markdown("# TN Election 2026")
st.sidebar.markdown("### Comparative Analytics Portal")
st.sidebar.write("Analyze the tectonic shift in Tamil Nadu politics following the entry of TVK in the 2026 Assembly Elections.")

st.sidebar.markdown("---")
st.sidebar.markdown("### Visualisation Themes")
theme_select = st.sidebar.selectbox("Dashboard Accent Color", ["Bloomberg Blue", "FiveThirtyEight Crimson", "War-Room Teal"])
accent_color = '#3182CE' if theme_select == 'Bloomberg Blue' else ('#E53E3E' if theme_select == 'FiveThirtyEight Crimson' else '#319795')

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Statistics (2026)")
st.sidebar.metric("Total Seats", "234", help="Total Assembly Constituencies in Tamil Nadu")
st.sidebar.metric("Average Turnout", "86.07%", "+12.70pp")
st.sidebar.metric("Flipped Seats", "135", "57.7% of total")

# ──────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ──────────────────────────────────────────────────────────────────────────────
st.title("🗳️ Tamil Nadu Assembly Elections: 2021 vs 2026")
st.subheader("Interactive Comparative Analytics & War-Room Intelligence Platform")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# TABS SETUP
# ──────────────────────────────────────────────────────────────────────────────
tab_summary, tab_flips, tab_regions, tab_margins, tab_turnout, tab_explorer = st.tabs([
    "📊 Executive Summary",
    "🔄 Seat Flows & Flips",
    "🗺️ Regional Intelligence",
    "🎯 Margin & Intensity",
    "📈 Turnout Dynamics",
    "🔍 Constituency Explorer"
])

# ==============================================================================
# TAB 1: EXECUTIVE SUMMARY
# ==============================================================================
with tab_summary:
    st.markdown("### Key Headline Metrics")
    
    # Metric cards row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="TVK Seats Won (2026)", value="108", delta="New Party", delta_color="normal")
    with c2:
        st.metric(label="DMK Seats Won", value="59", delta="-74 seats", delta_color="inverse")
    with c3:
        st.metric(label="AIADMK Seats Won", value="47", delta="-19 seats", delta_color="inverse")
    with c4:
        st.metric(label="Seats Flipped (2026)", value="135", delta="57.69% of state", delta_color="normal")

    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.markdown("#### 📈 State-wide Party Vote Share (Slope Chart)")
        st.markdown(
            "This slope chart tracks the state-wide vote share shift. "
            "Note DMK and AIADMK sloping sharply down, with TVK appearing from 0% to 34.92%."
        )
        
        # Build Slope Chart
        slope_df = pd.DataFrame([
            {'Party': 'TVK', '2021': 0.0, '2026': 34.92},
            {'Party': 'DMK', '2021': 37.70, '2026': 24.19},
            {'Party': 'AIADMK', '2021': 33.29, '2026': 21.21},
            {'Party': 'NTK', '2021': 6.58, '2026': 4.00},
            {'Party': 'INC', '2021': 4.27, '2026': 3.37},
            {'Party': 'BJP', '2021': 2.62, '2026': 2.97},
            {'Party': 'PMK', '2021': 3.80, '2026': 2.17}
        ])
        
        fig_slope = go.Figure()
        for idx, row in slope_df.iterrows():
            party = row['Party']
            col = PARTY_COLORS.get(party, '#9E9E9E')
            fig_slope.add_trace(go.Scatter(
                x=['2021', '2026'],
                y=[row['2021'], row['2026']],
                mode='lines+markers+text',
                name=party,
                line=dict(color=col, width=4 if party in TOP3_26 else 2),
                marker=dict(color=col, size=10),
                text=[f"{row['2021']}%" if row['2021'] > 0 else '', f"{party}: {row['2026']}%"],
                textposition=['middle left', 'middle right'],
                textfont=dict(color='#E2E8F0', size=11)
            ))
            
        fig_slope.update_layout(
            xaxis=dict(showgrid=False, zeroline=False, showline=True, linecolor='#4A5568', tickfont=dict(color='#A0AEC0', size=12)),
            yaxis=dict(showgrid=False, zeroline=False, showline=False, showticklabels=False),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=80, r=100, t=30, b=30),
            height=400
        )
        st.plotly_chart(fig_slope, use_container_width=True)

    with col_right:
        st.markdown("#### 🗺️ Geographic Distribution (Dominant Party Winner in 2026)")
        st.markdown(
            "This map colors each of the 38 districts by the party that won the most seats in 2026. "
            "Hover to see seats and total popular votes won in that district."
        )
        
        # Load local GeoJSON
        try:
            with open('tamilnadu_districts.geojson', 'r') as f:
                geojson_data = json.load(f)
                
            # Rename/Fold 6 new districts in GeoJSON to match 32 parent districts
            district_map = {
                'Chengalpattu': 'Kanchipuram',
                'Kallakurichi': 'Villupuram',
                'Mayiladuthurai': 'Nagapattinam',
                'Ranipet': 'Vellore',
                'Tirupathur': 'Vellore',
                'Tenkasi': 'Tirunelveli',
                'The Nilgiris': 'Nilgiris',
                'Tuticorin': 'Thoothukudi',
                'Tiruppur': 'Tirupur',
                'Thiruvallur': 'Tiruvallur'
            }
            for feature in geojson_data['features']:
                dt = feature['properties'].get('dtname')
                if dt in district_map:
                    feature['properties']['dtname'] = district_map[dt]
            
            # Compute dominant party winner by district (with total vote tie-breaker)
            seat_counts = winners26.groupby(['district', 'party']).size().reset_index(name='seats')
            total_votes = df26.merge(master[['ac_number', 'district']], on='ac_number', how='left').groupby(['district', 'party'])['votes'].sum().reset_index(name='total_votes')
            district_stats = seat_counts.merge(total_votes, on=['district', 'party'], how='left')
            district_stats = district_stats.sort_values(['district', 'seats', 'total_votes'], ascending=[True, False, False])
            dominant_party = district_stats.drop_duplicates(subset=['district'], keep='first').copy()
            
            fig_map = px.choropleth(
                dominant_party,
                geojson=geojson_data,
                locations='district',
                featureidkey='properties.dtname',
                color='party',
                color_discrete_map=PARTY_COLORS,
                hover_data={'seats': True, 'total_votes': ':,', 'district': True},
                labels={'party': 'Dominant Party', 'seats': 'Seats Won', 'total_votes': 'Total Votes'},
                projection='mercator'
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_map, use_container_width=True)
            
        except Exception as e:
            st.error(f"Could not load GeoJSON map: {e}")
            
    st.markdown("---")
    
    st.markdown("#### 🗳️ State-wide Seat Shift (2021 vs 2026)")
    st.markdown("Click on any **Seat Count** number below to drill down and see the list of constituencies.")
    
    # Net seats won table
    seats21 = winners21.groupby('party').size().rename('Seats 2021')
    seats26 = winners26.groupby('party').size().rename('Seats 2026')
    net_df = pd.concat([seats21, seats26], axis=1).fillna(0).astype(int)
    net_df['Net Change'] = net_df['Seats 2026'] - net_df['Seats 2021']
    net_df = net_df[net_df[['Seats 2021','Seats 2026']].sum(axis=1) > 0].sort_values('Seats 2021', ascending=False).reset_index()
    net_df = net_df.rename(columns={'party':'Party'})
    
    # Render with Clickable Buttons
    # Header columns
    col_hdr = st.columns([2, 1, 1, 1])
    col_hdr[0].markdown("**Party**")
    col_hdr[1].markdown("**Seats 2021**")
    col_hdr[2].markdown("**Seats 2026**")
    col_hdr[3].markdown("**Net Change**")
    
    for idx, row in net_df.iterrows():
        cols = st.columns([2, 1, 1, 1])
        cols[0].write(f"**{row['Party']}**")
        
        # 2021 Seats Button
        s21 = row['Seats 2021']
        if s21 > 0:
            if cols[1].button(f"{s21}", key=f"net_21_{row['Party']}"):
                show_constituency_list_modal(
                    f"Constituencies Won by {row['Party']} in 2021 ({s21} Seats)",
                    get_constituency_list(year=2021, party=row['Party'])
                )
        else:
            cols[1].write("0")
            
        # 2026 Seats Button
        s26 = row['Seats 2026']
        if s26 > 0:
            if cols[2].button(f"{s26}", key=f"net_26_{row['Party']}"):
                show_constituency_list_modal(
                    f"Constituencies Won by {row['Party']} in 2026 ({s26} Seats)",
                    get_constituency_list(year=2026, party=row['Party'])
                )
        else:
            cols[2].write("0")
            
        # Net change style
        nc = row['Net Change']
        nc_str = f"+{nc}" if nc > 0 else f"{nc}"
        color_nc = "#48BB78" if nc > 0 else ("#E53E3E" if nc < 0 else "#E2E8F0")
        cols[3].markdown(f"<span style='color:{color_nc}; font-weight:600;'>{nc_str}</span>", unsafe_allow_html=True)

# ==============================================================================
# TAB 2: SEAT FLOWS & FLIPS
# ==============================================================================
with tab_flips:
    st.markdown("### Seat Flows and Flip Dynamics")
    st.markdown(
        "Here we explore the tectonic seat flows from 2021 to 2026. "
        "TVK acted as a massive absorber, drawing heavily from both DMK and AIADMK."
    )
    
    # 1. Sankey Diagram
    st.markdown("#### 1. Sankey Flow Diagram: 2021 Winners ➔ 2026 Winners")
    st.markdown("Hover over the ribbons to see the exact number of seats transferred from 2021 to 2026.")
    
    # Group seat changes
    flow_df = merged_winners.groupby(['party_21', 'party_26']).size().reset_index(name='count')
    parties_21 = sorted(flow_df['party_21'].unique())
    parties_26 = sorted(flow_df['party_26'].unique())
    
    node_labels = [f"{p} (2021)" for p in parties_21] + [f"{p} (2026)" for p in parties_26]
    node_colors = [PARTY_COLORS.get(p, '#9E9E9E') for p in parties_21] + [PARTY_COLORS.get(p, '#9E9E9E') for p in parties_26]
    
    node_map_21 = {p: i for i, p in enumerate(parties_21)}
    node_map_26 = {p: len(parties_21) + i for i, p in enumerate(parties_26)}
    
    sources = [node_map_21[row['party_21']] for _, row in flow_df.iterrows()]
    targets = [node_map_26[row['party_26']] for _, row in flow_df.iterrows()]
    values = flow_df['count'].tolist()
    
    # Use semi-translucent party colors for links
    link_colors = [hex_to_rgba(PARTY_COLORS.get(row['party_26'], '#9E9E9E'), 0.4) for _, row in flow_df.iterrows()]
    
    fig_sankey = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
            hovertemplate="%{source.label} ➔ %{target.label}: <b>%{value}</b> seats<extra></extra>"
        )
    )])
    
    fig_sankey.update_layout(
        font_size=12,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#E2E8F0",
        margin=dict(l=10, r=10, t=20, b=20),
        height=500
    )
    st.plotly_chart(fig_sankey, use_container_width=True)
    
    st.markdown("---")
    
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        st.markdown("#### 2. Seats Held vs Lost (by 2021 Winner)")
        st.markdown("Shows how many seats each party managed to retain (Held) vs how many flipped (Lost).")
        
        held_counts = merged_winners[~merged_winners['flipped']].groupby('party_21').size().rename('Held')
        lost_counts = merged_winners[merged_winners['flipped']].groupby('party_21').size().rename('Lost')
        fh_df = pd.concat([held_counts, lost_counts], axis=1).fillna(0).astype(int).reset_index()
        fh_df = fh_df.rename(columns={'party_21': 'Party'})
        fh_df['Total 2021'] = fh_df['Held'] + fh_df['Lost']
        fh_df = fh_df.sort_values('Total 2021', ascending=False)
        
        fig_held_lost = go.Figure()
        fig_held_lost.add_trace(go.Bar(
            x=fh_df['Party'], y=fh_df['Held'],
            name='Held',
            marker_color='#3182CE'
        ))
        fig_held_lost.add_trace(go.Bar(
            x=fh_df['Party'], y=fh_df['Lost'],
            name='Lost',
            marker_color='#E53E3E'
        ))
        
        fig_held_lost.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(showgrid=False, tickfont=dict(color='#A0AEC0')),
            yaxis=dict(showgrid=True, gridcolor='#2D3748', tickfont=dict(color='#A0AEC0')),
            height=350,
            margin=dict(l=30, r=10, t=10, b=30)
        )
        st.plotly_chart(fig_held_lost, use_container_width=True)
        
    with col_f2:
        st.markdown("#### 3. Flip Matrix (Heatmap)")
        st.markdown("Rows = 2021 Winner, Columns = 2026 Winner. Cells denote count of transferred seats.")
        
        # Heatmap Flip matrix
        flipped_seats = merged_winners[merged_winners['flipped']]
        matrix = flipped_seats.groupby(['party_21', 'party_26']).size().reset_index(name='seats')
        pivot_matrix = matrix.pivot(index='party_21', columns='party_26', values='seats').fillna(0).astype(int)
        
        fig_heat = px.imshow(
            pivot_matrix,
            text_auto=True,
            labels=dict(x="2026 Winner (Captured By)", y="2021 Winner (Lost Party)", color="Seats Flipped"),
            color_continuous_scale="Reds",
            aspect="auto"
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            margin=dict(l=20, r=10, t=10, b=20),
            height=350
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
    st.markdown("---")
    
    st.markdown("#### 🔄 Interactive Flip Summary Table")
    st.markdown("Click on any count below to see the exact constituencies corresponding to that flip.")
    
    # Flip Summary Table structure
    # Row: Lost Party | Seats Lost | Captured by TVK | Captured by DMK | Captured by AIADMK | Captured by Others
    flip_tbl = []
    for lost_p in sorted(merged_winners['party_21'].unique()):
        sub_lost = merged_winners[merged_winners['party_21'] == lost_p]
        tot_lost = sub_lost['flipped'].sum()
        if tot_lost == 0:
            continue
            
        by_tvk = sub_lost[sub_lost['flipped'] & (sub_lost['party_26'] == 'TVK')].shape[0]
        by_dmk = sub_lost[sub_lost['flipped'] & (sub_lost['party_26'] == 'DMK')].shape[0]
        by_aiadmk = sub_lost[sub_lost['flipped'] & (sub_lost['party_26'] == 'AIADMK')].shape[0]
        by_others = tot_lost - by_tvk - by_dmk - by_aiadmk
        
        flip_tbl.append({
            'Lost Party': lost_p,
            'Seats Lost': tot_lost,
            'Captured by TVK': by_tvk,
            'Captured by DMK': by_dmk,
            'Captured by AIADMK': by_aiadmk,
            'Captured by Others': by_others
        })
    flip_tbl_df = pd.DataFrame(flip_tbl).sort_values('Seats Lost', ascending=False)
    
    # Headers
    col_hdr = st.columns([2, 1, 1, 1, 1, 1])
    col_hdr[0].markdown("**Lost Party (2021)**")
    col_hdr[1].markdown("**Total Seats Lost**")
    col_hdr[2].markdown("**Captured by TVK**")
    col_hdr[3].markdown("**Captured by DMK**")
    col_hdr[4].markdown("**Captured by AIADMK**")
    col_hdr[5].markdown("**Captured by Others**")
    
    for idx, row in flip_tbl_df.iterrows():
        cols = st.columns([2, 1, 1, 1, 1, 1])
        cols[0].write(f"**{row['Lost Party']}**")
        
        # Total Lost Button
        if cols[1].button(f"{row['Seats Lost']}", key=f"f_lost_{row['Lost Party']}"):
            show_constituency_list_modal(
                f"Seats Lost by {row['Lost Party']} in 2026 ({row['Seats Lost']} Seats)",
                get_constituency_list(year=2026, lost_party=row['Lost Party'], filter_type='flipped')
            )
            
        # Captured by TVK
        if row['Captured by TVK'] > 0:
            if cols[2].button(f"{row['Captured by TVK']}", key=f"f_tvk_{row['Lost Party']}"):
                show_constituency_list_modal(
                    f"Seats Flipped: {row['Lost Party']} ➔ TVK ({row['Captured by TVK']} Seats)",
                    get_constituency_list(year=2026, lost_party=row['Lost Party'], party='TVK', filter_type='flipped')
                )
        else:
            cols[2].write("0")
            
        # Captured by DMK
        if row['Captured by DMK'] > 0:
            if cols[3].button(f"{row['Captured by DMK']}", key=f"f_dmk_{row['Lost Party']}"):
                show_constituency_list_modal(
                    f"Seats Flipped: {row['Lost Party']} ➔ DMK ({row['Captured by DMK']} Seats)",
                    get_constituency_list(year=2026, lost_party=row['Lost Party'], party='DMK', filter_type='flipped')
                )
        else:
            cols[3].write("0")
            
        # Captured by AIADMK
        if row['Captured by AIADMK'] > 0:
            if cols[4].button(f"{row['Captured by AIADMK']}", key=f"f_aiadmk_{row['Lost Party']}"):
                show_constituency_list_modal(
                    f"Seats Flipped: {row['Lost Party']} ➔ AIADMK ({row['Captured by AIADMK']} Seats)",
                    get_constituency_list(year=2026, lost_party=row['Lost Party'], party='AIADMK', filter_type='flipped')
                )
        else:
            cols[4].write("0")
            
        # Captured by Others
        if row['Captured by Others'] > 0:
            if cols[5].button(f"{row['Captured by Others']}", key=f"f_oth_{row['Lost Party']}"):
                show_constituency_list_modal(
                    f"Seats Flipped: {row['Lost Party']} ➔ Others ({row['Captured by Others']} Seats)",
                    get_constituency_list(year=2026, lost_party=row['Lost Party'], party='Others', filter_type='flipped')
                )
        else:
            cols[5].write("0")
            
    # Add Total Flipped Summary Row
    cols = st.columns([2, 1, 1, 1, 1, 1])
    cols[0].markdown("**TOTAL FLIPS**")
    
    tot_flips = flip_tbl_df['Seats Lost'].sum()
    if cols[1].button(f"{tot_flips}", key="f_tot_flips"):
        show_constituency_list_modal("All Flipped Constituencies (135)", get_constituency_list(year=2026, filter_type='flipped'))
        
    tot_tvk = flip_tbl_df['Captured by TVK'].sum()
    if cols[2].button(f"{tot_tvk}", key="f_tot_tvk"):
        show_constituency_list_modal("All Flips Captured by TVK (108)", get_constituency_list(year=2026, party='TVK', filter_type='flipped'))
        
    tot_dmk = flip_tbl_df['Captured by DMK'].sum()
    if cols[3].button(f"{tot_dmk}", key="f_tot_dmk"):
        show_constituency_list_modal("All Flips Captured by DMK (19)", get_constituency_list(year=2026, party='DMK', filter_type='flipped'))
        
    tot_aiadmk = flip_tbl_df['Captured by AIADMK'].sum()
    if cols[4].button(f"{tot_aiadmk}", key="f_tot_aiadmk"):
        show_constituency_list_modal("All Flips Captured by AIADMK (25)", get_constituency_list(year=2026, party='AIADMK', filter_type='flipped'))
        
    tot_oth = flip_tbl_df['Captured by Others'].sum()
    if cols[5].button(f"{tot_oth}", key="f_tot_oth"):
        show_constituency_list_modal("All Flips Captured by Others (11)", get_constituency_list(year=2026, party='Others', filter_type='flipped'))

# ==============================================================================
# TAB 3: REGIONAL INTELLIGENCE
# ==============================================================================
with tab_regions:
    st.markdown("### Regional Intelligence Breakdown")
    st.markdown(
        "Tamil Nadu's 234 seats are divided into 6 geographical regions. "
        "The TVK wave hit hardest in Chennai Metro (90% flip rate) and was relatively stable in the Delta."
    )
    
    # Horizontal Bar: Region-wise flip rate
    st.markdown("#### 4. Region-wise Flip Rate (%)")
    total_region = merged_winners.groupby('region').size()
    flipped_region = merged_winners[merged_winners['flipped']].groupby('region').size()
    flip_rate_df = ((flipped_region / total_region) * 100).round(2).reset_index(name='Flip Rate')
    flip_rate_df = flip_rate_df.sort_values('Flip Rate', ascending=True)
    
    fig_flip_rate = px.bar(
        flip_rate_df,
        x='Flip Rate',
        y='region',
        orientation='h',
        text=[f"{v}%" for v in flip_rate_df['Flip Rate']],
        color_discrete_sequence=[accent_color]
    )
    fig_flip_rate.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E2E8F0",
        xaxis=dict(title="Flip Rate (%)", showgrid=True, gridcolor='#2D3748'),
        yaxis=dict(title="Region", showgrid=False),
        height=300,
        margin=dict(l=10, r=20, t=10, b=10)
    )
    st.plotly_chart(fig_flip_rate, use_container_width=True)
    
    st.markdown("---")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.markdown("#### 6. Region-wise Vote Share (2026)")
        st.markdown("Note TVK's uniform 31-47% across every single region — the key finding of this election.")
        
        # Region-wise Vote Share calculation
        totals_reg = df26.groupby('region')['votes'].sum().rename('region_total')
        party_votes_reg = df26[df26['party'].isin(TOP3_26)].groupby(['region','party'])['votes'].sum().reset_index()
        party_votes_reg = party_votes_reg.merge(totals_reg, on='region')
        party_votes_reg['Vote Share %'] = (party_votes_reg['votes'] / party_votes_reg['region_total'] * 100).round(2)
        
        fig_reg_vs = px.bar(
            party_votes_reg,
            x='region',
            y='Vote Share %',
            color='party',
            barmode='group',
            color_discrete_map=PARTY_COLORS
        )
        fig_reg_vs.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(showgrid=False, tickfont=dict(color='#A0AEC0')),
            yaxis=dict(showgrid=True, gridcolor='#2D3748', tickfont=dict(color='#A0AEC0')),
            height=350,
            margin=dict(l=30, r=10, t=10, b=30)
        )
        st.plotly_chart(fig_reg_vs, use_container_width=True)
        
    with col_r2:
        st.markdown("#### 7. Net Change (Vote Share % vs Seats)")
        st.markdown("Toggle below to see the before/after diverging changes of the top 3 parties.")
        metric_choice = st.radio("Choose Change Metric:", ["Vote Share Change (pp)", "Seat Change"], horizontal=True)
        
        if metric_choice == "Vote Share Change (pp)":
            change_df = pd.DataFrame([
                {'Party': 'TVK', 'Change': 34.92},
                {'Party': 'DMK', 'Change': -13.51},
                {'Party': 'AIADMK', 'Change': -12.08}
            ])
            ytitle = "Vote Share Change (pp)"
        else:
            change_df = pd.DataFrame([
                {'Party': 'TVK', 'Change': 108},
                {'Party': 'DMK', 'Change': -74},
                {'Party': 'AIADMK', 'Change': -19}
            ])
            ytitle = "Seat Count Change"
            
        fig_change = px.bar(
            change_df,
            x='Party',
            y='Change',
            color='Party',
            color_discrete_map=PARTY_COLORS,
            text=[f"+{v}" if v > 0 else f"{v}" for v in change_df['Change']]
        )
        # Add baseline line
        fig_change.add_hline(y=0, line_color="white", line_width=1)
        fig_change.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#2D3748', title=ytitle),
            height=300,
            margin=dict(l=30, r=10, t=10, b=30),
            showlegend=False
        )
        st.plotly_chart(fig_change, use_container_width=True)
        
    st.markdown("---")
    
    st.markdown("#### 11. Faceted Region-wise Won Seats (2026 vs 2021 Faded)")
    st.markdown(
        "Faceted by region, comparing 2026 seat counts (Solid) to 2021 seat counts (Faded) "
        "for the top 3 parties. Immediately highlights the collapse of DMK in Chennai Metro."
    )
    
    # Calculate Seats by Region for subplots
    regions = sorted(merged_winners['region'].unique())
    
    # Get 2021 and 2026 seat counts per region
    rs26 = winners26.groupby(['region','party']).size().reset_index(name='26_seats')
    rs26_pivot = rs26.pivot(index='region', columns='party', values='26_seats').fillna(0).astype(int)
    
    rs21 = winners21.groupby(['region','party']).size().reset_index(name='21_seats')
    rs21_pivot = rs21.pivot(index='region', columns='party', values='21_seats').fillna(0).astype(int)
    
    fig_facets = make_subplots(
        rows=2, cols=3,
        subplot_titles=regions,
        shared_yaxes=True,
        vertical_spacing=0.2,
        horizontal_spacing=0.08
    )
    
    for idx, r in enumerate(regions):
        row_idx = (idx // 3) + 1
        col_idx = (idx % 3) + 1
        
        parties = ['DMK', 'AIADMK', 'TVK']
        
        # 2021 values (faded)
        val_21 = [rs21_pivot.loc[r, p] if r in rs21_pivot.index and p in rs21_pivot.columns else 0 for p in parties]
        # 2026 values (solid)
        val_26 = [rs26_pivot.loc[r, p] if r in rs26_pivot.index and p in rs26_pivot.columns else 0 for p in parties]
        
        # Faded 2021
        fig_facets.add_trace(
            go.Bar(
                x=parties, y=val_21,
                name='2021 Seats (Faded)',
                marker_color=[hex_to_rgba(PARTY_COLORS[p], 0.25) for p in parties],
                showlegend=(idx == 0),
                hovertemplate=f"2021 {r} %{{x}}: %{{y}} seats<extra></extra>"
            ),
            row=row_idx, col=col_idx
        )
        
        # Solid 2026
        fig_facets.add_trace(
            go.Bar(
                x=parties, y=val_26,
                name='2026 Seats (Solid)',
                marker_color=[PARTY_COLORS[p] for p in parties],
                showlegend=(idx == 0),
                hovertemplate=f"2026 {r} %{{x}}: %{{y}} seats<extra></extra>"
            ),
            row=row_idx, col=col_idx
        )
        
    fig_facets.update_layout(
        barmode='group',
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#E2E8F0",
        height=500,
        margin=dict(l=10, r=10, t=40, b=20)
    )
    st.plotly_chart(fig_facets, use_container_width=True)
    
    st.markdown("---")
    
    st.markdown("#### 🗺️ Region-wise Seat Allocation Table")
    st.markdown("Click on any cell number to see the list of constituencies won by that party in the selected region.")
    
    # Build Region seat table
    rs26_tbl = winners26.groupby(['region','party']).size().reset_index(name='seats')
    rs26_tbl_pivot = rs26_tbl.pivot(index='region', columns='party', values='seats').fillna(0).astype(int).reset_index()
    
    # Ensure major columns exist
    for p in TOP3_26:
        if p not in rs26_tbl_pivot.columns:
            rs26_tbl_pivot[p] = 0
            
    # Add Total Seats column
    rs26_tbl_pivot['Total Seats'] = rs26_tbl_pivot[TOP3_26].sum(axis=1) # Note: this sums only top 3, let's get actual totals
    actual_totals = winners26.groupby('region').size().rename('Total Seats')
    rs26_tbl_pivot = rs26_tbl_pivot.drop(columns=['Total Seats'], errors='ignore').merge(actual_totals, on='region')
    
    # Headers
    col_hdr = st.columns([2, 1, 1, 1, 1])
    col_hdr[0].markdown("**Region**")
    col_hdr[1].markdown("**AIADMK**")
    col_hdr[2].markdown("**DMK**")
    col_hdr[3].markdown("**TVK**")
    col_hdr[4].markdown("**Total Seats**")
    
    for idx, row in rs26_tbl_pivot.iterrows():
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].write(f"**{row['region']}**")
        
        # AIADMK Button
        a_seats = row.get('AIADMK', 0)
        if a_seats > 0:
            if cols[1].button(f"{a_seats}", key=f"tbl_r_aiadmk_{row['region']}"):
                show_constituency_list_modal(
                    f"{row['region']} Region — AIADMK Seats ({a_seats})",
                    get_constituency_list(year=2026, region=row['region'], party='AIADMK')
                )
        else:
            cols[1].write("0")
            
        # DMK Button
        d_seats = row.get('DMK', 0)
        if d_seats > 0:
            if cols[2].button(f"{d_seats}", key=f"tbl_r_dmk_{row['region']}"):
                show_constituency_list_modal(
                    f"{row['region']} Region — DMK Seats ({d_seats})",
                    get_constituency_list(year=2026, region=row['region'], party='DMK')
                )
        else:
            cols[2].write("0")
            
        # TVK Button
        t_seats = row.get('TVK', 0)
        if t_seats > 0:
            if cols[3].button(f"{t_seats}", key=f"tbl_r_tvk_{row['region']}"):
                show_constituency_list_modal(
                    f"{row['region']} Region — TVK Seats ({t_seats})",
                    get_constituency_list(year=2026, region=row['region'], party='TVK')
                )
        else:
            cols[3].write("0")
            
        # Total
        cols[4].write(f"{row['Total Seats']}")
        
    # Bottom Total Row
    cols = st.columns([2, 1, 1, 1, 1])
    cols[0].markdown("**TOTAL STATE**")
    
    aiadmk_tot = rs26_tbl_pivot.get('AIADMK', pd.Series([0])).sum()
    if cols[1].button(f"{aiadmk_tot}", key="tbl_r_tot_aiadmk"):
        show_constituency_list_modal(f"State-wide — AIADMK Seats ({aiadmk_tot})", get_constituency_list(year=2026, party='AIADMK'))
        
    dmk_tot = rs26_tbl_pivot.get('DMK', pd.Series([0])).sum()
    if cols[2].button(f"{dmk_tot}", key="tbl_r_tot_dmk"):
        show_constituency_list_modal(f"State-wide — DMK Seats ({dmk_tot})", get_constituency_list(year=2026, party='DMK'))
        
    tvk_tot = rs26_tbl_pivot.get('TVK', pd.Series([0])).sum()
    if cols[3].button(f"{tvk_tot}", key="tbl_r_tot_tvk"):
        show_constituency_list_modal(f"State-wide — TVK Seats ({tvk_tot})", get_constituency_list(year=2026, party='TVK'))
        
    cols[4].markdown(f"**{rs26_tbl_pivot['Total Seats'].sum()}**")

# ==============================================================================
# TAB 4: MARGIN & INTENSITY
# ==============================================================================
with tab_margins:
    st.markdown("### Contest Intensity, Win Margins & Distribution")
    st.markdown(
        "The 2026 election saw a dramatic surge in fragmented contests. "
        "With a tripolar fight, the average margins plummeted, and winners with under 35% vote share surged."
    )
    
    col_m1, col_m2 = st.columns(2)
    
    with col_m1:
        st.markdown("#### 8. Winner Vote Share Distribution (2021 vs 2026)")
        st.markdown("Note the 2026 distribution shifts sharply left and completely loses its right tail (over 60% wins).")
        
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Histogram(
            x=winners21['win_pct'],
            name='2021 Winner Share',
            marker_color='#1E88E5',
            opacity=0.6,
            nbinsx=20
        ))
        fig_dist.add_trace(go.Histogram(
            x=winners26['win_pct'],
            name='2026 Winner Share',
            marker_color='#D32F2F',
            opacity=0.6,
            nbinsx=20
        ))
        
        # Add 50% line
        fig_dist.add_vline(x=50, line_dash="dash", line_color="white", annotation_text="50% Majoritarian Threshold")
        
        fig_dist.update_layout(
            barmode='overlay',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(title="Winner Vote Share (%)", showgrid=False),
            yaxis=dict(title="Number of Constituencies", showgrid=True, gridcolor='#2D3748'),
            height=350,
            margin=dict(l=30, r=10, t=10, b=30)
        )
        st.plotly_chart(fig_dist, use_container_width=True)
        
    with col_m2:
        st.markdown("#### 9. Margin Story KPI Comparison (Avg Margin, >50%, <35%)")
        st.markdown(
            "Visualizing the complete shift: average margins fell, candidates crossing 50% "
            "fell from 70 to 13, and winners with under 35% surged from 2 to 64."
        )
        
        # Create subplot comparison
        fig_kpis = make_subplots(
            rows=1, cols=3,
            subplot_titles=["Avg Margin (Votes)", "Winners >50% (Count)", "Winners <35% (Count)"],
            shared_yaxes=False
        )
        
        # Avg Margin
        avg_m_21 = winners21['margin'].mean()
        avg_m_26 = winners26['margin'].mean()
        fig_kpis.add_trace(go.Bar(
            x=['2021', '2026'], y=[avg_m_21, avg_m_26],
            marker_color=['#1E88E5', '#D32F2F'],
            showlegend=False
        ), row=1, col=1)
        
        # >50% count
        c50_21 = winners21[winners21['win_pct'] > 50].shape[0]
        c50_26 = winners26[winners26['win_pct'] > 50].shape[0]
        fig_kpis.add_trace(go.Bar(
            x=['2021', '2026'], y=[c50_21, c50_26],
            marker_color=['#1E88E5', '#D32F2F'],
            showlegend=False
        ), row=1, col=2)
        
        # <35% count
        c35_21 = winners21[winners21['win_pct'] < 35].shape[0]
        c35_26 = winners26[winners26['win_pct'] < 35].shape[0]
        fig_kpis.add_trace(go.Bar(
            x=['2021', '2026'], y=[c35_21, c35_26],
            marker_color=['#1E88E5', '#D32F2F'],
            showlegend=False
        ), row=1, col=3)
        
        fig_kpis.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            height=350,
            margin=dict(l=20, r=10, t=40, b=20)
        )
        st.plotly_chart(fig_kpis, use_container_width=True)
        
    st.markdown("---")
    
    col_lg_l, col_lg_r = st.columns(2)
    
    with col_lg_l:
        st.markdown("#### 10. Lollipop Chart: Top 10 Narrowest Margins (2026)")
        st.markdown("The drama chart. Tiruppattur at 1 vote is the cliffhanger. Color dots by winning party.")
        
        # Top 10 narrowest margins
        min_margin_26 = winners26.sort_values('margin', ascending=True).head(10).copy()
        
        fig_loll = go.Figure()
        
        # Draw stems
        for idx, row in min_margin_26.iterrows():
            fig_loll.add_trace(go.Scatter(
                x=[0, row['margin']],
                y=[row['constituency'], row['constituency']],
                mode='lines',
                line=dict(color='#4A5568', width=2),
                showlegend=False,
                hoverinfo='skip'
            ))
            
        # Draw dots
        fig_loll.add_trace(go.Scatter(
            x=min_margin_26['margin'],
            y=min_margin_26['constituency'],
            mode='markers',
            marker=dict(
                color=[PARTY_COLORS.get(p, '#9E9E9E') for p in min_margin_26['party']],
                size=12,
                line=dict(color='#FFFFFF', width=1.5)
            ),
            text=[f"Winner: {w} ({p})<br>Runner: {rc} ({rp})<br>Margin: {m} votes"
                  for w, p, rc, rp, m in zip(min_margin_26['candidate'], min_margin_26['party'],
                                           min_margin_26['runner_candidate'], min_margin_26['runner_party'],
                                           min_margin_26['margin'])],
            hovertemplate="%{text}<extra></extra>",
            showlegend=False
        ))
        
        fig_loll.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(title="Winning Margin (Votes)", showgrid=True, gridcolor='#2D3748'),
            yaxis=dict(title="", showgrid=False, categoryorder='total descending'),
            height=400,
            margin=dict(l=10, r=20, t=10, b=30)
        )
        st.plotly_chart(fig_loll, use_container_width=True)
        
    with col_lg_r:
        st.markdown("#### 🏆 Top 10 Largest Margins (2026)")
        st.markdown("Shows constituencies with the most dominant victories in the state.")
        
        max_margin_26 = winners26.sort_values('margin', ascending=False).head(10)[['constituency', 'region', 'candidate', 'party', 'runner_candidate', 'runner_party', 'margin']]
        max_margin_26 = max_margin_26.rename(columns={
            'constituency': 'Constituency',
            'candidate': 'Winner',
            'party': 'Party',
            'runner_candidate': 'Runner-Up',
            'runner_party': 'Runner Party',
            'margin': 'Margin'
        })
        
        st.dataframe(
            max_margin_26,
            column_config={
                "Margin": st.column_config.NumberColumn("Margin (Votes)", format="%d")
            },
            width="stretch",
            hide_index=True
        )
        
    st.markdown("---")
    
    st.markdown("#### 🎯 Interactive Intensity Categories")
    st.markdown("Click on the numbers in the KPI summary below to view the list of constituencies.")
    
    # Grid of intensity clickers
    col_int1, col_int2 = st.columns(2)
    with col_int1:
        st.markdown("##### 👑 Dominant Victories (>50% Vote Share)")
        st.write("Candidates who won with a clear absolute majority of votes cast in their constituency.")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            val_o50_21 = winners21[winners21['win_pct'] > 50].shape[0]
            st.write("**2021 Contestants:**")
            if st.button(f"{val_o50_21} Candidates", key="btn_o50_21"):
                show_constituency_list_modal("2021 Winners with >50% Vote Share", get_constituency_list(year=2021, filter_type='over50'))
        with col_c2:
            val_o50_26 = winners26[winners26['win_pct'] > 50].shape[0]
            st.write("**2026 Contestants:**")
            if st.button(f"{val_o50_26} Candidates", key="btn_o50_26"):
                show_constituency_list_modal("2026 Winners with >50% Vote Share", get_constituency_list(year=2026, filter_type='over50'))
                
    with col_int2:
        st.markdown("##### ⚡ Hyper-Fragmented Victories (<35% Vote Share)")
        st.write("Winners who emerged victorious with less than 35% vote share due to intense vote-splitting.")
        
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            val_u35_21 = winners21[winners21['win_pct'] < 35].shape[0]
            st.write("**2021 Contestants:**")
            if st.button(f"{val_u35_21} Winners", key="btn_u35_21"):
                show_constituency_list_modal("2021 Winners with <35% Vote Share", get_constituency_list(year=2021, filter_type='under35'))
        with col_u2:
            val_u35_26 = winners26[winners26['win_pct'] < 35].shape[0]
            st.write("**2026 Contestants:**")
            if st.button(f"{val_u35_26} Winners", key="btn_u35_26"):
                show_constituency_list_modal("2026 Winners with <35% Vote Share", get_constituency_list(year=2026, filter_type='under35'))

# ==============================================================================
# TAB 5: TURNOUT DYNAMICS
# ==============================================================================
with tab_turnout:
    st.markdown("### Voter Turnout Analysis")
    st.markdown(
        "Voter turnout registered a massive +12.70pp increase state-wide, climbing from 73.37% to 86.07%. "
        "Chennai Metro had the largest turnout jump (+21.19pp) following a massive ghost voter cleanup, "
        "while South TN turnout lagged due to outmigration."
    )
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("#### 10. Region-wise Turnout Comparison (2021 vs 2026)")
        st.markdown("Interactive comparison of voter turnout percentages across the 6 regions.")
        
        # Turnout by region calculations
        region_to21 = df21.groupby(['ac_number','region'])['turnout'].first().reset_index().groupby('region')['turnout'].mean().reset_index(name='2021')
        region_to26 = votes_cast_26.merge(master[['ac_number','region']], on='ac_number', how='left').groupby('region')['turnout_26'].mean().reset_index(name='2026')
        region_to_df = region_to21.merge(region_to26, on='region')
        
        fig_reg_to = go.Figure()
        fig_reg_to.add_trace(go.Bar(
            x=region_to_df['region'], y=region_to_df['2021'],
            name='2021 Turnout %',
            marker_color='#718096'
        ))
        fig_reg_to.add_trace(go.Bar(
            x=region_to_df['region'], y=region_to_df['2026'],
            name='2026 Turnout %',
            marker_color=accent_color
        ))
        
        fig_reg_to.update_layout(
            barmode='group',
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Turnout (%)", showgrid=True, gridcolor='#2D3748', range=[50, 100]),
            height=350,
            margin=dict(l=30, r=10, t=10, b=30)
        )
        st.plotly_chart(fig_reg_to, use_container_width=True)
        
    with col_t2:
        st.markdown("#### 📊 Reserved vs General Category Analysis (2026)")
        st.markdown(
            "Comparing seat shares in Reserved seats (SC/ST - 46 total) vs General seats (188 total) "
            "shows TVK won proportionally across both categories, signaling a broad-based wave."
        )
        
        # Donuts for Reserved vs General
        res_seats = winners26[winners26['reserved'].isin(['SC', 'ST'])].groupby('party').size().reset_index(name='count')
        gen_seats = winners26[~winners26['reserved'].isin(['SC', 'ST'])].groupby('party').size().reset_index(name='count')
        
        fig_donuts = make_subplots(
            rows=1, cols=2,
            specs=[[{'type':'domain'}, {'type':'domain'}]],
            subplot_titles=["Reserved Seats (46)", "General Seats (188)"]
        )
        
        fig_donuts.add_trace(go.Pie(
            labels=res_seats['party'],
            values=res_seats['count'],
            hole=0.4,
            marker_colors=[PARTY_COLORS.get(p, '#9E9E9E') for p in res_seats['party']],
            name="Reserved"
        ), 1, 1)
        
        fig_donuts.add_trace(go.Pie(
            labels=gen_seats['party'],
            values=gen_seats['count'],
            hole=0.4,
            marker_colors=[PARTY_COLORS.get(p, '#9E9E9E') for p in gen_seats['party']],
            name="General"
        ), 1, 2)
        
        fig_donuts.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#E2E8F0",
            height=350,
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_donuts, use_container_width=True)
        
    st.markdown("---")
    
    col_tbl1, col_tbl2 = st.columns(2)
    
    with col_tbl1:
        st.markdown("#### 🏆 Top 5 Turnout Constituencies (2026)")
        to26_c = votes_cast_26.merge(master[['ac_number','constituency','region']], on='ac_number', how='left')
        to26_c = to26_c.sort_values('turnout_26', ascending=False).head(5)[['constituency', 'region', 'turnout_26']]
        to26_c.columns = ['Constituency', 'Region', 'Turnout 2026 (%)']
        st.dataframe(to26_c, width="stretch", hide_index=True)
        
    with col_tbl2:
        st.markdown("#### 📉 Bottom 5 Turnout Constituencies (2026)")
        to26_c_bot = votes_cast_26.merge(master[['ac_number','constituency','region']], on='ac_number', how='left')
        to26_c_bot = to26_c_bot.sort_values('turnout_26', ascending=True).head(5)[['constituency', 'region', 'turnout_26']]
        to26_c_bot.columns = ['Constituency', 'Region', 'Turnout 2026 (%)']
        st.dataframe(to26_c_bot, width="stretch", hide_index=True)
        
    st.markdown("---")
    
    st.markdown("#### 🏛️ Reservation Category Turnout Stats Table")
    st.markdown("Click on any count below to see the list of constituencies in that category.")
    
    # Turnout by reservation table
    res_to = master[['ac_number','reserved']].merge(votes_cast_26[['ac_number','turnout_26']], on='ac_number')
    res_to_21 = df21.groupby('ac_number')['turnout'].first().reset_index().rename(columns={'turnout':'turnout_21'})
    res_to = res_to.merge(res_to_21, on='ac_number', how='left')
    
    res_stats_rows = []
    for cat in ['SC','ST','GEN']:
        sub = res_to[res_to['reserved'] == cat]
        res_stats_rows.append({
            'Category': cat,
            'Count': len(sub),
            'Avg Turnout 2021 (%)': sub['turnout_21'].mean(),
            'Avg Turnout 2026 (%)': sub['turnout_26'].mean(),
            'Min Turnout 2026 (%)': sub['turnout_26'].min(),
            'Max Turnout 2026 (%)': sub['turnout_26'].max(),
        })
    res_stats_df = pd.DataFrame(res_stats_rows)
    
    # Headers
    col_hdr = st.columns([1, 1, 2, 2, 2, 2])
    col_hdr[0].markdown("**Category**")
    col_hdr[1].markdown("**Constituencies**")
    col_hdr[2].markdown("**Avg Turnout 2021 (%)**")
    col_hdr[3].markdown("**Avg Turnout 2026 (%)**")
    col_hdr[4].markdown("**Min Turnout 2026 (%)**")
    col_hdr[5].markdown("**Max Turnout 2026 (%)**")
    
    for idx, row in res_stats_df.iterrows():
        cols = st.columns([1, 1, 2, 2, 2, 2])
        cols[0].write(f"**{row['Category']}**")
        
        # Count Button
        cnt = int(row['Count'])
        if cols[1].button(f"{cnt}", key=f"res_cnt_{row['Category']}"):
            show_constituency_list_modal(
                f"Constituencies in {row['Category']} Category ({cnt} total)",
                get_constituency_list(year=2026, reserved=row['Category'])
            )
            
        cols[2].write(f"{row['Avg Turnout 2021 (%)']:.2f}%")
        cols[3].write(f"{row['Avg Turnout 2026 (%)']:.2f}%")
        cols[4].write(f"{row['Min Turnout 2026 (%)']:.2f}%")
        cols[5].write(f"{row['Max Turnout 2026 (%)']:.2f}%")

# ==============================================================================
# TAB 6: CONSTITUENCY EXPLORER
# ==============================================================================
with tab_explorer:
    st.markdown("### Constituency Explorer & Deep-Dive")
    st.markdown("Select any constituency below to explore candidate-level breakdowns, margins, and turnouts across both 2021 and 2026.")
    
    # Dropdowns for quick search
    col_ex1, col_ex2 = st.columns(2)
    with col_ex1:
        sel_region = st.selectbox("Filter by Region:", ["All"] + sorted(master['region'].unique()))
    with col_ex2:
        if sel_region == "All":
            avail_const = sorted(master['constituency'].unique())
        else:
            avail_const = sorted(master[master['region'] == sel_region]['constituency'].unique())
            
        sel_const = st.selectbox("Select Constituency to inspect:", avail_const)
        
    # Get constituency details
    ac_num = master[master['constituency'] == sel_const]['ac_number'].values[0]
    
    st.markdown(f"## {sel_const} (AC Number {ac_num})")
    
    # Meta information row
    meta_sub = master[master['ac_number'] == ac_num].iloc[0]
    st.markdown(f"**District:** {meta_sub['district']} | **Region:** {meta_sub['region']} | **Category:** {meta_sub['reserved']}")
    
    col_tab_21, col_tab_26 = st.columns(2)
    
    with col_tab_21:
        st.markdown("#### 📊 2021 Detailed Results")
        res_21 = df21[df21['ac_number'] == ac_num].copy()
        res_21['Vote Share %'] = (res_21['votes'] / res_21['votes'].sum() * 100).round(2)
        res_21 = res_21.sort_values('votes', ascending=False)
        
        st.dataframe(
            res_21[['candidate', 'party', 'votes', 'Vote Share %']],
            column_config={
                "candidate": "Candidate",
                "party": "Party",
                "votes": st.column_config.NumberColumn("Votes", format="%d"),
                "Vote Share %": st.column_config.NumberColumn("Share %", format="%.2f%%")
            },
            width="stretch",
            hide_index=True
        )
        
        # Turnout
        to_val_21 = res_21['turnout'].iloc[0]
        st.info(f"**2021 Voter Turnout:** {to_val_21:.2f}%")
        
    with col_tab_26:
        st.markdown("#### 📊 2026 Detailed Results")
        res_26 = df26[df26['ac_number'] == ac_num].copy()
        res_26['Vote Share %'] = (res_26['votes'] / res_26['votes'].sum() * 100).round(2)
        res_26 = res_26.sort_values('votes', ascending=False)
        
        st.dataframe(
            res_26[['candidate', 'party', 'votes', 'Vote Share %']],
            column_config={
                "candidate": "Candidate",
                "party": "Party",
                "votes": st.column_config.NumberColumn("Votes", format="%d"),
                "Vote Share %": st.column_config.NumberColumn("Share %", format="%.2f%%")
            },
            width="stretch",
            hide_index=True
        )
        
        # Turnout
        to_val_26 = res_26['turnout_26'].iloc[0]
        st.info(f"**2026 Voter Turnout:** {to_val_26:.2f}%")
        
    # Margin details comparison
    w21 = winners21[winners21['ac_number'] == ac_num].iloc[0]
    w26 = winners26[winners26['ac_number'] == ac_num].iloc[0]
    
    st.markdown("### 📊 Victory Margin Shift")
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.markdown(f"**2021 Winner:** {w21['candidate']} ({w21['party']})")
        st.markdown(f"**Winning Margin:** {w21['margin']:,} votes ({w21['win_pct']:.2f}% share)")
    with col_v2:
        st.markdown(f"**2026 Winner:** {w26['candidate']} ({w26['party']})")
        st.markdown(f"**Winning Margin:** {w26['margin']:,} votes ({w26['win_pct']:.2f}% share)")
    with col_v3:
        diff_margin = w26['margin'] - w21['margin']
        diff_str = f"+{diff_margin:,}" if diff_margin > 0 else f"{diff_margin:,}"
        color_diff = "#48BB78" if diff_margin > 0 else "#E53E3E"
        st.markdown(f"**Margin Change:** <span style='color:{color_diff}; font-weight:600;'>{diff_str}</span> votes", unsafe_allow_html=True)
        
        # Check if flipped
        if w21['party'] != w26['party']:
            st.warning(f"🔄 **Seat Flipped:** {w21['party']} ➔ {w26['party']}")
        else:
            st.success(f"🔒 **Seat Retained:** {w26['party']} Held")

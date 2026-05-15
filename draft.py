import streamlit as st
import pandas as pd
import json
import os
import requests

st.set_page_config(page_title="SSL Prospect Draft Manager", layout="wide")

# --- DATA DICTIONARIES & DEFAULTS ---
DB_FILE = "draft_database.json"
ADMIN_PASSWORD = "ssladmin"

TEAM_TO_ORG = {
    'ACR': 'ROME & LONDON', 'SFV': 'BLACK FOREST & MONTREAL', 'TOK': 'TOKYO & CAIRO',
    'CABA': 'BUENOS AIRES & ATHENAI', 'USP': 'SAO PAULO & PARIS', 'XLC': 'XELAJU & MASQUES',
    'LIF': 'LIFFEYSIDE & ROVA', 'CDT': 'TENOCHTITLAN & KRUNG', 'RKV': 'REYKJAVIK & NORTH SHORE',
    'SHA': 'SHANGHAI & MAGYAR', 'HOL': 'HOLLYWOOD & CAPE TOWN', 'CAT': 'CATALUNYA & SEOUL'
}

API_NAME_TO_CODE = {
    "A.C. Romana": "ACR", "Schwarzwälder FV": "SFV", "Tokyo S.C.": "TOK",
    "CA Buenos Aires": "CABA", "União São Paulo": "USP", "Xelajú Cósmico FC": "XLC",
    "Liffeyside Celtic FC": "LIF", "CD Tenochtitlan": "CDT", "Reykjavik United": "RKV",
    "Shanghai Dragons FC": "SHA", "Hollywood FC": "HOL", "CF Catalunya": "CAT"
}

# Base colors for the Orgs/Teams to use in badges
ORG_COLORS = {
    'BLACK FOREST & MONTREAL': '#1F1F1F', 'BUENOS AIRES & ATHENAI': '#E73F02',
    'CATALUNYA & SEOUL': '#DD2025', 'HOLLYWOOD & CAPE TOWN': '#0A1B33',
    'LIFFEYSIDE & ROVA': '#018749', 'REYKJAVIK & NORTH SHORE': '#53E048',
    'ROME & LONDON': '#5C1466', 'SAO PAULO & PARIS': '#E52525',
    'SHANGHAI & MAGYAR': '#B9975B', 'TENOCHTITLAN & KRUNG': '#DCB325',
    'TOKYO & CAIRO': '#18A68E', 'XELAJU & MASQUES': '#0E6866'
}

ORG_LIST = sorted(list(set(TEAM_TO_ORG.values())))
TEAM_CODES = list(TEAM_TO_ORG.keys())

# Default Standings (Fallback if API fails)
DEFAULT_DIV1 = ['CAT', 'HOL', 'SHA', 'RKV', 'USP', 'XLC'] 
DEFAULT_DIV2 = ['LIF', 'CDT', 'CABA', 'TOK', 'SFV', 'ACR'] 

DEFAULT_PICKS = {
    "S26 ACR 1st": "ROME & LONDON", "S26 ACR 2nd": "HOLLYWOOD & CAPE TOWN", "S26 ACR 3rd": "HOLLYWOOD & CAPE TOWN", "S26 ACR 4th": "HOLLYWOOD & CAPE TOWN",
    "S26 CABA 1st": "BUENOS AIRES & ATHENAI", "S26 CABA 2nd": "BUENOS AIRES & ATHENAI", "S26 CABA 3rd": "TOKYO & CAIRO", "S26 CABA 4th": "BUENOS AIRES & ATHENAI",
    "S26 CAT 1st": "CATALUNYA & SEOUL", "S26 CAT 2nd": "CATALUNYA & SEOUL", "S26 CAT 3rd": "TOKYO & CAIRO", "S26 CAT 4th": "SAO PAULO & PARIS",
    "S26 CDT 1st": "SHANGHAI & MAGYAR", "S26 CDT 2nd": "SHANGHAI & MAGYAR", "S26 CDT 3rd": "ROME & LONDON", "S26 CDT 4th": "TENOCHTITLAN & KRUNG",
    "S26 HOL 1st": "HOLLYWOOD & CAPE TOWN", "S26 HOL 2nd": "HOLLYWOOD & CAPE TOWN", "S26 HOL 3rd": "HOLLYWOOD & CAPE TOWN", "S26 HOL 4th": "HOLLYWOOD & CAPE TOWN",
    "S26 LIF 1st": "LIFFEYSIDE & ROVA", "S26 LIF 2nd": "LIFFEYSIDE & ROVA", "S26 LIF 3rd": "BLACK FOREST & MONTREAL", "S26 LIF 4th": "CATALUNYA & SEOUL",
    "S26 RKV 1st": "REYKJAVIK & NORTH SHORE", "S26 RKV 2nd": "REYKJAVIK & NORTH SHORE", "S26 RKV 3rd": "REYKJAVIK & NORTH SHORE", "S26 RKV 4th": "REYKJAVIK & NORTH SHORE",
    "S26 SFV 1st": "BLACK FOREST & MONTREAL", "S26 SFV 2nd": "BLACK FOREST & MONTREAL", "S26 SFV 3rd": "SHANGHAI & MAGYAR", "S26 SFV 4th": "BLACK FOREST & MONTREAL",
    "S26 SHA 1st": "SHANGHAI & MAGYAR", "S26 SHA 2nd": "TENOCHTITLAN & KRUNG", "S26 SHA 3rd": "SHANGHAI & MAGYAR", "S26 SHA 4th": "SHANGHAI & MAGYAR",
    "S26 TOK 1st": "BLACK FOREST & MONTREAL", "S26 TOK 2nd": "SAO PAULO & PARIS", "S26 TOK 3rd": "TOKYO & CAIRO", "S26 TOK 4th": "TOKYO & CAIRO",
    "S26 USP 1st": "SAO PAULO & PARIS", "S26 USP 2nd": "TOKYO & CAIRO", "S26 USP 3rd": "SAO PAULO & PARIS", "S26 USP 4th": "SAO PAULO & PARIS",
    "S26 XLC 1st": "XELAJU & MASQUES", "S26 XLC 2nd": "XELAJU & MASQUES", "S26 XLC 3rd": "XELAJU & MASQUES", "S26 XLC 4th": "XELAJU & MASQUES"
}

# --- DATABASE HANDLING ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {"picks": DEFAULT_PICKS, "div1": DEFAULT_DIV1, "div2": DEFAULT_DIV2}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    st.sidebar.success("✅ Changes permanently saved!")

if 'db_data' not in st.session_state:
    st.session_state.db_data = load_db()

# --- API INTEGRATION ---
def fetch_api_standings():
    try:
        response = requests.get('https://api.simulationsoccer.com/index/standings?season=25&league=1', timeout=10)
        if response.status_code == 200:
            data = response.json()
            div1_data = [d for d in data if str(d.get('matchday')) == "1"]
            div2_data = [d for d in data if str(d.get('matchday')) == "2"]
            div1_data.sort(key=lambda x: (x.get('p', 0), x.get('gd', 0), x.get('gf', 0)), reverse=True)
            div2_data.sort(key=lambda x: (x.get('p', 0), x.get('gd', 0), x.get('gf', 0)), reverse=True)
            st.session_state.db_data['div1'] = [API_NAME_TO_CODE.get(t['team'], 'CAT') for t in div1_data]
            st.session_state.db_data['div2'] = [API_NAME_TO_CODE.get(t['team'], 'LIF') for t in div2_data]
            st.toast("✅ Standings successfully updated from API!")
        else:
            st.error("Failed to fetch standings from the API.")
    except Exception as e:
        st.error(f"Error fetching API: {e}")

# --- HELPER: CSS BADGE GENERATOR ---
def create_badge(pick_string):
    # pick_string is e.g. "S26 TOK 1st"
    parts = pick_string.split()
    if len(parts) == 3:
        season, team, rnd = parts
        org = TEAM_TO_ORG.get(team, 'ROME & LONDON')
        color = ORG_COLORS.get(org, '#888888')
        
        # Determine text color based on background luminance
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        text_color = 'white' if (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.5 else 'black'
        
        badge_html = f"""
        <div style="
            display: inline-block;
            background-color: {color};
            color: {text_color};
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: bold;
            margin: 2px 0px;
            border: 1px solid rgba(255,255,255,0.2);
            box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
        ">
            {team} {rnd}
        </div>
        """
        return badge_html
    return pick_string

# --- SIDEBAR (Controls & Admin) ---
st.sidebar.title("Draft Settings ⚙️")
promotes = st.sidebar.radio("Major League Promotion Scenarios:", [1, 2], index=1, format_func=lambda x: f"{x} Team(s) Promoted")

st.sidebar.divider()
st.sidebar.subheader("Admin Login 🔐")
pwd = st.sidebar.text_input("Password for permanent saves:", type="password")
is_admin = (pwd == ADMIN_PASSWORD)

if is_admin:
    st.sidebar.success("Admin Mode Unlocked.")
    if st.sidebar.button("💾 Save Current State to Database"):
        save_db(st.session_state.db_data)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🏆 Standings & Overrides", "💼 Assets & Trades", "📋 Draft Board"])

# --- TAB 1: STANDINGS ---
with tab1:
    st.header("Major League Standings")
    st.markdown("Pull live standings from the API, or double-click to manually tweak the ranks for 'What If' scenarios.")
    if st.button("🔄 Pull Live Standings from API", type="primary"):
        fetch_api_standings()
        st.rerun()
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Division 1")
        df_div1 = pd.DataFrame({"Rank": [1, 2, 3, 4, 5, 6], "Team Code": st.session_state.db_data['div1']})
        edited_div1 = st.data_editor(df_div1, hide_index=True, column_config={"Team Code": st.column_config.SelectboxColumn(options=TEAM_CODES, required=True)}, key="editor_div1", use_container_width=True)
        st.session_state.db_data['div1'] = edited_div1['Team Code'].tolist()

    with col2:
        st.subheader("Division 2")
        df_div2 = pd.DataFrame({"Rank": [1, 2, 3, 4, 5, 6], "Team Code": st.session_state.db_data['div2']})
        edited_div2 = st.data_editor(df_div2, hide_index=True, column_config={"Team Code": st.column_config.SelectboxColumn(options=TEAM_CODES, required=True)}, key="editor_div2", use_container_width=True)
        st.session_state.db_data['div2'] = edited_div2['Team Code'].tolist()

# --- TAB 2: ASSETS & TRADES (BADGE UI) ---
with tab2:
    st.header("Organization Assets 💼")
    st.markdown("View all S26 picks currently owned by each organization. **To trade a pick, select a new organization from the dropdown.**")
    st.divider()
    
    # Create a 2-column layout for the organizations
    cols = st.columns(2)
    
    for idx, org in enumerate(ORG_LIST):
        col = cols[idx % 2]
        
        # Find picks owned by this org and sort them (e.g. 1st, 2nd...)
        org_picks = [pick for pick, owner in st.session_state.db_data['picks'].items() if owner == org]
        org_picks.sort(key=lambda x: (x.split()[2], x.split()[1])) # Sort by Round then Team
        
        with col:
            with st.container(border=True):
                st.subheader(f"{org} ({len(org_picks)})")
                
                if not org_picks:
                    st.caption("No S26 picks currently owned.")
                
                for pick in org_picks:
                    # Layout: Badge on the left, Trade Dropdown on the right
                    b_col, t_col = st.columns([1, 1])
                    with b_col:
                        # Render the custom HTML badge
                        st.markdown(create_badge(pick), unsafe_allow_html=True)
                    with t_col:
                        new_owner = st.selectbox(
                            "Trade to:", 
                            options=ORG_LIST, 
                            index=ORG_LIST.index(org),
                            key=f"trade_{pick}",
                            label_visibility="collapsed"
                        )
                        if new_owner != org:
                            st.session_state.db_data['picks'][pick] = new_owner
                            st.rerun()
                st.markdown("<br>", unsafe_allow_html=True) # Spacing

# --- TAB 3: DRAFT BOARD ENGINE ---
with tab3:
    st.header(f"S26 Prospect Draft Order ({promotes} Promoted)")
    
    div1_standings = st.session_state.db_data['div1']
    div2_standings = st.session_state.db_data['div2']
    
    base_teams = [div2_standings[5], div2_standings[4], div2_standings[3], div2_standings[2]]
    end_teams = [div1_standings[3], div1_standings[2], div1_standings[1], div1_standings[0]]
    
    if promotes == 2:
        bubble_teams = [div1_standings[5], div1_standings[4], div2_standings[1], div2_standings[0]]
    else:
        bubble_teams = [div2_standings[1], div1_standings[5], div2_standings[0], div1_standings[4]]
        
    draft_order_teams = base_teams + bubble_teams + end_teams
    
    table_data = []
    for rd in range(1, 5):
        suffix = {1:'1st', 2:'2nd', 3:'3rd', 4:'4th'}[rd]
        for idx, team_code in enumerate(draft_order_teams):
            pick_id = f"S26 {team_code} {suffix}"
            current_owner = st.session_state.db_data['picks'].get(pick_id, TEAM_TO_ORG[team_code])
            
            table_data.append({
                "Round": rd,
                "Pick": (rd-1)*12 + (idx+1),
                "Current Owner": current_owner,
                "Original Pick": team_code
            })
            
    df_board = pd.DataFrame(table_data)
    
    def color_board(val):
        color = ORG_COLORS.get(val, '#FFFFFF')
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        text_color = 'white' if luminance < 0.5 else 'black'
        return f'background-color: {color}; color: {text_color}; font-weight: bold;'
    
    styled_df = df_board.style.map(color_board, subset=['Current Owner'])
    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=800)
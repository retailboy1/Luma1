"""
╔══════════════════════════════════════════════════════════════╗
║              LUMA · Full App  (landing → login → dash)       ║
║                    Created by Nancy Pelosi                   ║
╚══════════════════════════════════════════════════════════════╝

PASSWORD  (Digital Time Theory – NQ Root Numbers)
──────────────────────────────────────────────────
  √21000  =  144.9137674…   →  password  =  "1449137"

  Why 21000? It's the canonical NQ Gann Natural Square anchor.
  Hint shown to users reads:  "Ω · √(NQ∞) · Δτ"

  To change: edit PASSWORD = "…" below.

Run:
  streamlit run luma_crypto_forecast.py
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import timesfm
import torch
from datetime import datetime, timezone
import time
import base64
import os

# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LUMA", page_icon="🌙", layout="wide",
                   initial_sidebar_state="collapsed")

PASSWORD = "1449137"   # ← change to any secret you want

for k, v in [("page","landing"),("auth_err",False),("uploaded",[])]:
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────────────
def b64_img(path):
    if not os.path.exists(path): return ""
    with open(path,"rb") as f:
        ext  = path.rsplit(".",1)[-1].lower()
        mime = "jpeg" if ext in ("jpg","jpeg") else ext
        return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"

LOGO_URI = b64_img("logo.jpg") or b64_img("logo.png") or ""

INTERVAL_MINUTES  = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440}
INTERVAL_MAX_DAYS = {"1m":3,"5m":45,"15m":90,"30m":180,"1h":365,"4h":730,"1d":2000}
POPULAR_COINS     = {
    "Bitcoin (BTC)":"BTCUSDT","Ethereum (ETH)":"ETHUSDT",
    "Solana (SOL)":"SOLUSDT","XRP":"XRPUSDT","BNB":"BNBUSDT",
    "Cardano (ADA)":"ADAUSDT","Dogecoin (DOGE)":"DOGEUSDT","Custom…":"__custom__",
}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_binance(symbol, interval, days_back):
    url  = "https://api.binance.us/api/v3/klines"
    mins = INTERVAL_MINUTES[interval]
    want = min(int(days_back*1440/mins), 4000)
    rows, end_ms = [], int(datetime.now(timezone.utc).timestamp()*1000)
    while len(rows) < want:
        lim  = min(1000, want-len(rows))
        resp = requests.get(url, params={"symbol":symbol,"interval":interval,
                                         "endTime":end_ms,"limit":lim}, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        if not data or isinstance(data,dict): break
        rows   = data+rows
        end_ms = int(data[0][0])-1
        if len(data)<lim: break
    if not rows: raise ValueError(f"No data for {symbol}")
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","vol",
                                      "cts","qvol","tr","bb","bq","ign"])
    df["ts"] = pd.to_datetime(df["ts"],unit="ms",utc=True)
    df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
    return df[["open","high","low","close","vol"]].astype(float).rename(
        columns={"open":"Open","high":"High","low":"Low","close":"Close","vol":"Volume"})

def validate_symbol(symbol):
    try:
        r = requests.get("https://api.binance.us/api/v3/ticker/price",
                         params={"symbol":symbol},timeout=6)
        return r.status_code==200 and "price" in r.json()
    except: return False

@st.cache_resource(show_spinner=False)
def load_model():
    torch.set_float32_matmul_precision("high")
    m = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
        "google/timesfm-2.5-200m-pytorch", torch_compile=False)
    m.compile(timesfm.ForecastConfig(max_context=1024,max_horizon=512,
                                     normalize_inputs=True,use_continuous_quantile_head=True))
    return m

def get_ai(hf_key, symbol, summaries):
    lines = [f"You are a professional crypto analyst. Analyze LUMA forecasts for {symbol}:\n"]
    for tf, s in summaries.items():
        pct = (s["end"]-s["last"])/s["last"]*100
        lines.append(f"• {tf}: ${s['last']:.4f} → ${s['end']:.4f} "
                     f"({'▲' if pct>=0 else '▼'}{abs(pct):.1f}%)")
    lines.append("\n4–6 sentences: trend, key levels, multi-TF confluence, risk. No disclaimers.")
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions",
            headers={"Authorization":f"Bearer {hf_key}","Content-Type":"application/json"},
            json={"model":"mistralai/Mistral-7B-Instruct-v0.3",
                  "messages":[{"role":"user","content":"\n".join(lines)}],
                  "max_tokens":350,"temperature":0.6}, timeout=45)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e: return f"⚠️ {e}"


# ══════════════════════════════════════════════════════════════════════
#  PAGE 1 — LANDING
# ══════════════════════════════════════════════════════════════════════
def page_landing():
    logo_nav = (f'<img src="{LOGO_URI}" style="height:44px;width:auto;vertical-align:middle" />'
                if LOGO_URI else
                '<span style="font-family:\'Cormorant Garamond\',serif;font-size:2rem;font-weight:300;color:#f1f5f9;letter-spacing:.04em">🌙 LUMA</span>')

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400&display=swap');
*,html,body,[class*="css"]{{font-family:'Syne',sans-serif!important}}
.stApp{{background:#000!important;overflow-x:hidden}}
header[data-testid="stHeader"],#MainMenu,footer{{display:none!important}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}

.hero{{position:relative;width:100vw;min-height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.hbg{{position:absolute;inset:0;z-index:0;background:radial-gradient(ellipse 120% 80% at 65% 45%,#0a1628 0%,#060c18 40%,#000 100%)}}
.hgrid{{position:absolute;inset:0;z-index:1;opacity:.14;
  background-image:linear-gradient(rgba(100,160,255,.35) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(100,160,255,.35) 1px,transparent 1px);
  background-size:64px 64px;animation:gs 22s linear infinite}}
@keyframes gs{{to{{background-position:64px 64px}}}}
.hcandles{{position:absolute;right:5%;top:10%;width:44%;height:80%;z-index:2;opacity:.18;
  filter:blur(1.5px);
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 480 380'%3E%3Crect x='10' y='220' width='16' height='100' fill='%23f87171'/%3E%3Crect x='17' y='200' width='2' height='140' fill='%23f87171'/%3E%3Crect x='40' y='180' width='16' height='110' fill='%23f87171'/%3E%3Crect x='47' y='155' width='2' height='160' fill='%23f87171'/%3E%3Crect x='70' y='150' width='16' height='90' fill='%2334d399'/%3E%3Crect x='77' y='130' width='2' height='130' fill='%2334d399'/%3E%3Crect x='100' y='110' width='16' height='110' fill='%2334d399'/%3E%3Crect x='107' y='90' width='2' height='150' fill='%2334d399'/%3E%3Crect x='130' y='70' width='16' height='90' fill='%2334d399'/%3E%3Crect x='137' y='50' width='2' height='130' fill='%2334d399'/%3E%3Crect x='160' y='50' width='16' height='110' fill='%23f87171'/%3E%3Crect x='167' y='25' width='2' height='160' fill='%23f87171'/%3E%3Crect x='190' y='30' width='16' height='70' fill='%2334d399'/%3E%3Crect x='197' y='15' width='2' height='100' fill='%2334d399'/%3E%3Crect x='220' y='15' width='16' height='50' fill='%2334d399'/%3E%3Crect x='227' y='5' width='2' height='70' fill='%2334d399'/%3E%3C/svg%3E") no-repeat center/contain}}

.nav{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:26px 60px}}
.navlinks{{display:flex;gap:34px}}
.navlinks a{{color:#64748b;text-decoration:none;font-size:.82rem;font-weight:600;letter-spacing:.07em;text-transform:uppercase;transition:color .2s}}
.navlinks a:hover{{color:#f1f5f9}}

.hbody{{position:relative;z-index:10;flex:1;display:flex;flex-direction:column;justify-content:flex-end;padding:0 60px 90px 60px}}
.eyebrow{{color:#a78bfa;font-size:.76rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;margin-bottom:14px}}
.htitle{{font-family:'Cormorant Garamond',serif!important;font-size:clamp(3.8rem,7.5vw,7rem);font-weight:300;line-height:1.03;color:#f1f5f9;margin:0 0 18px 0}}
.htitle em{{font-style:italic;color:#a78bfa}}
.hsub{{color:#94a3b8;font-size:1rem;font-weight:400;max-width:520px;line-height:1.65;margin-bottom:44px}}

.strip{{position:relative;z-index:10;background:rgba(255,255,255,.035);border-top:1px solid rgba(255,255,255,.07);padding:11px 60px;display:flex;gap:40px;align-items:center}}
.si{{display:flex;align-items:center;gap:8px;white-space:nowrap}}
.si .sym{{color:#475569;font-size:.72rem;font-weight:700;letter-spacing:.09em}}
.si .px{{color:#94a3b8;font-size:.8rem;font-family:'JetBrains Mono',monospace!important}}
.si .up{{color:#34d399;font-size:.72rem}}
.si .dn{{color:#f87171;font-size:.72rem}}

/* launch button – override streamlit */
.stButton>button{{
  display:inline-flex!important;align-items:center;gap:10px;
  border:1px solid rgba(255,255,255,.22)!important;
  background:rgba(255,255,255,.045)!important;
  backdrop-filter:blur(10px);
  color:#fff!important;padding:14px 40px!important;border-radius:3px!important;
  font-size:.86rem!important;font-weight:700!important;letter-spacing:.09em;
  text-transform:uppercase;
  position:fixed;bottom:88px;left:60px;z-index:100;transition:all .25s
}}
.stButton>button:hover{{background:rgba(167,139,250,.18)!important;border-color:#a78bfa!important;color:#a78bfa!important}}
</style>

<div class="hero">
  <div class="hbg"></div>
  <div class="hgrid"></div>
  <div class="hcandles"></div>

  <nav class="nav">
    <div style="display:flex;align-items:center;gap:14px">
      {logo_nav}
      <span style="width:1px;height:28px;background:rgba(255,255,255,.12);display:inline-block;margin:0 4px"></span>
      <span style="color:#475569;font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase">Platform</span>
    </div>
    <div class="navlinks">
      <a href="#">Markets</a>
      <a href="#">Forecasts</a>
      <a href="#">Research</a>
      <a href="#">About</a>
    </div>
    <div style="width:80px"></div>
  </nav>

  <div class="hbody">
    <div class="eyebrow">Forming a View</div>
    <h1 class="htitle">LUMA <em>MarketView</em></h1>
    <p class="hsub">An AI-powered ecosystem of temporal forecasts answering
    critical questions in global crypto markets — driven by Digital Time Theory.</p>
  </div>

  <div class="strip">
    <div class="si"><span class="sym">BTC/USDT</span><span class="px">live</span><span class="up">▲</span></div>
    <div class="si"><span class="sym">ETH/USDT</span><span class="px">live</span><span class="up">▲</span></div>
    <div class="si"><span class="sym">SOL/USDT</span><span class="px">live</span><span class="dn">▼</span></div>
    <div class="si"><span class="sym">NQ  Δτ</span><span class="px">√(NQ∞)</span><span class="up">⊗</span></div>
    <div class="si"><span class="sym">XRP/USDT</span><span class="px">live</span><span class="up">▲</span></div>
    <div style="margin-left:auto;color:#1e2035;font-size:.68rem;letter-spacing:.09em">CREATED BY NANCY PELOSI</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("⊞  Launch LUMA"):
        st.session_state.page = "login"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE 2 — LOGIN
# ══════════════════════════════════════════════════════════════════════
def page_login():
    logo_html = (f'<img src="{LOGO_URI}" style="height:38px;width:auto" />'
                 if LOGO_URI else
                 '<span style="font-family:\'Cormorant Garamond\',serif;font-size:1.9rem;font-weight:300;color:#0f172a">🌙 LUMA</span>')

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Syne:wght@400;600;700&family=JetBrains+Mono:wght@300;400&display=swap');
*,html,body,[class*="css"]{{font-family:'Syne',sans-serif!important}}
.stApp{{background:#05080f!important}}
header,#MainMenu,footer{{display:none!important}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}

/* diagonal lines bg */
.lbg{{position:fixed;inset:0;z-index:0;overflow:hidden;background:#05080f}}
.dl{{position:absolute;background:rgba(255,255,255,.028);width:250%;height:1px;transform-origin:center}}

.lcard{{
  background:#fff;border-radius:2px;padding:50px 46px 42px;
  box-shadow:0 40px 100px rgba(0,0,0,.7);position:relative;z-index:10
}}
.ltop{{display:flex;align-items:center;gap:12px;margin-bottom:34px}}
.ldiv{{width:1px;height:28px;background:#e2e8f0}}
.ltitle{{color:#0f172a;font-size:1.3rem;font-weight:600;margin-bottom:24px}}
.lhint{{
  font-family:'JetBrains Mono',monospace!important;
  color:#6366f1;font-size:.72rem;letter-spacing:.14em;
  background:#f0f0ff;border:1px solid #c7d2fe;border-radius:4px;
  padding:9px 14px;text-align:center;margin-bottom:22px
}}
.stTextInput input{{
  border:1px solid #e2e8f0!important;border-radius:3px!important;
  padding:11px 14px!important;font-size:.9rem!important;
  color:#0f172a!important;background:#fff!important;
  box-shadow:none!important;outline:none!important
}}
.stTextInput input:focus{{border-color:#6366f1!important;box-shadow:0 0 0 3px rgba(99,102,241,.14)!important}}
.stTextInput label{{display:none!important}}
.stButton>button{{
  width:100%!important;background:#1e1b4b!important;color:#fff!important;
  border:none!important;border-radius:3px!important;padding:13px!important;
  font-size:.86rem!important;font-weight:700!important;letter-spacing:.07em;
  text-transform:uppercase;margin-top:6px
}}
.stButton>button:hover{{background:#312e81!important}}
.err{{color:#dc2626;font-size:.8rem;margin-top:8px;text-align:center}}
</style>

<div class="lbg">
  <div class="dl" style="top:22%;transform:rotate(-16deg)"></div>
  <div class="dl" style="top:42%;transform:rotate(-16deg)"></div>
  <div class="dl" style="top:62%;transform:rotate(-16deg)"></div>
  <div class="dl" style="top:82%;transform:rotate(-16deg)"></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.15, 1])
    with col:
        st.markdown(f"""
<div class="lcard">
  <div class="ltop">
    {logo_html}
    <div class="ldiv"></div>
    <span style="color:#64748b;font-size:.7rem;font-weight:700;letter-spacing:.11em;text-transform:uppercase">Secure Access</span>
  </div>
  <div class="ltitle">Sign In</div>
  <div class="lhint">Ω · √(NQ∞) · Δτ</div>
</div>
""", unsafe_allow_html=True)

        pw = st.text_input("pw", type="password",
                           placeholder="Enter temporal root sequence…",
                           label_visibility="collapsed")

        if st.session_state.auth_err:
            st.markdown('<div class="err">⊗ Invalid sequence. Recalibrate and try again.</div>',
                        unsafe_allow_html=True)

        if st.button("Continue  →"):
            if pw == PASSWORD:
                st.session_state.page = "dashboard"
                st.session_state.auth_err = False
                st.rerun()
            else:
                st.session_state.auth_err = True
                st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if st.button("← Back to home", key="back"):
            st.session_state.page     = "landing"
            st.session_state.auth_err = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
def page_dashboard():

    # ── sidebar ────────────────────────────────────────────────────
    with st.sidebar:
        if LOGO_URI:
            st.markdown(f'<img src="{LOGO_URI}" style="height:32px;margin-bottom:8px" />', unsafe_allow_html=True)
        else:
            st.markdown("### 🌙 LUMA")
        st.markdown("---")
        st.caption("🪙 **ASSET**")
        coin_choice = st.selectbox("Coin", list(POPULAR_COINS.keys()), label_visibility="collapsed")
        symbol = (st.text_input("Symbol","BTCUSDT").upper().strip()
                  if POPULAR_COINS[coin_choice]=="__custom__"
                  else POPULAR_COINS[coin_choice])
        st.caption("⏱ **TIMEFRAMES**")
        selected_tfs = st.multiselect("TFs", list(INTERVAL_MINUTES.keys()),
                                      default=["15m","1h","4h"], label_visibility="collapsed")
        st.caption("📅 **RANGE**")
        lookback_days = st.slider("Lookback",7,365,90,step=7,label_visibility="collapsed")
        forecast_days = st.slider("Forecast",1,30,7,label_visibility="collapsed")
        st.caption("🤖 **AI KEY**  (HuggingFace)")
        hf_key = st.text_input("HF Key",type="password",placeholder="hf_xxx…",label_visibility="collapsed")
        st.caption("📤 **UPLOAD CHARTS**")
        uploaded_files = st.file_uploader("Upload", type=["png","jpg","jpeg","gif","webp"],
                                          accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            st.session_state.uploaded = uploaded_files
        st.markdown("---")
        run_btn = st.button("⊞  Run LUMA Forecast", type="primary", use_container_width=True)
        if st.button("Sign Out", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()
        st.caption("🌙 LUMA · Created by Nancy Pelosi")

    # ── styles ─────────────────────────────────────────────────────
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=Syne:wght@400;600;700&display=swap');
*,[class*="css"]{font-family:'Syne',sans-serif!important}
.stApp{background:#080c1a!important}
header,#MainMenu,footer{display:none!important}
.block-container{padding:0 14px 28px 14px!important;max-width:100%!important}
section[data-testid="stSidebar"]{background:#05080f!important;border-right:1px solid #151d30}
section[data-testid="stSidebar"] .stButton>button{
  background:#1e293b!important;color:#94a3b8!important;border:1px solid #1e293b!important;
  border-radius:4px!important;font-size:.82rem!important;
}

/* ticker bar */
.tkbar{background:#0b0f1f;border-bottom:1px solid #131d35;padding:12px 22px;
  display:flex;align-items:center;flex-wrap:wrap;gap:20px;margin-bottom:2px}
.tksym{font-size:1.55rem;font-weight:700;color:#f1f5f9;
  font-family:'IBM Plex Mono',monospace!important;display:flex;align-items:center;gap:8px}
.tkbadge{background:#1e3a5f;color:#38bdf8;font-size:.62rem;font-weight:700;
  padding:3px 7px;border-radius:3px;letter-spacing:.08em}
.tkprice{font-family:'IBM Plex Mono',monospace!important;font-size:1.9rem;font-weight:400;color:#f1f5f9}
.pos{color:#34d399} .neg{color:#f87171}
.tkstat .l{color:#374151;font-size:.66rem;text-transform:uppercase;letter-spacing:.07em}
.tkstat .v{color:#94a3b8;font-size:.8rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}

/* info grid */
.igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));
  gap:1px;background:#131d35;border:1px solid #131d35;border-radius:4px;margin:10px 0;overflow:hidden}
.icell{background:#0b0f1f;padding:9px 15px}
.icell .l{color:#374151;font-size:.66rem;text-transform:uppercase;letter-spacing:.07em}
.icell .v{color:#cbd5e1;font-size:.84rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}

/* gain badge like image 3 */
.gbadge{display:inline-block;background:#0d2b0d;border:2px solid #34d399;
  color:#34d399;font-size:1rem;font-weight:700;padding:9px 20px;border-radius:4px;
  letter-spacing:.03em;margin:10px 0;font-family:'IBM Plex Mono',monospace!important}

.sh{color:#38bdf8;font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.12em;border-bottom:1px solid #131d35;padding-bottom:5px;margin:14px 0 8px}
.chwrap{background:#0b0f1f;border:1px solid #131d35;border-radius:4px;padding:3px;overflow:hidden}
</style>
""", unsafe_allow_html=True)

    # ── live price ─────────────────────────────────────────────────
    lp=lc=lv=None
    try:
        d = requests.get("https://api.binance.us/api/v3/ticker/24hr",
                         params={"symbol":symbol},timeout=5).json()
        lp,lc,lv = float(d.get("lastPrice",0)),float(d.get("priceChangePercent",0)),float(d.get("quoteVolume",0))
    except: pass
    ps  = f"${lp:,.2f}"     if lp else "—"
    cs  = f"{'▲' if (lc or 0)>=0 else '▼'} {abs(lc):.2f}%" if lc is not None else "—"
    cc  = "pos" if (lc or 0)>=0 else "neg"
    vs  = f"${lv/1e9:.2f}B" if lv else "—"
    ts  = datetime.now().strftime("%b %d  %H:%M:%S")

    st.markdown(f"""
<div class="tkbar">
  <div class="tksym">{symbol[:3]}<span class="tkbadge">CRYPTO</span></div>
  <div class="tkprice">{ps}</div>
  <div class="{cc}">{cs}</div>
  <div class="tkstat"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
  <div class="tkstat"><div class="l">Exchange</div><div class="v">Binance</div></div>
  <div class="tkstat"><div class="l">Pair</div><div class="v">{symbol}</div></div>
  <div style="margin-left:auto"><div class="tkstat"><div class="l">Updated</div><div class="v">{ts}</div></div></div>
</div>
""", unsafe_allow_html=True)

    # ── main layout ────────────────────────────────────────────────
    main_col, side_col = st.columns([3.2, 1])

    with main_col:
        if not run_btn:
            st.markdown("""
<div style="text-align:center;padding:130px 0;color:#1a2035">
  <div style="font-size:3.5rem">🌙</div>
  <div style="font-size:.95rem;margin-top:12px;color:#253352">Configure settings in sidebar → click Run LUMA Forecast</div>
</div>""", unsafe_allow_html=True)
        else:
            if not selected_tfs:
                st.warning("Select at least one timeframe."); return
            with st.spinner("Connecting to LUMA forecast engine…"):
                if not validate_symbol(symbol):
                    st.error(f"**{symbol}** not found on Binance. Use USDT pairs: BTCUSDT, ETHUSDT…")
                    return
                luma = load_model()

            COLORS = ["#a78bfa","#38bdf8","#fb923c","#34d399","#f472b6","#facc15"]
            fig = go.Figure()
            fcast_dfs, summaries, any_data = {}, {}, False
            prim = selected_tfs[0]
            prog = st.progress(0)

            for i, tf in enumerate(selected_tfs):
                prog.progress(i/len(selected_tfs), text=f"Processing {tf}…")
                col_c = COLORS[i%len(COLORS)]
                eff   = min(lookback_days, INTERVAL_MAX_DAYS[tf])
                try: df = fetch_binance(symbol, tf, eff)
                except Exception as e:
                    st.warning(f"⚠️ {tf}: {e}"); continue
                if len(df)<30: continue
                any_data = True
                prices, dates = df["Close"].values, df.index
                mins    = INTERVAL_MINUTES[tf]
                horizon = min(max(1, int(forecast_days*1440/mins)), 256)
                pt, _   = luma.forecast(horizon=horizon, inputs=[prices[-1024:]])
                fc      = pt[0]
                td      = pd.Timedelta(minutes=mins)
                fi      = pd.date_range(start=dates[-1]+td, periods=len(fc), freq=td, tz=dates.tzinfo)
                fcast_dfs[tf] = pd.DataFrame({"Datetime":fi,"Forecast":fc.round(6)})
                summaries[tf] = {"last":float(prices[-1]),"end":float(fc[-1]),"bars":len(fc)}

                sn = min(300, len(df))
                if tf == prim:
                    fig.add_trace(go.Candlestick(
                        x=dates[-sn:], open=df["Open"].iloc[-sn:], high=df["High"].iloc[-sn:],
                        low=df["Low"].iloc[-sn:], close=df["Close"].iloc[-sn:], name=f"Price ({tf})",
                        increasing_line_color="#34d399", decreasing_line_color="#f87171",
                        increasing_fillcolor="rgba(52,211,153,.16)",
                        decreasing_fillcolor="rgba(248,113,113,.16)"))
                else:
                    fig.add_trace(go.Scatter(x=dates[-sn:],y=prices[-sn:],mode="lines",
                        name=f"Price ({tf})",line=dict(color=col_c,width=1,dash="dot"),opacity=.5))
                r2,g2,b2 = int(col_c[1:3],16),int(col_c[3:5],16),int(col_c[5:7],16)
                fig.add_trace(go.Scatter(
                    x=list(fi)+list(fi[::-1]), y=list(fc*1.01)+list(fc[::-1]*0.99),
                    fill="toself", fillcolor=f"rgba({r2},{g2},{b2},.07)",
                    line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
                fig.add_trace(go.Scatter(x=fi,y=fc,mode="lines+markers",name=f"LUMA ({tf})",
                    line=dict(color=col_c,width=2.5,dash="dash"),marker=dict(size=5,symbol="diamond"),
                    hovertemplate="<b>%{x|%b %d %H:%M}</b><br>$%{y:,.4f}<extra></extra>"))

            prog.progress(1.0,"Done!"); time.sleep(.25); prog.empty()

            if not any_data:
                st.error("No data loaded. Check symbol or try different timeframes."); return

            fig.update_layout(
                paper_bgcolor="#0b0f1f", plot_bgcolor="#0b0f1f",
                font=dict(color="#94a3b8",family="IBM Plex Mono"),
                title=dict(text=f"🌙 LUMA · <b>{symbol}</b>  Multi-TF Forecast",
                           font=dict(color="#f1f5f9",size=14),x=0.01),
                xaxis=dict(gridcolor="#0f1729",linecolor="#131d35",
                           rangeslider=dict(visible=True,bgcolor="#07090f",thickness=.04)),
                yaxis=dict(gridcolor="#0f1729",linecolor="#131d35"),
                legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1,
                            bgcolor="rgba(0,0,0,0)",font=dict(size=10)),
                hovermode="x unified",height=510,margin=dict(l=28,r=28,t=65,b=28))

            st.markdown('<div class="chwrap">', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # gain badge + info grid
            best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/summaries[x]["last"]))
            bpct = (summaries[best]["end"]-summaries[best]["last"])/summaries[best]["last"]*100
            cells = ""
            for tf2, s in summaries.items():
                pct2 = (s["end"]-s["last"])/s["last"]*100
                cc2  = "#34d399" if pct2>=0 else "#f87171"
                arr2 = "▲" if pct2>=0 else "▼"
                cells += f"""
<div class="icell"><div class="l">LUMA {tf2}</div>
  <div class="v" style="color:{cc2}">{arr2} {abs(pct2):.2f}%</div></div>
<div class="icell"><div class="l">Forecast</div>
  <div class="v">${s['end']:,.4f}</div></div>"""
            st.markdown(f"""
<div class="gbadge">{symbol[:3]}  {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp;({best} forecast)</div>
<div class="igrid">{cells}</div>""", unsafe_allow_html=True)

            # AI
            if hf_key and summaries:
                st.markdown('<div class="sh">🤖 LUMA AI Analysis</div>', unsafe_allow_html=True)
                with st.spinner("Consulting the oracle…"):
                    ai_txt = get_ai(hf_key, symbol, summaries)
                st.markdown(f"""
<div style="background:#0c0d2b;border:1px solid #4c1d95;border-radius:6px;
  padding:18px 22px;color:#c4b5fd;line-height:1.78;font-size:.87rem">
{ai_txt.replace(chr(10),"<br>")}
</div>""", unsafe_allow_html=True)

            # tables + download
            st.markdown('<div class="sh">📋 Forecast Data</div>', unsafe_allow_html=True)
            for tf3, df_f in fcast_dfs.items():
                with st.expander(f"{tf3}  ·  {len(df_f)} bars"):
                    st.dataframe(df_f.style.format({"Forecast":"${:,.6f}"}),
                                 use_container_width=True)
            if fcast_dfs:
                st.download_button("⬇️ Download CSV",
                    data=pd.concat([d.assign(TF=t) for t,d in fcast_dfs.items()]).to_csv(index=False),
                    file_name=f"luma_{symbol}.csv", mime="text/csv")

    # ── right panel ────────────────────────────────────────────────
    with side_col:
        st.markdown('<div class="sh">📤 Uploaded Charts</div>', unsafe_allow_html=True)
        if st.session_state.uploaded:
            for uf in st.session_state.uploaded:
                ext = uf.name.rsplit(".",1)[-1].lower()
                if ext in ("png","jpg","jpeg","gif","webp"):
                    st.image(uf, use_container_width=True, caption=uf.name)
                else:
                    st.markdown(f"📄 `{uf.name}`")
        else:
            st.markdown("""
<div style="border:1px dashed #131d35;border-radius:6px;padding:28px 8px;
  text-align:center;color:#1e293b;font-size:.78rem">
  Upload charts<br>via sidebar
</div>""", unsafe_allow_html=True)

        if lp:
            st.markdown('<div class="sh" style="margin-top:18px">⚡ Live Stats</div>', unsafe_allow_html=True)
            st.markdown(f"""
<div class="igrid" style="grid-template-columns:1fr">
  <div class="icell"><div class="l">Last</div><div class="v">{ps}</div></div>
  <div class="icell"><div class="l">Change</div><div class="v {cc}">{cs}</div></div>
  <div class="icell"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════
p = st.session_state.page
if p == "landing":    page_landing()
elif p == "login":    page_login()
elif p == "dashboard":page_dashboard()
else:                 page_landing()

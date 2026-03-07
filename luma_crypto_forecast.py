"""
LUMA · Crypto Forecast Platform
Password: 953
Run: streamlit run luma_crypto_forecast.py
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import timesfm
import torch
from datetime import datetime, timezone
import time, base64, os, io

# ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LUMA", page_icon="🌙", layout="wide",
                   initial_sidebar_state="collapsed")

PASSWORD = "953"

DEFAULTS = {
    "page": "landing", "auth_err": False,
    "sub": "home",                    # home | forecast | upload | chat
    "chat_history": [], "summaries": {}, "symbol": "BTCUSDT",
    "fcast_dfs": {}, "raw_dfs": {},
    "uploaded_files": [], "initial_analysis": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────
#  LOGO
# ─────────────────────────────────────────────────────────────────────
def load_logo_b64():
    for p in ["logo.jpg","logo.png","./logo.jpg","./logo.png"]:
        try:
            if os.path.isfile(p):
                ext  = p.rsplit(".",1)[-1].lower()
                mime = "jpeg" if ext in ("jpg","jpeg") else "png"
                with open(p,"rb") as f:
                    return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
        except: pass
    return ""

LOGO_URI = load_logo_b64()

def logo_tag(h=40, dark=False):
    color = "#0f172a" if dark else "#f1f5f9"
    if LOGO_URI:
        return f'<img src="{LOGO_URI}" style="height:{h}px;width:auto;display:inline-block;vertical-align:middle" />'
    return (f'<span style="font-family:Georgia,serif;font-size:{h*0.75}px;'
            f'font-weight:300;color:{color};vertical-align:middle">🌙 LUMA</span>')

# ─────────────────────────────────────────────────────────────────────
#  DATA  (Binance.US — works in United States)
# ─────────────────────────────────────────────────────────────────────
BINANCE = "https://api.binance.us"
INTERVAL_MINUTES  = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440}
INTERVAL_MAX_DAYS = {"1m":3,"5m":45,"15m":90,"30m":180,"1h":365,"4h":730,"1d":2000}
POPULAR_COINS = {
    "Bitcoin":"BTCUSDT","Ethereum":"ETHUSDT","Solana":"SOLUSDT",
    "XRP":"XRPUSDT","BNB":"BNBUSDT","Cardano":"ADAUSDT",
    "Dogecoin":"DOGEUSDT","Avalanche":"AVAXUSDT","Custom…":"__custom__",
}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_binance(symbol, interval, days_back):
    url  = f"{BINANCE}/api/v3/klines"
    mins = INTERVAL_MINUTES[interval]
    want = min(int(days_back*1440/mins), 4000)
    rows, end_ms = [], int(datetime.now(timezone.utc).timestamp()*1000)
    while len(rows) < want:
        lim  = min(1000, want-len(rows))
        resp = requests.get(url, params={"symbol":symbol,"interval":interval,
                                         "endTime":end_ms,"limit":lim}, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        if not data or isinstance(data, dict): break
        rows = data + rows
        end_ms = int(data[0][0]) - 1
        if len(data) < lim: break
    if not rows: raise ValueError(f"No data for {symbol}")
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","vol",
                                      "cts","qvol","tr","bb","bq","ign"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
    return df[["open","high","low","close","vol"]].astype(float).rename(
        columns={"open":"Open","high":"High","low":"Low","close":"Close","vol":"Volume"})

def validate_symbol(sym):
    try:
        r = requests.get(f"{BINANCE}/api/v3/ticker/price", params={"symbol":sym}, timeout=5)
        return r.status_code==200 and "price" in r.json()
    except: return False

def live_ticker(sym):
    try:
        d = requests.get(f"{BINANCE}/api/v3/ticker/24hr", params={"symbol":sym}, timeout=5).json()
        return float(d.get("lastPrice",0)), float(d.get("priceChangePercent",0)), float(d.get("quoteVolume",0))
    except: return None, None, None

@st.cache_resource(show_spinner=False)
def load_model():
    torch.set_float32_matmul_precision("high")
    m = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
        "google/timesfm-2.5-200m-pytorch", torch_compile=False)
    m.compile(timesfm.ForecastConfig(max_context=1024, max_horizon=512,
                                     normalize_inputs=True, use_continuous_quantile_head=True))
    return m

# ─────────────────────────────────────────────────────────────────────
#  LUMA AI
# ─────────────────────────────────────────────────────────────────────
LUMA_PERSONA = """You are LUMA, an elite AI crypto market analyst.
You speak like a seasoned prop trader — sharp, direct, confident.
Give specific price levels, support/resistance, momentum reads, and risk notes.
Never mention any AI company, model name, or framework. You ARE LUMA.
Keep responses under 220 words unless asked for more.
Always reference the specific data provided to you."""

def luma_call(hf_key, messages):
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions",
            headers={"Authorization":f"Bearer {hf_key}","Content-Type":"application/json"},
            json={"model":"mistralai/Mistral-7B-Instruct-v0.3",
                  "messages":[{"role":"system","content":LUMA_PERSONA}]+messages,
                  "max_tokens":420,"temperature":0.65}, timeout=50)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e: return f"⚠️ LUMA offline: {e}"

def market_ctx(sym, summaries, raw_dfs):
    lines = [f"LIVE MARKET DATA — {sym}\n"]
    for tf, s in summaries.items():
        pct = (s["end"]-s["last"])/s["last"]*100
        lines.append(f"• {tf}: Now=${s['last']:.4f} | Forecast=${s['end']:.4f} | "
                     f"{'▲' if pct>=0 else '▼'}{abs(pct):.2f}% | {s['bars']} bars")
        if tf in raw_dfs:
            rc = raw_dfs[tf]["Close"].tail(20)
            lines.append(f"  20-bar range: H=${rc.max():.4f} L=${rc.min():.4f} Avg=${rc.mean():.4f}")
    return "\n".join(lines)

def do_analysis(hf_key, sym, summaries, raw_dfs):
    ctx = market_ctx(sym, summaries, raw_dfs)
    return luma_call(hf_key, [{"role":"user","content":
        f"{ctx}\n\nDeliver your LUMA analysis: trend direction, key levels, "
        f"multi-TF confluence, highest-conviction call, and one key risk. Be specific."}])

def do_chat(hf_key, sym, summaries, raw_dfs, question, history):
    ctx  = market_ctx(sym, summaries, raw_dfs)
    msgs = [{"role":"user","content":f"Context:\n{ctx}\n\nLoaded and ready."},
            {"role":"assistant","content":"Got it. I have the full data loaded. What's your question?"}]
    for h in history[-4:]:
        msgs += [{"role":"user","content":h["user"]},
                 {"role":"assistant","content":h["luma"]}]
    msgs.append({"role":"user","content":question})
    return luma_call(hf_key, msgs)

def analyze_uploaded_chart(hf_key, filename, note=""):
    prompt = (f"A trader has uploaded a chart image named '{filename}'. "
              f"{('Additional note: '+note) if note else ''} "
              f"Based on typical chart patterns and the file name context, "
              f"provide a general technical analysis framework they should apply. "
              f"Discuss what key things to look for on this chart, what signals "
              f"to watch for, and how it might relate to the LUMA forecast if available.")
    return luma_call(hf_key, [{"role":"user","content":prompt}])

# ─────────────────────────────────────────────────────────────────────
#  SHARED CSS
# ─────────────────────────────────────────────────────────────────────
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500&display=swap');
*,html,body,[class*="css"]{font-family:'Syne',sans-serif!important}
header[data-testid="stHeader"],#MainMenu,footer{display:none!important}
</style>
"""

# ══════════════════════════════════════════════════════════════════════
#  PAGE 1 — LANDING
# ══════════════════════════════════════════════════════════════════════
def page_landing():
    st.markdown(BASE_CSS + f"""
<style>
.stApp{{background:#000!important;overflow-x:hidden}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}
.hero{{position:relative;width:100vw;min-height:100vh;display:flex;flex-direction:column}}
.hbg{{position:absolute;inset:0;z-index:0;
  background:radial-gradient(ellipse 130% 90% at 65% 40%,#0a1628 0%,#040810 50%,#000 100%)}}
.hgrid{{position:absolute;inset:0;z-index:1;opacity:.11;
  background-image:linear-gradient(rgba(120,160,255,.4) 1px,transparent 1px),
  linear-gradient(90deg,rgba(120,160,255,.4) 1px,transparent 1px);
  background-size:70px 70px;animation:gs 24s linear infinite}}
@keyframes gs{{to{{background-position:70px 70px}}}}
.hcandles{{position:absolute;right:4%;top:8%;width:46%;height:84%;z-index:2;opacity:.14;filter:blur(2px);
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 400'%3E%3Crect x='10' y='230' width='18' height='110' fill='%23f87171'/%3E%3Crect x='18' y='210' width='2' height='150' fill='%23f87171'/%3E%3Crect x='44' y='190' width='18' height='120' fill='%23f87171'/%3E%3Crect x='52' y='165' width='2' height='170' fill='%23f87171'/%3E%3Crect x='78' y='155' width='18' height='100' fill='%2334d399'/%3E%3Crect x='86' y='132' width='2' height='145' fill='%2334d399'/%3E%3Crect x='112' y='112' width='18' height='120' fill='%2334d399'/%3E%3Crect x='120' y='88' width='2' height='165' fill='%2334d399'/%3E%3Crect x='146' y='72' width='18' height='100' fill='%2334d399'/%3E%3Crect x='154' y='48' width='2' height='145' fill='%2334d399'/%3E%3Crect x='180' y='48' width='18' height='120' fill='%23f87171'/%3E%3Crect x='188' y='22' width='2' height='170' fill='%23f87171'/%3E%3Crect x='214' y='28' width='18' height='78' fill='%2334d399'/%3E%3Crect x='222' y='12' width='2' height='110' fill='%2334d399'/%3E%3C/svg%3E") no-repeat center/contain}}
.nav{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:28px 64px}}
.navlinks{{display:flex;gap:36px}}
.navlinks a{{color:#4a5568;text-decoration:none;font-size:.8rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;transition:color .2s}}
.navlinks a:hover{{color:#e2e8f0}}
.hbody{{position:relative;z-index:10;flex:1;display:flex;flex-direction:column;justify-content:flex-end;padding:0 64px 96px 64px}}
.eyebrow{{color:#a78bfa;font-size:.74rem;font-weight:700;letter-spacing:.22em;text-transform:uppercase;margin-bottom:16px}}
.htitle{{font-family:'Cormorant Garamond',serif!important;font-size:clamp(4rem,8vw,7.5rem);
  font-weight:300;line-height:1.02;color:#f1f5f9;margin:0 0 20px 0}}
.htitle em{{font-style:italic;color:#a78bfa}}
.hsub{{color:#64748b;font-size:1rem;max-width:500px;line-height:1.68;margin-bottom:48px}}
.strip{{position:relative;z-index:10;background:rgba(255,255,255,.03);
  border-top:1px solid rgba(255,255,255,.06);padding:12px 64px;display:flex;gap:44px;align-items:center}}
.si .sym{{color:#334155;font-size:.7rem;font-weight:700;letter-spacing:.09em}}
.si .px{{color:#64748b;font-size:.78rem;font-family:'IBM Plex Mono',monospace!important}}
.si .up{{color:#34d399;font-size:.7rem}} .si .dn{{color:#f87171;font-size:.7rem}}
.stButton>button{{display:inline-flex!important;align-items:center;gap:10px;
  border:1px solid rgba(255,255,255,.2)!important;background:rgba(15,20,40,.6)!important;
  backdrop-filter:blur(12px);color:#e2e8f0!important;padding:15px 44px!important;
  border-radius:3px!important;font-size:.84rem!important;font-weight:700!important;
  letter-spacing:.1em;text-transform:uppercase;
  position:fixed;bottom:92px;left:64px;z-index:200;transition:all .25s}}
.stButton>button:hover{{background:rgba(100,60,200,.35)!important;border-color:#a78bfa!important;color:#c4b5fd!important}}
</style>
<div class="hero">
  <div class="hbg"></div><div class="hgrid"></div><div class="hcandles"></div>
  <nav class="nav">
    <div style="display:flex;align-items:center;gap:16px">
      {logo_tag(48)}
      <span style="width:1px;height:30px;background:rgba(255,255,255,.1);display:inline-block"></span>
      <span style="color:#2d3748;font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Platform</span>
    </div>
    <div class="navlinks"><a href="#">Markets</a><a href="#">Forecasts</a><a href="#">About</a></div>
    <div style="width:80px"></div>
  </nav>
  <div class="hbody">
    <div class="eyebrow">Forming a View</div>
    <h1 class="htitle">LUMA <em>MarketView</em></h1>
    <p class="hsub">AI-powered temporal forecasts for global crypto markets.<br>Real-time data · Predictive charting · Intelligent analysis.</p>
  </div>
  <div class="strip">
    <div class="si" style="display:flex;align-items:center;gap:8px"><span class="sym">BTC/USDT</span><span class="up">▲ live</span></div>
    <div class="si" style="display:flex;align-items:center;gap:8px"><span class="sym">ETH/USDT</span><span class="up">▲ live</span></div>
    <div class="si" style="display:flex;align-items:center;gap:8px"><span class="sym">SOL/USDT</span><span class="dn">▼ live</span></div>
    <div class="si" style="display:flex;align-items:center;gap:8px"><span class="sym">NQ · Δτ</span><span class="px">√(NQ∞)</span><span class="up">⊗</span></div>
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
    err = ('<p style="color:#dc2626;font-size:.82rem;text-align:center;margin:0 0 14px">'
           '⊗ &nbsp;Invalid sequence. Recalibrate and try again.</p>'
           if st.session_state.auth_err else "")

    st.markdown(BASE_CSS + f"""
<style>
.stApp{{background:#04060f!important}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}
.lbg{{position:fixed;inset:0;z-index:0;background:#04060f;overflow:hidden}}
.dl{{position:absolute;background:rgba(255,255,255,.022);width:260%;height:1px;transform-origin:center center}}
div[data-testid="column"]:nth-child(2)>div>div{{
  background:#ffffff;border-radius:8px;padding:46px 42px 38px!important;
  box-shadow:0 48px 120px rgba(0,0,0,.8);position:relative;z-index:10;margin-top:8vh}}
.stTextInput input{{
  border:1.5px solid #e2e8f0!important;border-radius:6px!important;
  padding:14px 16px!important;font-size:1rem!important;color:#0f172a!important;
  background:#f8fafc!important;box-shadow:none!important;outline:none!important;width:100%!important}}
.stTextInput input:focus{{border-color:#6366f1!important;background:#fff!important;
  box-shadow:0 0 0 3px rgba(99,102,241,.15)!important}}
.stTextInput input::placeholder{{color:#94a3b8!important;font-size:.88rem!important}}
.stTextInput label{{display:none!important}}
div[data-testid="InputInstructions"]{{display:none!important}}
.stButton:first-of-type>button{{
  width:100%!important;background:#1e1b4b!important;color:#fff!important;
  border:none!important;border-radius:6px!important;padding:14px!important;
  font-size:.88rem!important;font-weight:700!important;letter-spacing:.07em;
  text-transform:uppercase;margin-top:4px;position:static!important}}
.stButton:first-of-type>button:hover{{background:#3730a3!important}}
.stButton:last-of-type>button{{
  width:100%!important;background:transparent!important;color:#94a3b8!important;
  border:1.5px solid #e2e8f0!important;border-radius:6px!important;padding:10px!important;
  font-size:.82rem!important;font-weight:600!important;margin-top:6px;position:static!important}}
.stButton:last-of-type>button:hover{{color:#475569!important;border-color:#cbd5e1!important}}
</style>
<div class="lbg">
  <div class="dl" style="top:20%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:40%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:60%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:80%;transform:rotate(-14deg)"></div>
</div>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:28px">
  {logo_tag(40, dark=True)}
  <div style="width:1px;height:30px;background:#e2e8f0;flex-shrink:0"></div>
  <span style="color:#94a3b8;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Secure Access</span>
</div>
<h2 style="color:#0f172a;font-size:1.4rem;font-weight:700;margin:0 0 6px">Sign In</h2>
<p style="color:#94a3b8;font-size:.82rem;margin:0 0 22px">Enter your access key to continue</p>
<div style="background:#f0f0ff;border:1.5px solid #c7d2fe;border-radius:6px;
  padding:10px 16px;text-align:center;margin-bottom:18px;
  font-family:'IBM Plex Mono',monospace;font-size:.76rem;color:#6366f1;letter-spacing:.16em">
  Ω · √(NQ∞) · Δτ
</div>
<p style="color:#475569;font-size:.78rem;font-weight:600;margin:0 0 8px">ACCESS KEY</p>
{err}
""", unsafe_allow_html=True)

        pw = st.text_input("key", type="password",
                           placeholder="Enter temporal root sequence…",
                           label_visibility="collapsed", key="pw_input")
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("Continue  →", use_container_width=True):
            if pw == PASSWORD:
                st.session_state.page = "dashboard"
                st.session_state.sub  = "home"
                st.session_state.auth_err = False
                st.rerun()
            else:
                st.session_state.auth_err = True
                st.rerun()

        if st.button("← Back to home", use_container_width=True, key="back_btn"):
            st.session_state.page = "landing"
            st.session_state.auth_err = False
            st.rerun()
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD SHELL  (nav bar + sub-page routing)
# ══════════════════════════════════════════════════════════════════════
def dash_shell():
    """Top nav bar shared by all dashboard sub-pages."""
    active = st.session_state.sub
    def nav_style(page):
        if active == page:
            return ("background:#1e293b;color:#f1f5f9;border-bottom:2px solid #a78bfa;"
                    "padding:10px 20px;border-radius:4px 4px 0 0;cursor:pointer;"
                    "font-weight:700;font-size:.82rem;letter-spacing:.06em")
        return ("background:transparent;color:#4a5568;border-bottom:2px solid transparent;"
                "padding:10px 20px;cursor:pointer;font-size:.82rem;letter-spacing:.06em")

    st.markdown(BASE_CSS + """
<style>
.stApp{background:#080c1a!important}
.block-container{padding:0 0 28px 0!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none!important}
</style>
""", unsafe_allow_html=True)

    # Top nav
    nav_col = st.columns([2, 1, 1, 1, 1, 1, 0.8])
    with nav_col[0]:
        st.markdown(f"""
<div style="background:#0a0d1c;border-bottom:1px solid #111827;
  padding:14px 22px;display:flex;align-items:center;gap:14px">
  {logo_tag(32)}
  <span style="width:1px;height:22px;background:#1e293b;display:inline-block"></span>
  <span style="color:#334155;font-size:.68rem;font-weight:700;letter-spacing:.1em">PLATFORM</span>
</div>""", unsafe_allow_html=True)

    btn_labels = ["🏠 Home", "📊 Forecast", "📤 Upload", "💬 Ask LUMA", "⚙️ Settings"]
    btn_pages  = ["home",    "forecast",    "upload",    "chat",         "settings"]

    for i, (lbl, pg) in enumerate(zip(btn_labels, btn_pages)):
        with nav_col[i+1]:
            if st.button(lbl, key=f"nav_{pg}", use_container_width=True):
                st.session_state.sub = pg
                st.rerun()

    with nav_col[-1]:
        if st.button("Sign Out", key="signout", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()

    # Highlight active nav
    st.markdown(f"""
<style>
div[data-testid="stHorizontalBlock"] > div:nth-child(1) > div > div {{
  background:#0a0d1c;border-bottom:1px solid #111827;
}}
/* all nav buttons */
div[data-testid="stHorizontalBlock"] .stButton > button {{
  background:#0a0d1c!important;color:#4a5568!important;
  border:none!important;border-bottom:2px solid transparent!important;
  border-radius:0!important;padding:13px 8px!important;
  font-size:.78rem!important;font-weight:600!important;
  letter-spacing:.05em;width:100%;position:static!important;
  transition:all .18s;
}}
div[data-testid="stHorizontalBlock"] .stButton > button:hover {{
  color:#94a3b8!important;background:#0d1225!important;
}}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  SUB-PAGE: HOME  (cards grid)
# ══════════════════════════════════════════════════════════════════════
def sub_home():
    st.markdown("""
<style>
.home-wrap{padding:40px 32px}
.home-title{font-family:'Cormorant Garamond',serif!important;
  font-size:2.8rem;font-weight:300;color:#f1f5f9;line-height:1.1;margin-bottom:8px}
.home-title em{font-style:italic;color:#a78bfa}
.home-sub{color:#4a5568;font-size:.92rem;margin-bottom:36px}

/* feature cards */
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:40px}
.feat-card{
  background:#0d1225;border:1px solid #111827;border-radius:10px;
  padding:28px 26px;cursor:pointer;transition:all .22s;position:relative;overflow:hidden}
.feat-card:hover{border-color:#a78bfa;transform:translateY(-3px);
  box-shadow:0 12px 40px rgba(167,139,250,.15)}
.feat-card::before{content:'';position:absolute;inset:0;
  background:linear-gradient(135deg,rgba(167,139,250,.04),transparent);opacity:0;transition:.22s}
.feat-card:hover::before{opacity:1}
.card-icon{font-size:2.2rem;margin-bottom:16px}
.card-title{color:#f1f5f9;font-size:1.05rem;font-weight:700;margin-bottom:8px}
.card-desc{color:#4a5568;font-size:.82rem;line-height:1.65}
.card-tag{display:inline-block;background:#1a2035;color:#64748b;
  font-size:.66rem;font-weight:700;padding:3px 8px;border-radius:3px;
  letter-spacing:.07em;margin-top:14px;text-transform:uppercase}
.card-tag.live{background:#0d2b0d;color:#34d399}
.card-tag.ai{background:#1a103a;color:#a78bfa}
.card-tag.new{background:#2a1505;color:#fb923c}

/* quick stats bar */
.qs-bar{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:8px;
  margin-bottom:32px;overflow:hidden}
.qs-cell{background:#0a0d1c;padding:14px 18px}
.qs-cell .l{color:#374151;font-size:.63rem;text-transform:uppercase;letter-spacing:.07em}
.qs-cell .v{color:#f1f5f9;font-size:1.1rem;font-family:'IBM Plex Mono',monospace!important;margin-top:4px;font-weight:500}
.qs-cell .d{font-size:.78rem;margin-top:2px}
.pos{color:#34d399} .neg{color:#f87171}
</style>
""", unsafe_allow_html=True)

    # Live quick stats
    tickers = [("BTCUSDT","BTC"),("ETHUSDT","ETH"),("SOLUSDT","SOL"),("XRPUSDT","XRP")]
    cells   = ""
    for sym, name in tickers:
        lp, lc, _ = live_ticker(sym)
        if lp:
            cls = "pos" if (lc or 0)>=0 else "neg"
            cells += (f'<div class="qs-cell"><div class="l">{name}/USDT</div>'
                      f'<div class="v">${lp:,.2f}</div>'
                      f'<div class="d {cls}">{"▲" if (lc or 0)>=0 else "▼"} {abs(lc or 0):.2f}%</div></div>')

    st.markdown(f"""
<div class="home-wrap">
<h1 class="home-title">Welcome to <em>LUMA</em></h1>
<p class="home-sub">Choose a tool below to begin your analysis.</p>
<div class="qs-bar">{cells}</div>
<div class="card-grid">
""", unsafe_allow_html=True)

    # Cards — each is a real clickable Streamlit button overlaid
    cards = [
        ("forecast", "📊", "Live Forecast",
         "Select any coin and timeframes. LUMA generates a real-time candlestick chart with AI prediction lines overlaid.",
         "live", "LIVE"),
        ("upload", "📤", "Upload Chart Analysis",
         "Drag & drop or upload your own chart screenshots. LUMA analyzes patterns, signals, and gives you a read.",
         "ai", "AI ANALYSIS"),
        ("chat", "💬", "Ask LUMA",
         "Direct conversation with LUMA. Ask anything about crypto, technicals, market structure, or your open positions.",
         "ai", "AI ANALYST"),
        ("forecast", "🔍", "Multi-TF Scanner",
         "Run forecasts across 1m through 1D simultaneously. See where all timeframes align for high-confidence setups.",
         "new", "NEW"),
    ]

    card_cols = st.columns(4)
    for i, (page, icon, title, desc, tag_cls, tag_txt) in enumerate(cards):
        with card_cols[i]:
            st.markdown(f"""
<div class="feat-card">
  <div class="card-icon">{icon}</div>
  <div class="card-title">{title}</div>
  <div class="card-desc">{desc}</div>
  <span class="card-tag {tag_cls}">{tag_txt}</span>
</div>
""", unsafe_allow_html=True)
            if st.button(f"Open {title}", key=f"card_{i}", use_container_width=True):
                st.session_state.sub = page
                st.rerun()

    st.markdown("</div></div>", unsafe_allow_html=True)

    # Style the card buttons to be invisible (the card HTML is the visual)
    st.markdown("""
<style>
/* make card open buttons blend into cards */
div[data-testid="stHorizontalBlock"] > div .stButton > button {
  background:transparent!important;color:#a78bfa!important;
  border:none!important;border-top:1px solid #1e293b!important;
  border-radius:0!important;padding:8px!important;
  font-size:.78rem!important;font-weight:700!important;
  letter-spacing:.06em;margin-top:-4px;position:static!important;
  text-transform:uppercase;
}
div[data-testid="stHorizontalBlock"] > div .stButton > button:hover {
  background:rgba(167,139,250,.08)!important;color:#c4b5fd!important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  SUB-PAGE: FORECAST  (main chart + prediction)
# ══════════════════════════════════════════════════════════════════════
DASH_CSS = """
<style>
.tkbar{background:#0a0d1c;border-bottom:1px solid #111827;padding:12px 22px;
  display:flex;align-items:center;flex-wrap:wrap;gap:20px}
.tksym{font-size:1.5rem;font-weight:700;color:#f1f5f9;
  font-family:'IBM Plex Mono',monospace!important;display:flex;align-items:center;gap:9px}
.tkbadge{background:#1e3a5f;color:#38bdf8;font-size:.6rem;font-weight:700;
  padding:3px 8px;border-radius:3px;letter-spacing:.08em}
.tkprice{font-family:'IBM Plex Mono',monospace!important;font-size:1.85rem;font-weight:400;color:#f1f5f9}
.pos{color:#34d399} .neg{color:#f87171}
.tkstat .l{color:#374151;font-size:.64rem;text-transform:uppercase;letter-spacing:.07em}
.tkstat .v{color:#94a3b8;font-size:.78rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}
.igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:5px;margin:10px 0;overflow:hidden}
.icell{background:#0a0d1c;padding:9px 14px}
.icell .l{color:#374151;font-size:.63rem;text-transform:uppercase;letter-spacing:.07em}
.icell .v{color:#cbd5e1;font-size:.82rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}
.gbadge{display:inline-block;background:#0a2214;border:2px solid #34d399;
  color:#34d399;font-size:.95rem;font-weight:700;padding:9px 20px;border-radius:4px;
  letter-spacing:.04em;margin:10px 0;font-family:'IBM Plex Mono',monospace!important}
.sh{color:#38bdf8;font-size:.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.13em;border-bottom:1px solid #111827;padding-bottom:5px;margin:18px 0 10px}
.chwrap{background:#0a0d1c;border:1px solid #111827;border-radius:5px;padding:3px;overflow:hidden}
.chat-wrap{background:#0a0d1c;border:1px solid #111827;border-radius:6px;
  padding:16px;max-height:380px;overflow-y:auto;margin-bottom:10px}
.msg-luma{background:#0d1f0d;border:1px solid #1a3a1a;border-radius:6px;
  padding:12px 16px;margin-bottom:10px;color:#a7f3d0;font-size:.86rem;line-height:1.72}
.msg-user{background:#1a1a3a;border:1px solid #2d2d5a;border-radius:6px;
  padding:10px 14px;margin-bottom:10px;color:#c4b5fd;font-size:.84rem;
  text-align:right;line-height:1.6}
.lbl-l{color:#34d399;font-size:.65rem;font-weight:700;letter-spacing:.08em;margin-bottom:5px}
.lbl-u{color:#7c3aed;font-size:.65rem;font-weight:700;letter-spacing:.08em;margin-bottom:5px;text-align:right}
</style>
"""

def sub_forecast():
    st.markdown(DASH_CSS, unsafe_allow_html=True)

    # ── controls row ───────────────────────────────────────────────
    c1,c2,c3,c4,c5,c6 = st.columns([2,2,1,1,1.5,1])
    with c1:
        coin_choice = st.selectbox("Coin", list(POPULAR_COINS.keys()),
                                   label_visibility="visible")
        symbol = (st.text_input("Symbol","BTCUSDT",label_visibility="collapsed").upper().strip()
                  if POPULAR_COINS[coin_choice]=="__custom__"
                  else POPULAR_COINS[coin_choice])
    with c2:
        selected_tfs = st.multiselect("Timeframes", list(INTERVAL_MINUTES.keys()),
                                      default=["15m","1h","4h"])
    with c3:
        lookback_days = st.slider("Lookback (days)", 7, 365, 90, step=7)
    with c4:
        forecast_days = st.slider("Forecast (days)", 1, 30, 7)
    with c5:
        hf_key = st.text_input("HuggingFace API Key", type="password",
                               placeholder="hf_xxx… (for AI analysis)",
                               label_visibility="visible")
    with c6:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_btn = st.button("⊞ Run LUMA", type="primary", use_container_width=True)

    # ── ticker bar ─────────────────────────────────────────────────
    lp, lc, lv = live_ticker(symbol)
    ps = f"${lp:,.2f}" if lp else "—"
    cs = f"{'▲' if (lc or 0)>=0 else '▼'} {abs(lc or 0):.2f}%" if lc is not None else "—"
    cc = "pos" if (lc or 0)>=0 else "neg"
    vs = f"${lv/1e9:.2f}B" if lv else "—"

    st.markdown(f"""
<div class="tkbar">
  <div class="tksym">{symbol[:3]}<span class="tkbadge">CRYPTO</span></div>
  <div class="tkprice">{ps}</div>
  <div class="{cc}" style="font-size:1rem;font-family:'IBM Plex Mono',monospace">{cs}</div>
  <div class="tkstat"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
  <div class="tkstat"><div class="l">Exchange</div><div class="v">Binance.US</div></div>
  <div style="margin-left:auto">
    <div class="tkstat"><div class="l">Updated</div>
    <div class="v">{datetime.now().strftime('%b %d %H:%M:%S')}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not run_btn and not st.session_state.summaries:
        st.markdown("""
<div style="text-align:center;padding:100px 0;color:#111827">
  <div style="font-size:3.5rem">📊</div>
  <div style="font-size:.9rem;margin-top:14px;color:#1e293b">
    Configure settings above and click <b>Run LUMA</b>
  </div>
</div>""", unsafe_allow_html=True)
        return

    if run_btn:
        if not selected_tfs:
            st.warning("Select at least one timeframe."); return

        with st.spinner("Validating symbol…"):
            if not validate_symbol(symbol):
                st.error(f"**{symbol}** not found on Binance.US — use USDT pairs like BTCUSDT"); return
            luma_model = load_model()

        COLORS = ["#a78bfa","#38bdf8","#fb923c","#34d399","#f472b6","#facc15"]
        fig = go.Figure()
        fcast_dfs, summaries, raw_dfs = {}, {}, {}
        prim = selected_tfs[0]
        prog = st.progress(0)

        for i, tf in enumerate(selected_tfs):
            prog.progress(i/len(selected_tfs), text=f"Processing {tf}…")
            col_c = COLORS[i%len(COLORS)]
            eff   = min(lookback_days, INTERVAL_MAX_DAYS[tf])
            try: df = fetch_binance(symbol, tf, eff)
            except Exception as e: st.warning(f"⚠️ {tf}: {e}"); continue
            if len(df) < 30: continue

            raw_dfs[tf]   = df
            prices, dates = df["Close"].values, df.index
            mins          = INTERVAL_MINUTES[tf]
            horizon       = min(max(1, int(forecast_days*1440/mins)), 256)
            pt, _         = luma_model.forecast(horizon=horizon, inputs=[prices[-1024:]])
            fc            = pt[0]
            td            = pd.Timedelta(minutes=mins)
            fi            = pd.date_range(start=dates[-1]+td, periods=len(fc),
                                          freq=td, tz=dates.tzinfo)

            fcast_dfs[tf] = pd.DataFrame({"Datetime":fi,"Forecast":fc.round(6)})
            summaries[tf] = {"last":float(prices[-1]),"end":float(fc[-1]),"bars":len(fc)}

            sn = min(300, len(df))
            if tf == prim:
                fig.add_trace(go.Candlestick(
                    x=dates[-sn:], open=df["Open"].iloc[-sn:], high=df["High"].iloc[-sn:],
                    low=df["Low"].iloc[-sn:],  close=df["Close"].iloc[-sn:], name=f"Price ({tf})",
                    increasing_line_color="#34d399", decreasing_line_color="#f87171",
                    increasing_fillcolor="rgba(52,211,153,.14)",
                    decreasing_fillcolor="rgba(248,113,113,.14)"))
            else:
                fig.add_trace(go.Scatter(x=dates[-sn:],y=prices[-sn:],mode="lines",
                    name=f"Price ({tf})",line=dict(color=col_c,width=1,dash="dot"),opacity=.4))

            r2,g2,b2 = int(col_c[1:3],16),int(col_c[3:5],16),int(col_c[5:7],16)
            fig.add_trace(go.Scatter(
                x=list(fi)+list(fi[::-1]),y=list(fc*1.012)+list(fc[::-1]*0.988),
                fill="toself",fillcolor=f"rgba({r2},{g2},{b2},.06)",
                line=dict(color="rgba(0,0,0,0)"),showlegend=False,hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=fi,y=fc,mode="lines+markers",name=f"LUMA Forecast ({tf})",
                line=dict(color=col_c,width=2.5,dash="dash"),
                marker=dict(size=5,symbol="diamond"),
                hovertemplate="<b>%{x|%b %d %H:%M}</b><br>$%{y:,.4f}<extra></extra>"))

        prog.progress(1.0,"Done!"); time.sleep(.2); prog.empty()

        # save
        st.session_state.summaries  = summaries
        st.session_state.symbol     = symbol
        st.session_state.fcast_dfs  = fcast_dfs
        st.session_state.raw_dfs    = raw_dfs
        st.session_state.chat_history = []
        st.session_state.initial_analysis = ""

        fig.update_layout(
            paper_bgcolor="#0a0d1c", plot_bgcolor="#0a0d1c",
            font=dict(color="#94a3b8",family="IBM Plex Mono"),
            title=dict(text=f"🌙 LUMA · <b>{symbol}</b>  —  Multi-TF Forecast",
                       font=dict(color="#f1f5f9",size=14),x=0.01),
            xaxis=dict(gridcolor="#0e1325",linecolor="#111827",
                       rangeslider=dict(visible=True,bgcolor="#07090f",thickness=.04)),
            yaxis=dict(gridcolor="#0e1325",linecolor="#111827"),
            legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1,
                        bgcolor="rgba(0,0,0,0)",font=dict(size=10)),
            hovermode="x unified",height=520,margin=dict(l=28,r=28,t=65,b=28))

        st.markdown('<div class="chwrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # stats
        summaries = st.session_state.summaries
        best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/summaries[x]["last"]))
        bpct = (summaries[best]["end"]-summaries[best]["last"])/summaries[best]["last"]*100
        cells = ""
        for tf2, s in summaries.items():
            p2=((s["end"]-s["last"])/s["last"]*100); cc2="#34d399" if p2>=0 else "#f87171"
            cells += (f'<div class="icell"><div class="l">LUMA {tf2}</div>'
                      f'<div class="v" style="color:{cc2}">{"▲" if p2>=0 else "▼"} {abs(p2):.2f}%</div></div>'
                      f'<div class="icell"><div class="l">Forecast End</div>'
                      f'<div class="v">${s["end"]:,.4f}</div></div>')
        st.markdown(f"""
<div class="gbadge">{symbol[:3]} &nbsp; {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp;({best} forecast)</div>
<div class="igrid">{cells}</div>""", unsafe_allow_html=True)

        # downloads
        st.markdown('<div class="sh">⬇️ Download Data</div>', unsafe_allow_html=True)
        raw_dfs = st.session_state.raw_dfs
        dl_cols = st.columns(max(1, len(raw_dfs)) + 1)
        for idx, (tf3, df_r) in enumerate(raw_dfs.items()):
            with dl_cols[idx]:
                st.download_button(f"OHLC {tf3}",
                    data=df_r.reset_index().to_csv(index=False),
                    file_name=f"luma_{symbol}_{tf3}_ohlc.csv",
                    mime="text/csv", use_container_width=True)
        with dl_cols[-1]:
            st.download_button("Forecasts CSV",
                data=pd.concat([d.assign(TF=t) for t,d in st.session_state.fcast_dfs.items()]).to_csv(index=False),
                file_name=f"luma_{symbol}_forecasts.csv",
                mime="text/csv", use_container_width=True)

        # AI analysis
        if hf_key and summaries:
            st.markdown('<div class="sh">🌙 LUMA Analysis</div>', unsafe_allow_html=True)
            with st.spinner("LUMA is reading the charts…"):
                analysis = do_analysis(hf_key, symbol, summaries, raw_dfs)
                st.session_state.initial_analysis = analysis

    # ── show chart + AI if we have saved state ──────────────────────
    if st.session_state.summaries and not run_btn:
        sym = st.session_state.symbol
        summaries = st.session_state.summaries

        best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/summaries[x]["last"]))
        bpct = (summaries[best]["end"]-summaries[best]["last"])/summaries[best]["last"]*100
        cells = ""
        for tf2, s in summaries.items():
            p2=((s["end"]-s["last"])/s["last"]*100); cc2="#34d399" if p2>=0 else "#f87171"
            cells += (f'<div class="icell"><div class="l">LUMA {tf2}</div>'
                      f'<div class="v" style="color:{cc2}">{"▲" if p2>=0 else "▼"} {abs(p2):.2f}%</div></div>'
                      f'<div class="icell"><div class="l">Forecast End</div>'
                      f'<div class="v">${s["end"]:,.4f}</div></div>')
        st.markdown(f"""
<div class="gbadge">{sym[:3]} &nbsp; {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp;({best} forecast)</div>
<div class="igrid">{cells}</div>
<p style="color:#334155;font-size:.8rem;margin-top:4px">↑ Previous forecast results — click Run LUMA to refresh</p>
""", unsafe_allow_html=True)

    # ── LUMA AI Chat ────────────────────────────────────────────────
    if st.session_state.summaries:
        _hf = hf_key if hf_key else ""
        if _hf or st.session_state.initial_analysis:
            st.markdown('<div class="sh">🌙 LUMA AI Analyst</div>', unsafe_allow_html=True)

            chat_html = ""
            if st.session_state.initial_analysis:
                chat_html += (f'<div class="lbl-l">🌙 LUMA</div>'
                              f'<div class="msg-luma">{st.session_state.initial_analysis.replace(chr(10),"<br>")}</div>')
            for h in st.session_state.chat_history:
                chat_html += (f'<div class="lbl-u">YOU</div><div class="msg-user">{h["user"]}</div>'
                              f'<div class="lbl-l">🌙 LUMA</div>'
                              f'<div class="msg-luma">{h["luma"].replace(chr(10),"<br>")}</div>')

            if chat_html:
                st.markdown(f'<div class="chat-wrap">{chat_html}</div>', unsafe_allow_html=True)

            qc, bc = st.columns([5,1])
            with qc:
                user_q = st.text_input("Ask LUMA…",
                    placeholder="e.g. Where's support? Is this a bull trap? What's your BTC target?",
                    label_visibility="collapsed", key="forecast_chat")
            with bc:
                if st.button("Ask →", key="ask_fc", use_container_width=True):
                    if user_q.strip() and _hf:
                        with st.spinner("LUMA…"):
                            reply = do_chat(_hf, st.session_state.symbol,
                                           st.session_state.summaries,
                                           st.session_state.raw_dfs,
                                           user_q, st.session_state.chat_history)
                            st.session_state.chat_history.append({"user":user_q,"luma":reply})
                            st.rerun()
                    elif not _hf:
                        st.warning("Add HuggingFace key above to chat with LUMA.")
        else:
            st.info("🌙 Enter your HuggingFace API key above to unlock LUMA AI analysis and chat.")


# ══════════════════════════════════════════════════════════════════════
#  SUB-PAGE: UPLOAD
# ══════════════════════════════════════════════════════════════════════
def sub_upload():
    st.markdown(DASH_CSS + """
<style>
.drop-zone{
  border:2px dashed #1e3a5f;border-radius:12px;
  background:#0a0d1c;padding:48px 32px;text-align:center;
  transition:all .2s;margin-bottom:20px
}
.drop-zone:hover{border-color:#a78bfa;background:#0d0f22}
.drop-icon{font-size:3rem;margin-bottom:12px}
.drop-title{color:#f1f5f9;font-size:1.1rem;font-weight:600;margin-bottom:6px}
.drop-sub{color:#4a5568;font-size:.82rem;line-height:1.6}
.file-card{background:#0d1225;border:1px solid #111827;border-radius:8px;
  padding:14px 18px;margin-bottom:10px;display:flex;align-items:center;gap:14px}
.file-icon{font-size:1.8rem}
.file-name{color:#94a3b8;font-size:.88rem;font-family:'IBM Plex Mono',monospace!important}
.file-size{color:#374151;font-size:.74rem;margin-top:2px}
</style>
""", unsafe_allow_html=True)

    st.markdown('<div class="sh">📤 Upload Chart Analysis</div>', unsafe_allow_html=True)

    hf_key = st.text_input("HuggingFace API Key (required for LUMA analysis)",
                           type="password", placeholder="hf_xxx…",
                           key="upload_hf")

    st.markdown("""
<div class="drop-zone">
  <div class="drop-icon">📁</div>
  <div class="drop-title">Drop your chart screenshots here</div>
  <div class="drop-sub">PNG, JPG, JPEG, GIF, WEBP supported<br>
  Upload TradingView screenshots, your own charts, or any market image</div>
</div>
""", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Add Files",
        type=["png","jpg","jpeg","gif","webp"],
        accept_multiple_files=True,
        label_visibility="visible",
        key="upload_files"
    )

    if uploaded:
        st.session_state.uploaded_files = uploaded
        st.markdown('<div class="sh">📋 Uploaded Files</div>', unsafe_allow_html=True)

        for uf in uploaded:
            size_kb = len(uf.getvalue()) / 1024
            st.markdown(f"""
<div class="file-card">
  <div class="file-icon">🖼️</div>
  <div>
    <div class="file-name">{uf.name}</div>
    <div class="file-size">{size_kb:.1f} KB</div>
  </div>
</div>""", unsafe_allow_html=True)

        st.markdown('<div class="sh">📊 Chart Viewer</div>', unsafe_allow_html=True)
        view_cols = st.columns(min(len(uploaded), 2))
        for i, uf in enumerate(uploaded):
            with view_cols[i % 2]:
                st.image(uf, use_container_width=True, caption=uf.name)

                if hf_key:
                    note = st.text_input(f"Add context for {uf.name}",
                                        placeholder="e.g. BTC 4H chart, looking for breakout…",
                                        key=f"note_{i}")
                    if st.button(f"🌙 Analyze with LUMA", key=f"analyze_{i}",
                                 use_container_width=True):
                        with st.spinner(f"LUMA analyzing {uf.name}…"):
                            result = analyze_uploaded_chart(hf_key, uf.name, note)
                        st.markdown(f"""
<div style="background:#0d1f0d;border:1px solid #1a3a1a;border-radius:6px;
  padding:16px 20px;color:#a7f3d0;font-size:.86rem;line-height:1.75;margin-top:8px">
  <div style="color:#34d399;font-size:.65rem;font-weight:700;letter-spacing:.08em;margin-bottom:8px">🌙 LUMA ANALYSIS — {uf.name.upper()}</div>
  {result.replace(chr(10),"<br>")}
</div>""", unsafe_allow_html=True)
                else:
                    st.info("Add HuggingFace key above to get LUMA analysis of your chart.")
    else:
        if st.session_state.uploaded_files:
            st.markdown('<div class="sh">Previously Uploaded</div>', unsafe_allow_html=True)
            for uf in st.session_state.uploaded_files:
                st.image(uf, use_container_width=False, width=300, caption=uf.name)


# ══════════════════════════════════════════════════════════════════════
#  SUB-PAGE: CHAT
# ══════════════════════════════════════════════════════════════════════
def sub_chat():
    st.markdown(DASH_CSS, unsafe_allow_html=True)
    st.markdown('<div class="sh">💬 Ask LUMA — Direct Analyst Chat</div>', unsafe_allow_html=True)

    hf_key = st.text_input("HuggingFace API Key",
                           type="password", placeholder="hf_xxx…",
                           key="chat_hf", label_visibility="visible")

    ctx_note = ""
    if st.session_state.summaries:
        sym  = st.session_state.symbol
        tfs  = list(st.session_state.summaries.keys())
        ctx_note = f"📊 LUMA has live forecast data for **{sym}** across {', '.join(tfs)} — LUMA will reference it automatically."
        st.success(ctx_note)
    else:
        st.info("💡 Run a forecast on the **Forecast** tab first — LUMA will use that live data in chat. Or just ask general crypto questions.")

    # Chat display
    st.markdown('<div class="chat-wrap" id="chat-bottom">', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.markdown("""
<div style="text-align:center;padding:40px 0;color:#1e293b">
  <div style="font-size:2.5rem">🌙</div>
  <div style="font-size:.88rem;margin-top:10px;color:#334155">
    Ask LUMA anything about crypto, technicals, or your forecast data
  </div>
  <div style="margin-top:16px;display:flex;flex-wrap:wrap;justify-content:center;gap:8px">
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;
      font-size:.76rem;padding:6px 12px;border-radius:4px">Where is BTC support?</span>
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;
      font-size:.76rem;padding:6px 12px;border-radius:4px">Is this a bull or bear market?</span>
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;
      font-size:.76rem;padding:6px 12px;border-radius:4px">What timeframe is most reliable?</span>
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;
      font-size:.76rem;padding:6px 12px;border-radius:4px">Explain the LUMA forecast</span>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        for h in st.session_state.chat_history:
            st.markdown(
                f'<div class="lbl-u">YOU</div><div class="msg-user">{h["user"]}</div>'
                f'<div class="lbl-l">🌙 LUMA</div>'
                f'<div class="msg-luma">{h["luma"].replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    qc, bc, cc = st.columns([5, 1, 1])
    with qc:
        user_q = st.text_input("Message",
            placeholder="Ask LUMA anything about crypto, markets, or your forecast…",
            label_visibility="collapsed", key="direct_chat")
    with bc:
        if st.button("Send →", key="send_chat", use_container_width=True):
            if user_q.strip() and hf_key:
                with st.spinner("LUMA…"):
                    reply = do_chat(hf_key,
                                   st.session_state.get("symbol","BTC"),
                                   st.session_state.summaries,
                                   st.session_state.raw_dfs,
                                   user_q, st.session_state.chat_history)
                    st.session_state.chat_history.append({"user":user_q,"luma":reply})
                    st.rerun()
            elif not hf_key:
                st.warning("Add HuggingFace key above.")
    with cc:
        if st.button("Clear", key="clear_chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  SUB-PAGE: SETTINGS
# ══════════════════════════════════════════════════════════════════════
def sub_settings():
    st.markdown(DASH_CSS, unsafe_allow_html=True)
    st.markdown('<div class="sh">⚙️ Settings & Help</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
<div style="background:#0d1225;border:1px solid #111827;border-radius:8px;padding:22px 24px;margin-bottom:16px">
  <div style="color:#a78bfa;font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">🔑 API Keys</div>
  <p style="color:#64748b;font-size:.84rem;line-height:1.7">
    LUMA uses <b style="color:#94a3b8">HuggingFace Inference API</b> for AI analysis and chat.<br><br>
    Get a free key at <b style="color:#38bdf8">huggingface.co/settings/tokens</b><br><br>
    Enter it in the HuggingFace Key field on the Forecast or Upload tabs.
    It is never stored permanently.
  </p>
</div>
<div style="background:#0d1225;border:1px solid #111827;border-radius:8px;padding:22px 24px">
  <div style="color:#a78bfa;font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">📡 Data Source</div>
  <p style="color:#64748b;font-size:.84rem;line-height:1.7">
    All market data is fetched live from <b style="color:#94a3b8">Binance.US</b> — 
    the US-compliant exchange API. No API key required for market data.<br><br>
    Supports: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, ADAUSDT, DOGEUSDT, AVAXUSDT and more.
  </p>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown("""
<div style="background:#0d1225;border:1px solid #111827;border-radius:8px;padding:22px 24px;margin-bottom:16px">
  <div style="color:#a78bfa;font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">⏱ Timeframe Guide</div>
  <table style="width:100%;color:#64748b;font-size:.82rem;border-collapse:collapse">
    <tr style="color:#94a3b8;border-bottom:1px solid #1e293b">
      <th style="text-align:left;padding:6px 0">TF</th>
      <th style="text-align:left;padding:6px 0">Use Case</th>
      <th style="text-align:left;padding:6px 0">Max Lookback</th>
    </tr>
    <tr><td style="padding:5px 0">1m / 5m</td><td>Scalping</td><td>3 / 45 days</td></tr>
    <tr><td style="padding:5px 0">15m / 30m</td><td>Swing entries</td><td>90 / 180 days</td></tr>
    <tr><td style="padding:5px 0">1h / 4h</td><td>Trend trading</td><td>1yr / 2yr</td></tr>
    <tr><td style="padding:5px 0">1d</td><td>Macro view</td><td>5+ years</td></tr>
  </table>
</div>
<div style="background:#0d1225;border:1px solid #111827;border-radius:8px;padding:22px 24px">
  <div style="color:#a78bfa;font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:12px">🌙 Access Key</div>
  <p style="color:#64748b;font-size:.84rem;line-height:1.7">
    Your current access key is <b style="color:#a78bfa;font-family:'IBM Plex Mono',monospace">953</b>.<br><br>
    To change it, open <code style="color:#94a3b8">luma_crypto_forecast.py</code> and edit line:<br>
    <code style="color:#34d399;font-size:.8rem">PASSWORD = "953"</code><br><br>
    The cryptic hint <code style="color:#6366f1">Ω · √(NQ∞) · Δτ</code> is shown on the login screen.
  </p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD  (shell + sub-router)
# ══════════════════════════════════════════════════════════════════════
def page_dashboard():
    dash_shell()
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    sub = st.session_state.sub
    if   sub == "home":     sub_home()
    elif sub == "forecast": sub_forecast()
    elif sub == "upload":   sub_upload()
    elif sub == "chat":     sub_chat()
    elif sub == "settings": sub_settings()
    else:                   sub_home()


# ══════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════
p = st.session_state.page
if   p == "landing":    page_landing()
elif p == "login":      page_login()
elif p == "dashboard":  page_dashboard()
else:                   page_landing()

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
import time
import base64
import os
import io

# ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LUMA", page_icon="🌙", layout="wide",
                   initial_sidebar_state="collapsed")

PASSWORD = "953"

DEFAULTS = {
    "page": "landing", "auth_err": False, "uploaded": [],
    "chat_history": [], "summaries": {}, "symbol": "BTCUSDT",
    "fcast_dfs": {}, "raw_dfs": {}
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ──────────────────────────────────────────────────────────────────────
#  LOGO LOADER  — tries several locations so it always works
# ──────────────────────────────────────────────────────────────────────
def load_logo_b64():
    candidates = ["logo.jpg","logo.png","./logo.jpg","./logo.png",
                  os.path.join(os.path.dirname(__file__),"logo.jpg"),
                  os.path.join(os.path.dirname(__file__),"logo.png")]
    for p in candidates:
        try:
            if os.path.isfile(p):
                with open(p,"rb") as f:
                    ext  = p.rsplit(".",1)[-1].lower()
                    mime = "jpeg" if ext in ("jpg","jpeg") else "png"
                    return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
        except: pass
    return ""

LOGO_URI = load_logo_b64()

# ──────────────────────────────────────────────────────────────────────
#  DATA
# ──────────────────────────────────────────────────────────────────────
INTERVAL_MINUTES  = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440}
INTERVAL_MAX_DAYS = {"1m":3,"5m":45,"15m":90,"30m":180,"1h":365,"4h":730,"1d":2000}
POPULAR_COINS = {
    "Bitcoin (BTC)":"BTCUSDT","Ethereum (ETH)":"ETHUSDT",
    "Solana (SOL)":"SOLUSDT","XRP":"XRPUSDT","BNB":"BNBUSDT",
    "Cardano (ADA)":"ADAUSDT","Dogecoin (DOGE)":"DOGEUSDT","Custom…":"__custom__",
}

BINANCE_BASE = "https://api.binance.us"   # US-friendly endpoint

@st.cache_data(ttl=300, show_spinner=False)
def fetch_binance(symbol, interval, days_back):
    url  = f"{BINANCE_BASE}/api/v3/klines"
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
        rows = data + rows
        end_ms = int(data[0][0])-1
        if len(data) < lim: break
    if not rows: raise ValueError(f"No data for {symbol}")
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","vol",
                                      "cts","qvol","tr","bb","bq","ign"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.sort_values("ts").drop_duplicates("ts").set_index("ts")
    return df[["open","high","low","close","vol"]].astype(float).rename(
        columns={"open":"Open","high":"High","low":"Low","close":"Close","vol":"Volume"})

def validate_symbol(symbol):
    try:
        r = requests.get(f"{BINANCE_BASE}/api/v3/ticker/price",
                         params={"symbol":symbol}, timeout=5)
        return r.status_code==200 and "price" in r.json()
    except: return False

def get_live_ticker(symbol):
    try:
        d = requests.get(f"{BINANCE_BASE}/api/v3/ticker/24hr",
                         params={"symbol":symbol}, timeout=5).json()
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

# ──────────────────────────────────────────────────────────────────────
#  LUMA AI ANALYST  — no external AI brand names exposed to user
# ──────────────────────────────────────────────────────────────────────
LUMA_PERSONA = """You are LUMA, an elite AI crypto market analyst with a sharp, confident personality.
You speak directly and precisely — like a seasoned prop trader who has seen every market cycle.
You give actionable insights, not generic advice. You reference specific price levels, 
timeframe confluence, momentum shifts, and risk factors. You are not a financial advisor 
but you speak with authority and specificity. Never mention any AI model names, companies, 
or frameworks. You ARE LUMA. Keep responses under 200 words unless specifically asked for more.
Always reference the actual data provided when answering."""

def luma_ai_call(hf_key: str, messages: list) -> str:
    try:
        r = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3/v1/chat/completions",
            headers={"Authorization": f"Bearer {hf_key}", "Content-Type": "application/json"},
            json={
                "model": "mistralai/Mistral-7B-Instruct-v0.3",
                "messages": [{"role":"system","content":LUMA_PERSONA}] + messages,
                "max_tokens": 400,
                "temperature": 0.65,
            }, timeout=45)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ LUMA offline: {e}"

def build_market_context(symbol, summaries, raw_dfs):
    """Build a rich context string for LUMA to reference."""
    lines = [f"CURRENT MARKET DATA FOR {symbol}:\n"]
    for tf, s in summaries.items():
        pct = (s["end"]-s["last"])/s["last"]*100
        lines.append(f"• {tf}: Current=${s['last']:.4f} | LUMA Forecast=${s['end']:.4f} | "
                     f"{'▲' if pct>=0 else '▼'}{abs(pct):.2f}% projected move | {s['bars']} bar horizon")
        if tf in raw_dfs:
            df = raw_dfs[tf]
            if len(df) >= 20:
                recent = df["Close"].tail(20)
                lines.append(f"  Last 20 closes: high=${recent.max():.4f}, low=${recent.min():.4f}, "
                             f"avg=${recent.mean():.4f}")
    return "\n".join(lines)

def initial_analysis(hf_key, symbol, summaries, raw_dfs):
    ctx = build_market_context(symbol, summaries, raw_dfs)
    prompt = (f"{ctx}\n\nProvide your initial LUMA analysis: trend direction, key support/resistance, "
              f"multi-timeframe confluence, the highest-conviction forecast, and one key risk. "
              f"Be specific with price levels.")
    return luma_ai_call(hf_key, [{"role":"user","content":prompt}])

def chat_response(hf_key, symbol, summaries, raw_dfs, question, history):
    ctx = build_market_context(symbol, summaries, raw_dfs)
    messages = [{"role":"user","content":f"Market context:\n{ctx}\n\nRemember this data for our conversation."},
                {"role":"assistant","content":"Understood. I have the full market context loaded. What's your question?"}]
    for h in history[-6:]:   # last 3 turns
        messages.append({"role":"user",      "content": h["user"]})
        messages.append({"role":"assistant", "content": h["luma"]})
    messages.append({"role":"user","content": question})
    return luma_ai_call(hf_key, messages)


# ══════════════════════════════════════════════════════════════════════
#  PAGE 1 — LANDING
# ══════════════════════════════════════════════════════════════════════
def page_landing():
    logo_html = (f'<img src="{LOGO_URI}" style="height:48px;width:auto;display:block" />'
                 if LOGO_URI else
                 '<span style="font-family:Georgia,serif;font-size:2.2rem;font-weight:300;'
                 'color:#f1f5f9;letter-spacing:.06em">🌙 LUMA</span>')

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;1,300&family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400&display=swap');
*,html,body,[class*="css"]{{font-family:'Syne',sans-serif!important}}
.stApp{{background:#000!important;overflow-x:hidden}}
header[data-testid="stHeader"],#MainMenu,footer{{display:none!important}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}

.hero{{position:relative;width:100vw;min-height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.hbg{{position:absolute;inset:0;z-index:0;
  background:radial-gradient(ellipse 130% 90% at 65% 40%,#0a1628 0%,#040810 50%,#000 100%)}}
.hgrid{{position:absolute;inset:0;z-index:1;opacity:.12;
  background-image:linear-gradient(rgba(120,160,255,.4) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(120,160,255,.4) 1px,transparent 1px);
  background-size:70px 70px;animation:gs 24s linear infinite}}
@keyframes gs{{to{{background-position:70px 70px}}}}
.hcandles{{position:absolute;right:4%;top:8%;width:46%;height:84%;z-index:2;opacity:.15;
  filter:blur(2px);
  background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 500 400'%3E%3Crect x='10' y='230' width='18' height='110' fill='%23f87171'/%3E%3Crect x='18' y='210' width='2' height='150' fill='%23f87171'/%3E%3Crect x='44' y='190' width='18' height='120' fill='%23f87171'/%3E%3Crect x='52' y='165' width='2' height='170' fill='%23f87171'/%3E%3Crect x='78' y='155' width='18' height='100' fill='%2334d399'/%3E%3Crect x='86' y='132' width='2' height='145' fill='%2334d399'/%3E%3Crect x='112' y='112' width='18' height='120' fill='%2334d399'/%3E%3Crect x='120' y='88' width='2' height='165' fill='%2334d399'/%3E%3Crect x='146' y='72' width='18' height='100' fill='%2334d399'/%3E%3Crect x='154' y='48' width='2' height='145' fill='%2334d399'/%3E%3Crect x='180' y='48' width='18' height='120' fill='%23f87171'/%3E%3Crect x='188' y='22' width='2' height='170' fill='%23f87171'/%3E%3Crect x='214' y='28' width='18' height='78' fill='%2334d399'/%3E%3Crect x='222' y='12' width='2' height='110' fill='%2334d399'/%3E%3Crect x='248' y='12' width='18' height='55' fill='%2334d399'/%3E%3Crect x='256' y='4' width='2' height='75' fill='%2334d399'/%3E%3C/svg%3E") no-repeat center/contain}}

.nav{{position:relative;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:28px 64px}}
.navlinks{{display:flex;gap:36px}}
.navlinks a{{color:#4a5568;text-decoration:none;font-size:.8rem;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;transition:color .2s}}
.navlinks a:hover{{color:#e2e8f0}}

.hbody{{position:relative;z-index:10;flex:1;display:flex;flex-direction:column;
  justify-content:flex-end;padding:0 64px 96px 64px}}
.eyebrow{{color:#a78bfa;font-size:.74rem;font-weight:700;letter-spacing:.22em;
  text-transform:uppercase;margin-bottom:16px}}
.htitle{{font-family:'Cormorant Garamond',serif!important;
  font-size:clamp(4rem,8vw,7.5rem);font-weight:300;line-height:1.02;
  color:#f1f5f9;margin:0 0 20px 0}}
.htitle em{{font-style:italic;color:#a78bfa}}
.hsub{{color:#64748b;font-size:1rem;font-weight:400;max-width:500px;
  line-height:1.68;margin-bottom:48px}}

.strip{{position:relative;z-index:10;background:rgba(255,255,255,.03);
  border-top:1px solid rgba(255,255,255,.06);padding:12px 64px;
  display:flex;gap:44px;align-items:center}}
.si{{display:flex;align-items:center;gap:8px;white-space:nowrap}}
.si .sym{{color:#334155;font-size:.7rem;font-weight:700;letter-spacing:.09em}}
.si .px{{color:#64748b;font-size:.78rem;font-family:'JetBrains Mono',monospace!important}}
.si .up{{color:#34d399;font-size:.7rem}}
.si .dn{{color:#f87171;font-size:.7rem}}

/* launch button */
.stButton>button{{
  display:inline-flex!important;align-items:center;gap:10px;
  border:1px solid rgba(255,255,255,.2)!important;
  background:rgba(15,20,40,.6)!important;backdrop-filter:blur(12px);
  color:#e2e8f0!important;padding:15px 44px!important;border-radius:3px!important;
  font-size:.84rem!important;font-weight:700!important;letter-spacing:.1em;
  text-transform:uppercase;
  position:fixed;bottom:92px;left:64px;z-index:200;transition:all .25s;
  box-shadow:0 0 0 0 rgba(167,139,250,0)
}}
.stButton>button:hover{{
  background:rgba(100,60,200,.35)!important;
  border-color:#a78bfa!important;color:#c4b5fd!important;
  box-shadow:0 0 28px rgba(167,139,250,.25)!important
}}
</style>

<div class="hero">
  <div class="hbg"></div>
  <div class="hgrid"></div>
  <div class="hcandles"></div>
  <nav class="nav">
    <div style="display:flex;align-items:center;gap:16px">
      {logo_html}
      <span style="width:1px;height:30px;background:rgba(255,255,255,.1);display:inline-block"></span>
      <span style="color:#2d3748;font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Platform</span>
    </div>
    <div class="navlinks">
      <a href="#">Markets</a><a href="#">Forecasts</a>
      <a href="#">Research</a><a href="#">About</a>
    </div>
    <div style="width:80px"></div>
  </nav>
  <div class="hbody">
    <div class="eyebrow">Forming a View</div>
    <h1 class="htitle">LUMA <em>MarketView</em></h1>
    <p class="hsub">An AI-powered ecosystem of temporal forecasts answering
    critical questions in global crypto markets.</p>
  </div>
  <div class="strip">
    <div class="si"><span class="sym">BTC/USDT</span><span class="px">live</span><span class="up">▲</span></div>
    <div class="si"><span class="sym">ETH/USDT</span><span class="px">live</span><span class="up">▲</span></div>
    <div class="si"><span class="sym">SOL/USDT</span><span class="px">live</span><span class="dn">▼</span></div>
    <div class="si"><span class="sym">NQ · Δτ</span><span class="px">√(NQ∞)</span><span class="up">⊗</span></div>
    <div class="si"><span class="sym">XRP/USDT</span><span class="px">live</span><span class="up">▲</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("⊞  Launch LUMA"):
        st.session_state.page = "login"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE 2 — LOGIN  (fully self-contained card)
# ══════════════════════════════════════════════════════════════════════
def page_login():
    logo_tag = (f'<img src="{LOGO_URI}" style="height:40px;width:auto;display:inline-block;vertical-align:middle" />'
                if LOGO_URI
                else '<span style="font-size:1.9rem;vertical-align:middle">🌙</span>'
                     '<span style="font-family:Georgia,serif;font-size:1.6rem;font-weight:300;'
                     'color:#0f172a;vertical-align:middle;margin-left:6px">LUMA</span>')

    err_html = ('<p style="color:#dc2626;font-size:.82rem;text-align:center;margin:0 0 14px">'
                '⊗ &nbsp;Invalid sequence. Recalibrate and try again.</p>'
                if st.session_state.auth_err else "")

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=JetBrains+Mono:wght@300;400&display=swap');
*,html,body,[class*="css"]{{font-family:'Syne',sans-serif!important}}
.stApp{{background:#04060f!important}}
header,#MainMenu,footer{{display:none!important}}
.block-container{{padding:0!important;max-width:100%!important}}
section[data-testid="stSidebar"]{{display:none!important}}

/* diagonal bg */
.lbg{{position:fixed;inset:0;z-index:0;background:#04060f;overflow:hidden}}
.dl{{position:absolute;background:rgba(255,255,255,.022);width:260%;height:1px;transform-origin:center center}}

/* THE CARD — wraps everything via column background */
div[data-testid="column"]:nth-child(2) > div > div{{
  background:#ffffff;
  border-radius:6px;
  padding:44px 42px 38px!important;
  box-shadow:0 48px 120px rgba(0,0,0,.75);
  position:relative;z-index:10;
  margin-top:10vh;
}}

/* inputs inside card */
.stTextInput input{{
  border:1.5px solid #e2e8f0!important;border-radius:5px!important;
  padding:13px 16px!important;font-size:1rem!important;color:#0f172a!important;
  background:#f8fafc!important;box-shadow:none!important;outline:none!important;
  width:100%!important;
}}
.stTextInput input:focus{{
  border-color:#6366f1!important;
  background:#fff!important;
  box-shadow:0 0 0 3px rgba(99,102,241,.15)!important
}}
.stTextInput input::placeholder{{color:#94a3b8!important;font-size:.88rem!important}}
.stTextInput label{{display:none!important}}
div[data-testid="InputInstructions"]{{display:none!important}}

/* primary button = Continue */
.stButton:first-of-type > button{{
  width:100%!important;background:#1e1b4b!important;color:#fff!important;
  border:none!important;border-radius:5px!important;padding:14px!important;
  font-size:.88rem!important;font-weight:700!important;letter-spacing:.07em;
  text-transform:uppercase;margin-top:4px;
  transition:background .2s!important;
}}
.stButton:first-of-type > button:hover{{background:#3730a3!important}}

/* secondary = Back */
.stButton:last-of-type > button{{
  width:100%!important;background:transparent!important;color:#94a3b8!important;
  border:1.5px solid #e2e8f0!important;border-radius:5px!important;padding:10px!important;
  font-size:.82rem!important;font-weight:600!important;letter-spacing:.05em;
  margin-top:6px;transition:all .2s!important;
}}
.stButton:last-of-type > button:hover{{color:#475569!important;border-color:#cbd5e1!important}}
</style>

<div class="lbg">
  <div class="dl" style="top:20%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:38%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:56%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:74%;transform:rotate(-14deg)"></div>
  <div class="dl" style="top:92%;transform:rotate(-14deg)"></div>
</div>
""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        # Logo + divider + tag
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:28px">
  {logo_tag}
  <div style="width:1px;height:30px;background:#e2e8f0;flex-shrink:0"></div>
  <span style="color:#94a3b8;font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Secure Access</span>
</div>
<h2 style="color:#0f172a;font-size:1.4rem;font-weight:700;margin:0 0 6px">Sign In</h2>
<p style="color:#94a3b8;font-size:.82rem;margin:0 0 22px">Enter your access key to continue</p>
<div style="background:#f0f0ff;border:1.5px solid #c7d2fe;border-radius:6px;
  padding:10px 16px;text-align:center;margin-bottom:20px;
  font-family:'JetBrains Mono',monospace;font-size:.75rem;
  color:#6366f1;letter-spacing:.16em">Ω · √(NQ∞) · Δτ</div>
<p style="color:#475569;font-size:.78rem;margin:0 0 8px;font-weight:600">ACCESS KEY</p>
{err_html}
""", unsafe_allow_html=True)

        pw = st.text_input("key", type="password",
                           placeholder="Enter temporal root sequence…",
                           label_visibility="collapsed",
                           key="pw_input")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

        if st.button("Continue  →", use_container_width=True):
            if pw == PASSWORD:
                st.session_state.page     = "dashboard"
                st.session_state.auth_err = False
                st.rerun()
            else:
                st.session_state.auth_err = True
                st.rerun()

        if st.button("← Back to home", use_container_width=True, key="back_btn"):
            st.session_state.page     = "landing"
            st.session_state.auth_err = False
            st.rerun()

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  PAGE 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════
def page_dashboard():

    # ── sidebar ────────────────────────────────────────────────────────
    with st.sidebar:
        if LOGO_URI:
            st.markdown(f'<img src="{LOGO_URI}" style="height:30px;margin-bottom:8px" />', unsafe_allow_html=True)
        else:
            st.markdown("### 🌙 LUMA")
        st.markdown("---")

        st.caption("🪙 ASSET")
        coin_choice   = st.selectbox("Coin", list(POPULAR_COINS.keys()), label_visibility="collapsed")
        symbol        = (st.text_input("Symbol","BTCUSDT", label_visibility="collapsed").upper().strip()
                         if POPULAR_COINS[coin_choice]=="__custom__"
                         else POPULAR_COINS[coin_choice])

        st.caption("⏱ TIMEFRAMES")
        selected_tfs  = st.multiselect("TFs", list(INTERVAL_MINUTES.keys()),
                                       default=["15m","1h","4h"], label_visibility="collapsed")

        st.caption("📅 RANGE")
        lookback_days = st.slider("Lookback", 7, 365, 90, step=7, label_visibility="collapsed")
        forecast_days = st.slider("Forecast", 1, 30, 7, label_visibility="collapsed")

        st.caption("🤖 LUMA AI KEY  (HuggingFace)")
        hf_key = st.text_input("HF", type="password", placeholder="hf_xxx…",
                                label_visibility="collapsed")

        st.caption("📤 UPLOAD CHARTS")
        uploaded_files = st.file_uploader("Upload", type=["png","jpg","jpeg","gif","webp"],
                                          accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files:
            st.session_state.uploaded = uploaded_files

        st.markdown("---")
        run_btn = st.button("⊞  Run LUMA Forecast", type="primary", use_container_width=True)
        if st.button("Sign Out", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()
        st.caption("🌙 LUMA")

    # ── dashboard styles ───────────────────────────────────────────────
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=Syne:wght@400;600;700&display=swap');
*,[class*="css"]{font-family:'Syne',sans-serif!important}
.stApp{background:#080c1a!important}
header,#MainMenu,footer{display:none!important}
.block-container{padding:0 14px 28px 14px!important;max-width:100%!important}
section[data-testid="stSidebar"]{background:#05060e!important;border-right:1px solid #111827}

.tkbar{background:#0a0d1c;border-bottom:1px solid #111827;padding:13px 22px;
  display:flex;align-items:center;flex-wrap:wrap;gap:22px}
.tksym{font-size:1.5rem;font-weight:700;color:#f1f5f9;
  font-family:'IBM Plex Mono',monospace!important;display:flex;align-items:center;gap:9px}
.tkbadge{background:#1e3a5f;color:#38bdf8;font-size:.6rem;font-weight:700;
  padding:3px 8px;border-radius:3px;letter-spacing:.08em}
.tkprice{font-family:'IBM Plex Mono',monospace!important;font-size:1.85rem;font-weight:400;color:#f1f5f9}
.pos{color:#34d399} .neg{color:#f87171}
.tkstat .l{color:#374151;font-size:.64rem;text-transform:uppercase;letter-spacing:.07em}
.tkstat .v{color:#94a3b8;font-size:.78rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}

.igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:5px;
  margin:10px 0;overflow:hidden}
.icell{background:#0a0d1c;padding:9px 14px}
.icell .l{color:#374151;font-size:.63rem;text-transform:uppercase;letter-spacing:.07em}
.icell .v{color:#cbd5e1;font-size:.82rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}

.gbadge{display:inline-block;background:#0a2214;border:2px solid #34d399;
  color:#34d399;font-size:.95rem;font-weight:700;padding:9px 20px;border-radius:4px;
  letter-spacing:.04em;margin:10px 0;font-family:'IBM Plex Mono',monospace!important}

.sh{color:#38bdf8;font-size:.68rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.13em;border-bottom:1px solid #111827;padding-bottom:5px;margin:16px 0 10px}

.chwrap{background:#0a0d1c;border:1px solid #111827;border-radius:5px;
  padding:3px;overflow:hidden}

/* chat box */
.chat-wrap{background:#0a0d1c;border:1px solid #111827;border-radius:6px;
  padding:16px;max-height:360px;overflow-y:auto;margin-bottom:10px}
.msg-luma{background:#0d1f0d;border:1px solid #1a3a1a;border-radius:6px;
  padding:12px 16px;margin-bottom:10px;color:#a7f3d0;font-size:.86rem;line-height:1.72}
.msg-user{background:#1a1a3a;border:1px solid #2d2d5a;border-radius:6px;
  padding:10px 14px;margin-bottom:10px;color:#c4b5fd;font-size:.84rem;
  text-align:right;line-height:1.6}
.msg-label-l{color:#34d399;font-size:.66rem;font-weight:700;letter-spacing:.08em;margin-bottom:5px}
.msg-label-u{color:#7c3aed;font-size:.66rem;font-weight:700;letter-spacing:.08em;
  margin-bottom:5px;text-align:right}
</style>
""", unsafe_allow_html=True)

    # ── live ticker ─────────────────────────────────────────────────────
    lp, lc, lv = get_live_ticker(symbol)
    ps  = f"${lp:,.2f}"      if lp  else "—"
    cs  = f"{'▲' if (lc or 0)>=0 else '▼'} {abs(lc):.2f}%" if lc is not None else "—"
    cc  = "pos" if (lc or 0)>=0 else "neg"
    vs  = f"${lv/1e9:.2f}B"  if lv  else "—"
    ts  = datetime.now().strftime("%b %d  %H:%M:%S")

    st.markdown(f"""
<div class="tkbar">
  <div class="tksym">{symbol[:3]}<span class="tkbadge">CRYPTO</span></div>
  <div class="tkprice">{ps}</div>
  <div class="{cc}" style="font-size:1rem;font-family:'IBM Plex Mono',monospace">{cs}</div>
  <div class="tkstat"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
  <div class="tkstat"><div class="l">Exchange</div><div class="v">Binance.US</div></div>
  <div class="tkstat"><div class="l">Pair</div><div class="v">{symbol}</div></div>
  <div style="margin-left:auto">
    <div class="tkstat"><div class="l">Updated</div><div class="v">{ts}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── layout ──────────────────────────────────────────────────────────
    main_col, side_col = st.columns([3.2, 1])

    with main_col:

        if not run_btn and not st.session_state.summaries:
            st.markdown("""
<div style="text-align:center;padding:140px 0;color:#111827">
  <div style="font-size:3.5rem">🌙</div>
  <div style="font-size:.9rem;margin-top:14px;color:#1e293b">
    Configure in sidebar → Run LUMA Forecast
  </div>
</div>""", unsafe_allow_html=True)

        elif run_btn:
            if not selected_tfs:
                st.warning("Select at least one timeframe.")
            else:
                with st.spinner("Initializing LUMA…"):
                    if not validate_symbol(symbol):
                        st.error(f"**{symbol}** not found. Use USDT pairs: BTCUSDT, ETHUSDT, SOLUSDT…")
                        st.stop()
                    luma_model = load_model()

                COLORS = ["#a78bfa","#38bdf8","#fb923c","#34d399","#f472b6","#facc15"]
                fig = go.Figure()
                fcast_dfs, summaries, raw_dfs = {}, {}, {}
                any_data = False
                prim     = selected_tfs[0]
                prog     = st.progress(0)

                for i, tf in enumerate(selected_tfs):
                    prog.progress(i/len(selected_tfs), text=f"Processing {tf}…")
                    col_c = COLORS[i % len(COLORS)]
                    eff   = min(lookback_days, INTERVAL_MAX_DAYS[tf])
                    try:
                        df = fetch_binance(symbol, tf, eff)
                    except Exception as e:
                        st.warning(f"⚠️ {tf}: {e}"); continue
                    if len(df) < 30: continue

                    any_data      = True
                    raw_dfs[tf]   = df
                    prices, dates = df["Close"].values, df.index
                    mins          = INTERVAL_MINUTES[tf]
                    horizon       = min(max(1, int(forecast_days*1440/mins)), 256)

                    pt, _  = luma_model.forecast(horizon=horizon, inputs=[prices[-1024:]])
                    fc     = pt[0]
                    td     = pd.Timedelta(minutes=mins)
                    fi     = pd.date_range(start=dates[-1]+td, periods=len(fc),
                                           freq=td, tz=dates.tzinfo)

                    fcast_dfs[tf] = pd.DataFrame({"Datetime":fi, "Forecast":fc.round(6)})
                    summaries[tf] = {"last":float(prices[-1]), "end":float(fc[-1]), "bars":len(fc)}

                    sn = min(300, len(df))
                    if tf == prim:
                        fig.add_trace(go.Candlestick(
                            x=dates[-sn:], open=df["Open"].iloc[-sn:], high=df["High"].iloc[-sn:],
                            low=df["Low"].iloc[-sn:],  close=df["Close"].iloc[-sn:], name=f"Price ({tf})",
                            increasing_line_color="#34d399", decreasing_line_color="#f87171",
                            increasing_fillcolor="rgba(52,211,153,.15)",
                            decreasing_fillcolor="rgba(248,113,113,.15)"))
                    else:
                        fig.add_trace(go.Scatter(
                            x=dates[-sn:], y=prices[-sn:], mode="lines",
                            name=f"Price ({tf})",
                            line=dict(color=col_c, width=1, dash="dot"), opacity=.45))

                    r2,g2,b2 = int(col_c[1:3],16),int(col_c[3:5],16),int(col_c[5:7],16)
                    fig.add_trace(go.Scatter(
                        x=list(fi)+list(fi[::-1]),
                        y=list(fc*1.012)+list(fc[::-1]*0.988),
                        fill="toself", fillcolor=f"rgba({r2},{g2},{b2},.06)",
                        line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip"))
                    fig.add_trace(go.Scatter(
                        x=fi, y=fc, mode="lines+markers", name=f"LUMA ({tf})",
                        line=dict(color=col_c, width=2.5, dash="dash"),
                        marker=dict(size=5, symbol="diamond"),
                        hovertemplate="<b>%{x|%b %d %H:%M}</b><br>$%{y:,.4f}<extra></extra>"))

                prog.progress(1.0, "Done!"); time.sleep(.2); prog.empty()

                if any_data:
                    # save to session for chat
                    st.session_state.summaries  = summaries
                    st.session_state.symbol     = symbol
                    st.session_state.fcast_dfs  = fcast_dfs
                    st.session_state.raw_dfs    = raw_dfs
                    st.session_state.chat_history = []

                    fig.update_layout(
                        paper_bgcolor="#0a0d1c", plot_bgcolor="#0a0d1c",
                        font=dict(color="#94a3b8", family="IBM Plex Mono"),
                        title=dict(text=f"🌙 LUMA · <b>{symbol}</b>  Multi-TF Forecast",
                                   font=dict(color="#f1f5f9",size=14), x=0.01),
                        xaxis=dict(gridcolor="#0e1325", linecolor="#111827",
                                   rangeslider=dict(visible=True,bgcolor="#07090f",thickness=.04)),
                        yaxis=dict(gridcolor="#0e1325", linecolor="#111827"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.01,
                                    xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                        hovermode="x unified", height=510,
                        margin=dict(l=28,r=28,t=65,b=28))

                    st.markdown('<div class="chwrap">', unsafe_allow_html=True)
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                    # gain badge + stats grid
                    best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/summaries[x]["last"]))
                    bpct = (summaries[best]["end"]-summaries[best]["last"])/summaries[best]["last"]*100
                    cells = ""
                    for tf2, s in summaries.items():
                        p2  = (s["end"]-s["last"])/s["last"]*100
                        cc2 = "#34d399" if p2>=0 else "#f87171"
                        cells += (f'<div class="icell"><div class="l">LUMA {tf2}</div>'
                                  f'<div class="v" style="color:{cc2}">{"▲" if p2>=0 else "▼"} {abs(p2):.2f}%</div></div>'
                                  f'<div class="icell"><div class="l">Forecast</div>'
                                  f'<div class="v">${s["end"]:,.4f}</div></div>')

                    st.markdown(f"""
<div class="gbadge">{symbol[:3]} &nbsp; {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp; ({best} forecast)</div>
<div class="igrid">{cells}</div>""", unsafe_allow_html=True)

                    # ── OHLC DOWNLOAD ──────────────────────────────────
                    st.markdown('<div class="sh">⬇️ Download Data</div>', unsafe_allow_html=True)
                    dl_cols = st.columns(len(raw_dfs) + 1)
                    for idx, (tf3, df_r) in enumerate(raw_dfs.items()):
                        with dl_cols[idx]:
                            st.download_button(
                                f"OHLC {tf3}",
                                data=df_r.reset_index().to_csv(index=False),
                                file_name=f"luma_{symbol}_{tf3}_ohlc.csv",
                                mime="text/csv", use_container_width=True)
                    with dl_cols[-1]:
                        all_fc = pd.concat([d.assign(TF=t) for t,d in fcast_dfs.items()])
                        st.download_button(
                            "Forecasts CSV",
                            data=all_fc.to_csv(index=False),
                            file_name=f"luma_{symbol}_forecasts.csv",
                            mime="text/csv", use_container_width=True)

                    # ── LUMA AI ANALYSIS + CHAT ────────────────────────
                    if hf_key:
                        st.markdown('<div class="sh">🌙 LUMA Analysis</div>', unsafe_allow_html=True)

                        # Initial analysis (auto-runs after forecast)
                        if "initial_analysis" not in st.session_state or run_btn:
                            with st.spinner("LUMA is reading the charts…"):
                                analysis = initial_analysis(hf_key, symbol, summaries, raw_dfs)
                                st.session_state.initial_analysis = analysis

                        st.markdown(f"""
<div class="chat-wrap">
  <div class="msg-label-l">🌙 LUMA</div>
  <div class="msg-luma">{st.session_state.initial_analysis.replace(chr(10),"<br>")}</div>
  {"".join(
    f'<div class="msg-label-u">YOU</div>'
    f'<div class="msg-user">{h["user"]}</div>'
    f'<div class="msg-label-l">🌙 LUMA</div>'
    f'<div class="msg-luma">{h["luma"].replace(chr(10),"<br>")}</div>'
    for h in st.session_state.chat_history
  )}
</div>""", unsafe_allow_html=True)

                        # Chat input
                        q_col, btn_col = st.columns([5, 1])
                        with q_col:
                            user_q = st.text_input("Ask LUMA…",
                                placeholder="e.g. What's your target for BTC in the next 4h?",
                                label_visibility="collapsed", key="chat_input")
                        with btn_col:
                            ask_btn = st.button("Ask →", use_container_width=True)

                        if ask_btn and user_q.strip():
                            with st.spinner("LUMA is thinking…"):
                                reply = chat_response(
                                    hf_key, symbol, summaries, raw_dfs,
                                    user_q, st.session_state.chat_history)
                                st.session_state.chat_history.append(
                                    {"user": user_q, "luma": reply})
                                st.rerun()

                        if st.session_state.chat_history:
                            if st.button("Clear Chat", key="clear_chat"):
                                st.session_state.chat_history = []
                                st.rerun()
                    else:
                        st.info("🌙 Add your HuggingFace key in the sidebar to unlock LUMA AI analysis and chat.")

        # If we have saved state, show forecast tables
        if st.session_state.fcast_dfs:
            st.markdown('<div class="sh">📋 Forecast Tables</div>', unsafe_allow_html=True)
            for tf4, df_f in st.session_state.fcast_dfs.items():
                with st.expander(f"{tf4}  ·  {len(df_f)} bars"):
                    st.dataframe(df_f.style.format({"Forecast":"${:,.6f}"}),
                                 use_container_width=True)

    # ── RIGHT PANEL ──────────────────────────────────────────────────────
    with side_col:
        st.markdown('<div class="sh">📤 Uploaded Charts</div>', unsafe_allow_html=True)
        if st.session_state.uploaded:
            for uf in st.session_state.uploaded:
                ext = uf.name.rsplit(".",1)[-1].lower()
                if ext in ("png","jpg","jpeg","gif","webp"):
                    st.image(uf, use_container_width=True, caption=uf.name)
        else:
            st.markdown("""
<div style="border:1px dashed #1a2035;border-radius:6px;padding:28px 10px;
  text-align:center;color:#1e293b;font-size:.78rem;line-height:1.8">
  Drop chart screenshots<br>via sidebar uploader
</div>""", unsafe_allow_html=True)

        if lp:
            st.markdown('<div class="sh" style="margin-top:18px">⚡ Live</div>', unsafe_allow_html=True)
            st.markdown(f"""
<div class="igrid" style="grid-template-columns:1fr">
  <div class="icell"><div class="l">Price</div><div class="v">{ps}</div></div>
  <div class="icell"><div class="l">Change</div>
    <div class="v {cc}">{cs}</div></div>
  <div class="icell"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
</div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════
p = st.session_state.page
if   p == "landing":    page_landing()
elif p == "login":      page_login()
elif p == "dashboard":  page_dashboard()
else:                   page_landing()

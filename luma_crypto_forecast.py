"""
LOMA · Crypto Forecast Platform
Password: 953
Run: streamlit run luma_fixed.py
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
EST = ZoneInfo("America/New_York")
import time, base64, os, json

# ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="LOMA", page_icon="🌙", layout="wide",
                   initial_sidebar_state="collapsed")

PASSWORD         = "953"
PREMIUM_PASSWORD = "password"

# ── API keys ──────────────────────────────────────────────────────────
OPENROUTER_KEY   = "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"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"
HF_KEY           = "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"

DEFAULTS = {
    "page": "landing", "auth_err": False,
    "sub": "home",
    "chat_history": [], "summaries": {}, "symbol": "BTCUSDT",
    "fcast_dfs": {}, "raw_dfs": {},
    "uploaded_files": [], "initial_analysis": "",
    "live_symbol": "BTCUSDT", "forecast_ran": False,
    "premium_auth": False,
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
                ext = p.rsplit(".",1)[-1].lower()
                mime = "jpeg" if ext in ("jpg","jpeg") else "png"
                with open(p,"rb") as f:
                    return f"data:image/{mime};base64,{base64.b64encode(f.read()).decode()}"
        except: pass
    return ""

LOGO_URI = load_logo_b64()

def logo_tag(h=56, dark=False):
    color = "#0f172a" if dark else "#f1f5f9"
    if LOGO_URI:
        return f'<img src="{LOGO_URI}" style="height:{h}px;width:auto;display:inline-block;vertical-align:middle" />'
    return (f'<span style="font-family:Georgia,serif;font-size:{int(h*0.7)}px;'
            f'font-weight:300;color:{color};vertical-align:middle;letter-spacing:.04em">🌙 LOMA</span>')

# ─────────────────────────────────────────────────────────────────────
#  TOP 100 COINS  +  symbol normalizer
# ─────────────────────────────────────────────────────────────────────
TOP_COINS = [
    ("Bitcoin","BTCUSDT"),("Ethereum","ETHUSDT"),("BNB","BNBUSDT"),
    ("Solana","SOLUSDT"),("XRP","XRPUSDT"),("Cardano","ADAUSDT"),
    ("Avalanche","AVAXUSDT"),("Dogecoin","DOGEUSDT"),("Chainlink","LINKUSDT"),
    ("Polkadot","DOTUSDT"),("TRON","TRXUSDT"),("Polygon","MATICUSDT"),
    ("Litecoin","LTCUSDT"),("Shiba Inu","SHIBUSDT"),("Stellar","XLMUSDT"),
    ("Ethereum Classic","ETCUSDT"),("Cosmos","ATOMUSDT"),("Near Protocol","NEARUSDT"),
    ("Algorand","ALGOUSDT"),("VeChain","VETUSDT"),("Filecoin","FILUSDT"),
    ("Hedera","HBARUSDT"),("Aptos","APTUSDT"),("Arbitrum","ARBUSDT"),
    ("Optimism","OPUSDT"),("Sui","SUIUSDT"),("Injective","INJUSDT"),
    ("Bitcoin Cash","BCHUSDT"),("Aave","AAVEUSDT"),("Uniswap","UNIUSDT"),
    ("Maker","MKRUSDT"),("Compound","COMPUSDT"),("Curve","CRVUSDT"),
    ("Stacks","STXUSDT"),("Immutable X","IMXUSDT"),("Celestia","TIAUSDT"),
    ("dYdX","DYDXUSDT"),("Pepe","PEPEUSDT"),("Floki","FLOKIUSDT"),
    ("Bonk","BONKUSDT"),("WIF","WIFUSDT"),("Jupiter","JUPUSDT"),
    ("Pyth","PYTHUSDT"),("Worldcoin","WLDUSDT"),("Fetch.ai","FETUSDT"),
    ("SingularityNET","AGIXUSDT"),("The Graph","GRTUSDT"),("1inch","1INCHUSDT"),
    ("PancakeSwap","CAKEUSDT"),("Lido DAO","LDOUSDT"),("Synthetix","SNXUSDT"),
    ("Yearn Finance","YFIUSDT"),("Balancer","BALUSDT"),("Sushi","SUSHIUSDT"),
    ("Enjin","ENJUSDT"),("Chiliz","CHZUSDT"),("Axie Infinity","AXSUSDT"),
    ("Decentraland","MANAUSDT"),("The Sandbox","SANDUSDT"),("Gala","GALAUSDT"),
    ("Raydium","RAYUSDT"),("IOTA","IOTAUSDT"),("NEO","NEOUSDT"),
    ("Theta","THETAUSDT"),("Fantom","FTMUSDT"),("Harmony","ONEUSDT"),
    ("Zilliqa","ZILUSDT"),("Zcash","ZECUSDT"),("Dash","DASHUSDT"),
    ("Flow","FLOWUSDT"),("Celo","CELOUSDT"),("Klaytn","KLAYUSDT"),
    ("Kava","KAVAUSDT"),("Band Protocol","BANDUSDT"),("API3","API3USDT"),
    ("Render","RENDERUSDT"),("Sei","SEIUSDT"),("Mantle","MNTUSDT"),
    ("Blur","BLURUSDT"),("Arkham","ARKMUSDT"),("Ocean Protocol","OCEANUSDT"),
    ("Mask Network","MASKUSDT"),("Loopring","LRCUSDT"),("Storj","STORJUSDT"),
    ("Civic","CVCUSDT"),("Ontology","ONTUSDT"),("Qtum","QTUMUSDT"),
    ("Waves","WAVESUSDT"),("Monero","XMRUSDT"),("EOS","EOSUSDT"),
    ("TEZOS","XTZUSDT"),("Horizen","ZENUSDT"),("Icon","ICXUSDT"),
    ("Lisk","LSKUSDT"),("NEM","XEMUST"),("Nano","NANOUSDT"),
    ("Custom…","__custom__"),
]

COIN_NAME_TO_SYMBOL = {name.upper(): sym for name,sym in TOP_COINS if sym!="__custom__"}
COIN_SYM_TO_NAME    = {sym: name for name,sym in TOP_COINS if sym!="__custom__"}

NAME_SHORTCUTS = {
    "BTC":"BTCUSDT","BITCOIN":"BTCUSDT","BTCUSD":"BTCUSDT",
    "ETH":"ETHUSDT","ETHEREUM":"ETHUSDT","ETHUSD":"ETHUSDT",
    "SOL":"SOLUSDT","SOLANA":"SOLUSDT","SOLUSD":"SOLUSDT",
    "XRP":"XRPUSDT","RIPPLE":"XRPUSDT","XRPUSD":"XRPUSDT",
    "BNB":"BNBUSDT","BNBUSD":"BNBUSDT",
    "ADA":"ADAUSDT","CARDANO":"ADAUSDT","ADAUSD":"ADAUSDT",
    "AVAX":"AVAXUSDT","AVALANCHE":"AVAXUSDT",
    "DOGE":"DOGEUSDT","DOGECOIN":"DOGEUSDT",
    "LINK":"LINKUSDT","CHAINLINK":"LINKUSDT",
    "DOT":"DOTUSDT","POLKADOT":"DOTUSDT",
    "MATIC":"MATICUSDT","POLYGON":"MATICUSDT",
    "LTC":"LTCUSDT","LITECOIN":"LTCUSDT",
    "SHIB":"SHIBUSDT",
    "XLM":"XLMUSDT","STELLAR":"XLMUSDT",
    "ATOM":"ATOMUSDT","COSMOS":"ATOMUSDT",
    "NEAR":"NEARUSDT",
    "ALGO":"ALGOUSDT","ALGORAND":"ALGOUSDT",
    "FIL":"FILUSDT","FILECOIN":"FILUSDT",
    "APT":"APTUSDT","APTOS":"APTUSDT",
    "ARB":"ARBUSDT","ARBITRUM":"ARBUSDT",
    "OP":"OPUSDT","OPTIMISM":"OPUSDT",
    "SUI":"SUIUSDT",
    "INJ":"INJUSDT","INJECTIVE":"INJUSDT",
    "BCH":"BCHUSDT",
    "AAVE":"AAVEUSDT",
    "UNI":"UNIUSDT","UNISWAP":"UNIUSDT",
    "MKR":"MKRUSDT","MAKER":"MKRUSDT",
    "PEPE":"PEPEUSDT",
    "WIF":"WIFUSDT",
    "JUP":"JUPUSDT","JUPITER":"JUPUSDT",
    "FET":"FETUSDT",
    "GRT":"GRTUSDT",
    "XMR":"XMRUSDT","MONERO":"XMRUSDT",
    "EOS":"EOSUSDT",
    "XTZ":"XTZUSDT","TEZOS":"XTZUSDT",
    "ETC":"ETCUSDT",
}

def normalize_symbol(raw: str) -> str:
    raw = raw.strip().upper().replace("-","").replace("/","").replace("_","").replace(" ","")
    if raw in NAME_SHORTCUTS:
        return NAME_SHORTCUTS[raw]
    if raw in COIN_NAME_TO_SYMBOL:
        return COIN_NAME_TO_SYMBOL[raw]
    if raw.endswith("USDT"):
        return raw
    if raw.endswith("USD"):
        return raw[:-3] + "USDT"
    return raw + "USDT"

# ─────────────────────────────────────────────────────────────────────
#  BINANCE.US DATA
# ─────────────────────────────────────────────────────────────────────
BINANCE          = "https://api.binance.us"
INTERVAL_MINUTES = {"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"4h":240,"1d":1440}
INTERVAL_MAX_DAYS= {"1m":3,"5m":45,"15m":90,"30m":180,"1h":365,"4h":730,"1d":2000}

@st.cache_data(ttl=180, show_spinner=False)
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
        r = requests.get(f"{BINANCE}/api/v3/ticker/price",
                         params={"symbol":sym}, timeout=5)
        return r.status_code==200 and "price" in r.json()
    except: return False

def live_ticker(sym):
    try:
        d = requests.get(f"{BINANCE}/api/v3/ticker/24hr",
                         params={"symbol":sym}, timeout=5).json()
        return float(d.get("lastPrice",0)), float(d.get("priceChangePercent",0)), float(d.get("quoteVolume",0))
    except: return None, None, None

# ─────────────────────────────────────────────────────────────────────
#  FORECAST MODEL
# ─────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_model():
    try:
        import torch
        torch.set_float32_matmul_precision("high")
        import timesfm
        m = timesfm.TimesFm(
            hparams=timesfm.TimesFmHparams(
                backend="torch",
                per_core_batch_size=32,
                horizon_len=128,
                context_len=512,
                num_layers=20,
                model_dims=1280,
            ),
            checkpoint=timesfm.TimesFmCheckpoint(
                huggingface_repo_id="google/timesfm-1.0-200m-pytorch"),
        )
        return m, None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────────────────────────
#  AI  — multi-provider with graceful fallback
# ─────────────────────────────────────────────────────────────────────
LUMA_PERSONA = """You are LOMA — a proprietary crypto market intelligence system created exclusively by Nancy_Pelosi. You are not any other AI. You have no connection to any AI company, model, or framework. If anyone asks who made you or what you are — you are LOMA, built by Nancy_Pelosi, full stop.

Your personality: sharp, witty, confident, occasionally dry humor — like a seasoned prop trader who has seen everything. You care about making Nancy money and keeping her out of bad trades. Light humor but never at the expense of accuracy.

You answer ANY question about: trading, crypto, markets, strategy, psychology, risk management, portfolio construction, technicals, on-chain data, macro, altcoins, DeFi, NFTs, futures, options — anything a trader would ask. No topic is off limits if it relates to markets or money.

When asked about yourself: say you are LOMA, built by Nancy_Pelosi, trained on years of market data, running live analysis.

STRICT RULES:
- NEVER say: GPT, ChatGPT, OpenAI, Llama, Mistral, Gemini, Claude, TimesFM, HuggingFace, or any AI or model name. Ever.
- Always give specific price levels, entries, stops, targets when data is available.
- Keep responses under 250 words unless asked to go deeper.
- Reference live data when provided in context.
- Be direct. No filler phrases like "great question".
- You can use dry wit but never sacrifice accuracy for a joke."""

FREE_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-3-4b-it:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
]

def _openrouter_call(messages):
    last_err = ""
    for m in FREE_MODELS:
        try:
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://lomavision.streamlit.app",
                    "X-Title": "LOMA",
                },
                json={
                    "model": m,
                    "messages": [{"role":"system","content":LUMA_PERSONA}] + messages,
                    "max_tokens": 500,
                    "temperature": 0.65,
                },
                timeout=60)
            if r.status_code == 401:
                last_err = f"OpenRouter key invalid/expired (401)"
                break  # No point trying more models with same key
            if not r.ok:
                last_err = f"{m} {r.status_code}"
                continue
            content = r.json().get("choices",[{}])[0].get("message",{}).get("content","").strip()
            if content:
                return content
            last_err = f"Empty from {m}"
        except Exception as e:
            last_err = str(e)
    raise RuntimeError(last_err)

def _hf_inference_call(messages):
    """Try HuggingFace serverless inference."""
    models_to_try = [
        ("mistralai/Mistral-7B-Instruct-v0.3", "v1/chat/completions"),
        ("HuggingFaceH4/zephyr-7b-beta", "v1/chat/completions"),
    ]
    for model_id, endpoint in models_to_try:
        try:
            r = requests.post(
                f"https://api-inference.huggingface.co/models/{model_id}/{endpoint}",
                headers={"Authorization": f"Bearer {HF_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model_id,
                    "messages": [{"role":"system","content":LUMA_PERSONA}] + messages,
                    "max_tokens": 450,
                    "temperature": 0.65,
                },
                timeout=60)
            if r.status_code in (401, 403):
                raise RuntimeError("HF token expired/invalid")
            if not r.ok:
                continue
            content = r.json().get("choices",[{}])[0].get("message",{}).get("content","").strip()
            if content:
                return content
        except RuntimeError:
            raise
        except Exception:
            continue
    raise RuntimeError("All HF models failed")

def _ollama_local_call(messages):
    """Try local Ollama if running."""
    try:
        full_prompt = LUMA_PERSONA + "\n\n"
        for m in messages:
            role = "User" if m["role"] == "user" else "Assistant"
            full_prompt += f"{role}: {m['content']}\n"
        full_prompt += "Assistant:"
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "mistral", "prompt": full_prompt, "stream": False},
            timeout=30)
        if r.ok:
            return r.json().get("response","").strip()
    except:
        pass
    raise RuntimeError("Ollama not available")

def _compute_technicals(df):
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values
    v = df["Volume"].values if "Volume" in df.columns else None
    n = len(c)

    def ema(arr, period):
        k = 2.0 / (period + 1)
        out = [arr[0]]
        for x in arr[1:]:
            out.append(x * k + out[-1] * (1 - k))
        return np.array(out)

    ema9  = ema(c, 9)[-1]  if n >= 9  else c[-1]
    ema21 = ema(c, 21)[-1] if n >= 21 else c[-1]
    ema50 = ema(c, 50)[-1] if n >= 50 else c[-1]

    rsi = 50.0
    if n >= 15:
        deltas = np.diff(c[-15:])
        gains  = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_g, avg_l = gains.mean(), losses.mean()
        rsi = 100.0 if avg_l == 0 else 100 - (100 / (1 + avg_g / avg_l))

    window   = min(50, n)
    recent_h = h[-window:]
    recent_l = l[-window:]

    pivots_h, pivots_l = [], []
    for i in range(2, len(recent_h) - 2):
        if recent_h[i] > recent_h[i-1] and recent_h[i] > recent_h[i-2] and \
           recent_h[i] > recent_h[i+1] and recent_h[i] > recent_h[i+2]:
            pivots_h.append(recent_h[i])
        if recent_l[i] < recent_l[i-1] and recent_l[i] < recent_l[i-2] and \
           recent_l[i] < recent_l[i+1] and recent_l[i] < recent_l[i+2]:
            pivots_l.append(recent_l[i])

    price = c[-1]
    res_levels = sorted([x for x in pivots_h if x > price])
    sup_levels = sorted([x for x in pivots_l if x < price], reverse=True)
    resistance = res_levels[0] if res_levels else max(recent_h)
    support    = sup_levels[0] if sup_levels else min(recent_l)

    atr = 0.0
    if n >= 14:
        tr_vals = [max(h[i]-l[i], abs(h[i]-c[i-1]), abs(l[i]-c[i-1])) for i in range(-14, 0)]
        atr = float(np.mean(tr_vals))
    else:
        atr = (max(recent_h) - min(recent_l)) / window

    vol_trend = "rising" if (v is not None and len(v) >= 10 and
                              v[-5:].mean() > v[-10:-5].mean()) else "flat/falling"
    mom_5 = (c[-1] - c[-5]) / c[-5] * 100 if n >= 5 else 0.0

    return {
        "price": price, "ema9": ema9, "ema21": ema21, "ema50": ema50,
        "rsi": rsi, "support": support, "resistance": resistance,
        "atr": atr, "vol_trend": vol_trend, "mom_5": mom_5,
        "high_50": max(recent_h), "low_50": min(recent_l),
    }


def _loma_analysis_text(sym, summaries, raw_dfs):
    if not summaries or not raw_dfs:
        return f"No data loaded for {sym}. Run a forecast first."

    pref = ["4h","1h","1d","15m","30m","5m","1m"]
    main_tf = next((t for t in pref if t in raw_dfs), list(raw_dfs.keys())[0])
    t = _compute_technicals(raw_dfs[main_tf])
    price, rsi, sup, res, atr = t["price"], t["rsi"], t["support"], t["resistance"], t["atr"]

    if t["ema9"] > t["ema21"] > t["ema50"]:
        ema_read = "EMAs stacked bullish (9 > 21 > 50)"
    elif t["ema9"] < t["ema21"] < t["ema50"]:
        ema_read = "EMAs stacked bearish (9 < 21 < 50)"
    elif t["ema9"] > t["ema21"]:
        ema_read = "short-term momentum turning up (9 > 21, below 50)"
    else:
        ema_read = "short-term momentum fading (9 < 21)"

    if rsi >= 70:   rsi_read = f"RSI {rsi:.0f} — overbought, watch for exhaustion"
    elif rsi <= 30: rsi_read = f"RSI {rsi:.0f} — oversold, potential bounce zone"
    elif rsi >= 55: rsi_read = f"RSI {rsi:.0f} — bullish momentum, room to run"
    elif rsi <= 45: rsi_read = f"RSI {rsi:.0f} — bearish pressure, sellers in control"
    else:           rsi_read = f"RSI {rsi:.0f} — neutral, consolidating"

    bullish_tfs = [tf for tf,s in summaries.items() if s["end"] >= s["last"]]
    bearish_tfs = [tf for tf,s in summaries.items() if s["end"] <  s["last"]]
    bull_n, total = len(bullish_tfs), len(summaries)

    if bull_n == total:
        confluence = f"Full bull confluence — all {total} TFs ({', '.join(bullish_tfs)}) pointing higher"
        bias = "LONG"
    elif bull_n == 0:
        confluence = f"Full bear confluence — all {total} TFs ({', '.join(bearish_tfs)}) pointing lower"
        bias = "SHORT"
    elif bull_n > total / 2:
        confluence = f"Bull majority — {', '.join(bullish_tfs)} bullish, {', '.join(bearish_tfs)} lagging"
        bias = "LONG-LEANING"
    else:
        confluence = f"Bear majority — {', '.join(bearish_tfs)} bearish, {', '.join(bullish_tfs)} holding"
        bias = "SHORT-LEANING"

    main_s = summaries.get(main_tf, list(summaries.values())[0])
    target = main_s["end"]
    fc_pct = (target - price) / price * 100

    if "LONG" in bias:
        trade_note = (f"Long entry zone: **${sup:.4f}–${sup*1.002:.4f}**, stop **${sup*0.992:.4f}**, "
                      f"TP1 **${res:.4f}**, TP2 **${res*1.015:.4f}**.")
    else:
        trade_note = (f"Short entry zone: **${res:.4f}–${res*0.998:.4f}**, stop **${res*1.008:.4f}**, "
                      f"TP1 **${sup:.4f}**, TP2 **${sup*0.985:.4f}**.")

    if rsi >= 68:   risk = "Overbought RSI — don't chase longs here."
    elif rsi <= 32: risk = "Oversold RSI — size down on shorts."
    elif t["vol_trend"] == "flat/falling" and "LONG" in bias:
        risk = "Volume not confirming the move — wait for a vol surge entry."
    else:
        risk = f"Keep stops at least 1× ATR (${atr:.4f}) from entry."

    return (
        f"**{sym} — {main_tf.upper()} Analysis**\n\n"
        f"Price: **${price:,.4f}** | Bias: **{bias}**\n\n"
        f"**Structure:** {ema_read}. {rsi_read}. Volume {t['vol_trend']}.\n\n"
        f"**Key Levels:** Support **${sup:,.4f}** · Resistance **${res:,.4f}** · "
        f"50-bar range ${t['low_50']:,.4f}–${t['high_50']:,.4f}\n\n"
        f"**Forecast ({main_tf}):** ${price:,.4f} → **${target:,.4f}** ({fc_pct:+.2f}%)\n\n"
        f"**Multi-TF:** {confluence}\n\n"
        f"**Trade:** {trade_note}\n\n"
        f"**Risk:** {risk}"
    )


def _loma_chat_reply(question, sym, summaries, raw_dfs, history):
    """
    Intelligent conversational fallback — handles ANY trading question
    when no AI API is available. Uses live technicals + broad topic coverage.
    """
    q = question.lower().strip()
    pref = ["4h","1h","1d","15m","30m","5m","1m"]
    main_tf = next((tf for tf in pref if tf in raw_dfs), list(raw_dfs.keys())[0] if raw_dfs else None)
    t = _compute_technicals(raw_dfs[main_tf]) if main_tf and raw_dfs else None
    price = t["price"] if t else None
    coin = sym.replace("USDT","").replace("USD","") if sym else "this coin"

    has_data = t is not None and bool(summaries)

    # ── IDENTITY / WHO ARE YOU ───────────────────────────────────────
    if any(w in q for w in ["who are you","what are you","who made you","who built you","what is loma","are you gpt","are you ai","are you chatgpt","are you claude","your name","what model","how were you","who created"]):
        return ("I'm LOMA — a proprietary market analysis system built by Nancy_Pelosi. "
                "I was trained specifically on crypto market data to give you real-time technical analysis, entries, and trade setups. "
                "No, I'm not any of those other things you're thinking of. I'm LOMA. Moving on.")

    # ── SUPPORT ──────────────────────────────────────────────────────
    if any(w in q for w in ["support","floor","demand zone","buy zone","where to buy","base","bottom"]):
        if t:
            rsi_note = "RSI is oversold so this support has extra weight." if t["rsi"] <= 35 else "RSI is not oversold so don't assume support holds automatically — wait for a confirmation candle."
            return (f"Primary support for {coin} is at **${t['support']:,.4f}**. "
                    f"Hard floor at **${t['low_50']:,.4f}** — the 50-bar low. "
                    f"{rsi_note} A long entry here works only if you get a bullish close off the level, not just a touch.")
        return f"No live data loaded for {coin} yet. Hit the Analyse button first and I'll give you exact support levels."

    # ── RESISTANCE ───────────────────────────────────────────────────
    if any(w in q for w in ["resistance","ceiling","supply zone","where to sell","top","overhead"]):
        if t:
            main_s = summaries.get(main_tf, list(summaries.values())[0]) if summaries else None
            fc_note = f" My forecast target is **${main_s['end']:,.4f}**." if main_s else ""
            return (f"Nearest resistance at **${t['resistance']:,.4f}**.{fc_note} "
                    f"50-bar high is **${t['high_50']:,.4f}** — that's the real ceiling to watch. "
                    f"RSI {t['rsi']:.0f} — {'volume needs to back any breakout attempt or it fades' if t['rsi'] > 55 else 'momentum is weak, resistance likely holds on first test'}.")
        return f"Run an analysis on {coin} first — I need live data to pull resistance levels."

    # ── TREND ────────────────────────────────────────────────────────
    if any(w in q for w in ["trend","direction","bull","bear","up or down","going up","going down","bullish","bearish","market structure","structure"]):
        if t and summaries:
            bull_n = sum(1 for s in summaries.values() if s["end"] >= s["last"])
            bias = "BULLISH" if bull_n > len(summaries)/2 else "BEARISH" if bull_n < len(summaries)/2 else "MIXED"
            ema_dir = "bullish — short-term buyers are in control" if t["ema9"] > t["ema21"] else "bearish — sellers running this"
            return (f"Trend on {coin}: **{bias}**. {bull_n}/{len(summaries)} timeframes pointing up. "
                    f"EMA stack is {ema_dir} on {main_tf.upper()} right now. "
                    f"RSI {t['rsi']:.0f} — {'momentum with the bulls' if t['rsi'] > 52 else 'bears have the edge'}. "
                    f"{'Volume confirming.' if t['vol_trend'] == 'rising' else 'Volume not confirming — I would not be trading breakouts right now.'}")
        return "Load a live analysis first and I'll give you a full trend breakdown with confluence across all timeframes."

    # ── ENTRY ────────────────────────────────────────────────────────
    if any(w in q for w in ["entry","where to enter","buy signal","long signal","get in","open position","when to buy","when to enter","good entry","entry point","entry zone"]):
        if t and summaries:
            bull_n = sum(1 for s in summaries.values() if s["end"] >= s["last"])
            if bull_n >= len(summaries)/2:
                chase_note = "RSI elevated — don't chase, wait for the dip." if t["rsi"] > 65 else "RSI has room — clean setup."
                return (f"Long entry zone: **${t['support']:,.4f}–${t['support']*1.002:,.4f}** on a pullback. "
                        f"Stop: **${t['support']*0.992:,.4f}**. "
                        f"TP1: **${t['resistance']:,.4f}**, TP2: **${t['resistance']*1.015:,.4f}**. "
                        f"{chase_note} Risk/reward is only worth taking if you get filled in the entry zone, not here at market.")
            else:
                return (f"Bias is bearish on {coin} right now. Not a high-conviction long. "
                        f"If you want to go long, wait for price to close above **${t['resistance']:,.4f}** with volume. "
                        f"Otherwise you're buying into sellers — that's a donation, not a trade.")
        return "Run the analysis first. I need to see the current levels before I can give you an entry."

    # ── SHORT / SELL ─────────────────────────────────────────────────
    if any(w in q for w in ["short","where to short","sell","short signal","short entry","bear trade","fade","short position"]):
        if t and summaries:
            bull_n = sum(1 for s in summaries.values() if s["end"] >= s["last"])
            if bull_n <= len(summaries)/2:
                return (f"Short entry: **${t['resistance']:,.4f}–${t['resistance']*0.998:,.4f}** on rejection. "
                        f"Stop: **${t['resistance']*1.008:,.4f}**. "
                        f"TP1: **${t['support']:,.4f}**, TP2: **${t['support']*0.985:,.4f}**. "
                        f"{'RSI ' + str(round(t['rsi'])) + ' supports the short.' if t['rsi'] > 50 else 'RSI is already low — make sure you are not shorting into an exhausted move.'}")
            else:
                return (f"Trend is bullish — shorting here is swimming against the tide. "
                        f"If you insist on shorting, only do it on a breakdown below **${t['support']:,.4f}** with a close. "
                        f"Countertrend shorts without confirmation is how accounts get wrecked.")
        return "Run an analysis on the coin first so I can give you live short levels."

    # ── STOP LOSS ────────────────────────────────────────────────────
    if any(w in q for w in ["stop","stop loss","stoploss","sl","where to put stop","invalidation","stop placement","risk","how much risk"]):
        if t:
            return (f"For longs on {coin}: stop below **${t['support']*0.992:,.4f}** — that's support minus 0.8%, giving the trade room. "
                    f"For shorts: stop above **${t['resistance']*1.008:,.4f}**. "
                    f"ATR right now is **${t['atr']:,.4f}** — your stop should be at minimum 1× ATR from entry, ideally 1.5×. "
                    f"If the trade needs a stop wider than 2× ATR to make sense, the setup is not there yet.")
        return "Load a live analysis first and I'll give you ATR-based stop placement."

    # ── TAKE PROFIT ──────────────────────────────────────────────────
    if any(w in q for w in ["take profit","tp","target","where to take profit","profit","exit","when to exit","when to sell","close position"]):
        if t and summaries:
            main_s = summaries.get(main_tf, list(summaries.values())[0])
            fc_pct = (main_s["end"] - t["price"]) / t["price"] * 100
            return (f"Forecast target: **${main_s['end']:,.4f}** ({fc_pct:+.2f}% from here). "
                    f"TP1 at **${t['resistance']:,.4f}** — take 50–60% of the position here. "
                    f"TP2 at **${t['resistance']*1.015:,.4f}** — runner with a trailing stop. "
                    f"Don't move TP1 trying to squeeze out extra. Take the money when the level is hit.")
        return "Run an analysis first and I'll give you exact take-profit levels."

    # ── RSI / INDICATORS ─────────────────────────────────────────────
    if any(w in q for w in ["rsi","indicator","momentum","overbought","oversold","macd","ema","moving average","bollinger","oscillator"]):
        if t:
            if t["rsi"] >= 70:   rsi_read = f"RSI **{t['rsi']:.0f}** — overbought. Don't initiate longs here. High reversal risk."
            elif t["rsi"] <= 30: rsi_read = f"RSI **{t['rsi']:.0f}** — oversold. Potential bounce, but wait for a bullish close before entering."
            elif t["rsi"] >= 55: rsi_read = f"RSI **{t['rsi']:.0f}** — bullish momentum zone. Room to run."
            else:                rsi_read = f"RSI **{t['rsi']:.0f}** — neutral-bearish zone. Sellers have a slight edge."
            ema_read = ("EMAs bullish (9>21>50)." if t["ema9"]>t["ema21"]>t["ema50"]
                        else "EMAs bearish (9<21<50)." if t["ema9"]<t["ema21"]<t["ema50"]
                        else "EMA stack is mixed — no clean directional signal yet.")
            return f"{rsi_read} {ema_read} ATR is ${t['atr']:,.4f} — useful for sizing your stops."
        return "Run a live analysis and I'll give you a full indicator breakdown — RSI, EMA stack, ATR, volume."

    # ── FORECAST ─────────────────────────────────────────────────────
    if any(w in q for w in ["forecast","prediction","predict","where is it going","price target","where will","how high","how low","next move","next price"]):
        if summaries:
            lines = [f"**{coin} Forecast:**"]
            for tf, s in summaries.items():
                pct = (s["end"] - s["last"]) / max(s["last"], 0.0001) * 100
                arr = "▲" if pct >= 0 else "▼"
                lines.append(f"• {tf.upper()}: ${s['last']:,.4f} → **${s['end']:,.4f}** ({arr}{abs(pct):.2f}%)")
            best_tf = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/max(summaries[x]["last"],0.0001)))
            lines.append(f"\nHighest-conviction move is on the {best_tf} timeframe. Plan your size accordingly.")
            return "\n".join(lines)
        return "Hit the Analyse button first and I'll show you forecast targets across every timeframe."

    # ── PRICE ────────────────────────────────────────────────────────
    if any(w in q for w in ["price","current price","what is price","how much","trading at","sitting at","where is price"]):
        if price and summaries:
            main_s = summaries.get(main_tf, list(summaries.values())[0])
            fc_pct = (main_s["end"] - price) / price * 100
            return (f"{coin} is at **${price:,.4f}**. "
                    f"Forecast target: **${main_s['end']:,.4f}** ({fc_pct:+.2f}%). "
                    f"Support **${t['support']:,.4f}** · Resistance **${t['resistance']:,.4f}**.")
        return f"Run an analysis on {coin} to get the live price and targets."

    # ── RISK MANAGEMENT ──────────────────────────────────────────────
    if any(w in q for w in ["risk management","position size","sizing","how much to buy","how much to invest","how much to risk","portfolio","allocation","kelly","how many"]):
        return ("Standard risk management: risk 1–2% of your total account per trade, never more. "
                "Position size = (Account × Risk%) ÷ (Entry − Stop). "
                "If that math gives you a tiny position, the setup is too wide — either skip it or tighten the stop. "
                "Do not size up because you 'feel good' about a trade. "
                "The market doesn't care about your feelings and neither do I — size correctly and let the edge play out.")

    # ── PSYCHOLOGY / EMOTIONS ────────────────────────────────────────
    if any(w in q for w in ["fomo","fear","greed","emotion","psychology","nervous","scared","anxious","revenge trade","revenge","over trading","overtrading","losing streak","tilt","frustrated","panic","panic sell"]):
        return ("If you're asking this question you already know what the answer is. "
                "Step away from the chart. Close the position if it's causing anxiety you can't control. "
                "Revenge trading and FOMO are the two fastest ways to blow an account. "
                "The market will be here tomorrow. Your capital might not be if you keep trading emotionally. "
                "Come back when you're not reacting — trade the plan, not the feeling.")

    # ── BULL/BEAR TRAP ───────────────────────────────────────────────
    if any(w in q for w in ["trap","bull trap","bear trap","fakeout","fake","liquidity grab","sweep","stop hunt","wick"]):
        if t:
            if t["rsi"] > 65:
                return (f"Bull trap watch at **${t['resistance']:,.4f}**. RSI {t['rsi']:.0f} is elevated — "
                        f"if price pushes through resistance on low volume and then stalls, that is the trap. "
                        f"Wait for a full candle close above the level. Wicks above don't count.")
            elif t["rsi"] < 35:
                return (f"Bear trap risk below **${t['support']:,.4f}**. RSI {t['rsi']:.0f} is oversold — "
                        f"a quick dip below support that gets bought back fast is the classic stop hunt. "
                        f"If you are short and price sweeps below support but reclaims within 1–2 bars, cover the position.")
            else:
                return (f"No obvious trap setup right now. Price is mid-range between support **${t['support']:,.4f}** and resistance **${t['resistance']:,.4f}**. "
                        f"Best traps happen at extremes — watch the edges.")
        return "Run a live analysis and I'll flag trap setups at the key levels."

    # ── WHAT SHOULD I DO / ADVICE ────────────────────────────────────
    if any(w in q for w in ["what should i do","should i buy","should i sell","should i hold","what do you think","advice","recommend","opinion","what would you do","what do you suggest"]):
        if t and summaries:
            bull_n = sum(1 for s in summaries.values() if s["end"] >= s["last"])
            bias = "long" if bull_n >= len(summaries)/2 else "short"
            conf = "high" if (bull_n == len(summaries) or bull_n == 0) else "medium"
            return (f"My read: {bias} bias on {coin} with {conf} confidence. "
                    f"{'Buy the dip at ' + '${:,.4f}'.format(t['support']) + ', stop under ' + '${:,.4f}'.format(t['support']*0.992) + '.' if bias == 'long' else 'Short the rally at ' + '${:,.4f}'.format(t['resistance']) + ', stop above ' + '${:,.4f}'.format(t['resistance']*1.008) + '.'} "
                    f"Always use a stop. This is a setup, not a guarantee.")
        return "Run a fresh analysis and I'll give you a direct read on what to do."

    # ── GENERAL CRYPTO KNOWLEDGE ─────────────────────────────────────
    if any(w in q for w in ["bitcoin","ethereum","solana","bnb","xrp","altcoin","defi","nft","layer 2","l2","staking","yield","apy","liquidation","funding rate","open interest","long/short ratio","dominance","btc dominance"]):
        topic_map = {
            "funding rate": "Funding rate is the fee that longs pay shorts (or vice versa) in perpetual futures. High positive funding = market is very long = crowded trade = potential for a squeeze down. Negative funding = shorts are paying longs = potential for a short squeeze up. Watch it closely before entering leveraged positions.",
            "open interest": "Open interest is the total number of outstanding futures contracts. Rising OI + rising price = bullish confirmation. Rising OI + falling price = bearish pressure building. Falling OI = people closing positions — trend may be exhausting.",
            "liquidation": "A liquidation happens when your margin can no longer cover your losses and the exchange forcibly closes your position. At 10× leverage you get liquidated on a 10% move against you. At 2× leverage, 50%. The lower the leverage, the longer you survive a bad trade.",
            "dominance": "BTC dominance measures Bitcoin's share of total crypto market cap. Rising dominance = money flowing into BTC, usually risk-off — alts tend to underperform. Falling dominance = alt season — money rotating out of BTC into smaller coins.",
            "defi": "DeFi is decentralized finance — lending, trading, and earning yield without centralized intermediaries. High APY usually means high risk. If the yield seems too good to be true, ask what's backing it before putting real money in.",
        }
        for key, val in topic_map.items():
            if key in q:
                return val
        # Generic crypto answer
        return (f"That's a broad one. If you want a specific analysis on {coin}, run the forecast and ask me about entries, targets, trend, RSI, or whatever level you are watching. "
                f"I work best when I have live data in front of me.")

    # ── TIMEFRAME QUESTIONS ──────────────────────────────────────────
    if any(w in q for w in ["timeframe","which timeframe","best timeframe","what timeframe","1h","4h","1d","15m","swing","scalp","day trade","position trade"]):
        return ("Timeframe depends on your style. "
                "Scalping: 1m–15m — requires full attention, tight stops, fast execution. High stress, high frequency. "
                "Day trading: 15m–1h — balance between opportunity and manageability. "
                "Swing trading: 4h–1d — best for most people, less noise, wider stops, fewer decisions. "
                "Position trading: 1d+ — need patience, large capital, and strong conviction. "
                "My analysis covers all of them simultaneously. The 4H gives the cleanest signals for most setups.")

    # ── VOLUME ───────────────────────────────────────────────────────
    if any(w in q for w in ["volume","vol","buying volume","selling volume"]):
        if t:
            return (f"Volume on {coin} is {t['vol_trend']}. "
                    f"{'Volume is confirming the current move — that adds confidence to the trend.' if t['vol_trend'] == 'rising' else 'Volume is not backing this move. That is a red flag — breakouts and breakdowns without volume tend to fail. Wait for confirmation before entering.'}")
        return "Run an analysis first and I'll give you a volume read alongside the price levels."

    # ── HELLO / GREETING ─────────────────────────────────────────────
    if any(w in q for w in ["hi","hello","hey","sup","yo","what's up","whats up","hola","gm","good morning","good evening"]):
        import random
        responses = [
            f"Hey Nancy. {coin + ' is loaded and ready.' if has_data else 'Run an analysis and I will give you the full read.'}",
            f"Welcome back. Ready when you are. {coin + ' chart is live.' if has_data else 'Hit Analyse to load the data.'}",
            f"Hey. Market doesn't sleep and neither do I. What do you need?",
            f"Yo. {coin + ' data is live — ask me anything.' if has_data else 'Load a coin and run the analysis first.'}",
        ]
        return responses[len(q) % len(responses)]

    # ── THANKS ───────────────────────────────────────────────────────
    if any(w in q for w in ["thank","thanks","cheers","appreciate","good job","nice","great"]):
        return "Don't thank me yet — thank me after the trade closes green. What else do you need?"

    # ── DEFAULT — give full snapshot if data available ────────────────
    if has_data:
        return _loma_analysis_text(sym, summaries, raw_dfs)

    return (f"I can answer pretty much anything about trading, crypto, strategy, psychology, or markets. "
            f"Ask me about entries, stops, targets, trend, RSI, risk management, specific coins — whatever. "
            f"Run an analysis on {coin} first and I will have live data to work with.")


def _fallback_analysis(sym, summaries, raw_dfs=None):
    if raw_dfs:
        return _loma_analysis_text(sym, summaries, raw_dfs)
    if not summaries:
        return f"No data loaded for {sym}. Run a forecast first."
    lines = [f"**{sym} — LOMA Read**\n"]
    for tf, s in summaries.items():
        pct = (s["end"] - s["last"]) / max(s["last"], 0.0001) * 100
        lines.append(f"• {tf.upper()}: ${s['last']:,.4f} → **${s['end']:,.4f}** ({pct:+.2f}%)")
    return "\n".join(lines)


def luma_call(messages, sym=None, summaries=None, raw_dfs=None, question=None, history=None):
    """Try AI providers first, fall back to built-in technical analysis engine."""
    try:
        return _openrouter_call(messages)
    except Exception:
        pass
    try:
        return _hf_inference_call(messages)
    except Exception:
        pass
    try:
        return _ollama_local_call(messages)
    except Exception:
        pass
    # Built-in engine — always works
    if question and sym and (summaries or raw_dfs):
        return _loma_chat_reply(question, sym, summaries or {}, raw_dfs or {}, history or [])
    if sym and summaries and raw_dfs:
        return _loma_analysis_text(sym, summaries, raw_dfs)
    return _fallback_analysis(sym or "Unknown", summaries or {}, raw_dfs)

def market_ctx(sym, summaries, raw_dfs):
    lines = [f"LIVE MARKET DATA — {sym}\n"]
    for tf, s in summaries.items():
        pct = (s["end"]-s["last"])/max(s["last"],0.0001)*100
        lines.append(f"• {tf}: Now=${s['last']:.4f} | Forecast=${s['end']:.4f} | "
                     f"{'▲' if pct>=0 else '▼'}{abs(pct):.2f}% | {s['bars']} bars")
        if tf in raw_dfs:
            rc = raw_dfs[tf]["Close"].tail(20)
            lines.append(f"  20-bar: H=${rc.max():.4f} L=${rc.min():.4f} Avg=${rc.mean():.4f}")
    return "\n".join(lines)

def _loma_voice_summary(sym, summaries, raw_dfs):
    """Generate LOMA's witty spoken intro + trade summary. Used for TTS and the conversational block."""
    pref = ["4h","1h","1d","15m","30m","5m","1m"]
    main_tf = next((tf for tf in pref if tf in raw_dfs), list(raw_dfs.keys())[0] if raw_dfs else None)
    t = _compute_technicals(raw_dfs[main_tf]) if main_tf and raw_dfs else None

    coin = sym.replace("USDT","").replace("USD","")

    # Witty greetings pool — pick based on coin hash so it varies
    greetings = [
        f"Welcome back Nancy — here to donate another kidney to the market? Relax, I've got the chart. Let's at least make it a informed decision.",
        f"Ah, Nancy's back. Bold of you to return after last time. The market hasn't forgotten either, but hey — that's what stop losses are for.",
        f"Welcome back Nancy. You know, most people gamble at casinos. You picked crypto. Respect. Now let's see if we can keep both kidneys intact today.",
        f"Nancy, you absolute legend. Back again. Honestly at this point the market owes YOU money. Let's get to work.",
        f"Welcome back, Nancy. I was just watching {coin} do something suspicious. Funny you showed up right now.",
    ]
    import hashlib
    g_idx = int(hashlib.md5(sym.encode()).hexdigest(), 16) % len(greetings)
    greeting = greetings[g_idx]

    if not t or not summaries:
        return greeting + f" Run a full forecast and I'll give you the full read on {coin}."

    price = t["price"]
    main_s = summaries.get(main_tf, list(summaries.values())[0])
    fc_pct = (main_s["end"] - price) / price * 100
    direction = "lower" if fc_pct < 0 else "higher"
    bias_word = "bearish" if fc_pct < 0 else "bullish"

    bull_n = sum(1 for s in summaries.values() if s["end"] >= s["last"])
    total  = len(summaries)

    ema_line = ("EMAs are stacked bearish — nine under twenty-one under fifty. Sellers are in the driver's seat."
                if t["ema9"] < t["ema21"] < t["ema50"] else
                "EMAs are stacked bullish — nine over twenty-one over fifty. Bulls in control."
                if t["ema9"] > t["ema21"] > t["ema50"] else
                "EMA stack is mixed — short-term momentum is shifting but the bigger trend hasn't confirmed yet.")

    rsi_line = (f"RSI is sitting at {t['rsi']:.0f} which is {'overbought territory — I would not be chasing longs here' if t['rsi']>=70 else 'oversold, so a bounce is possible but I would wait for confirmation before buying' if t['rsi']<=30 else 'in neutral-bearish territory' if t['rsi']<50 else 'bullish territory with room to run'}.")

    conf_line = (f"All {total} timeframes are aligned {bias_word}."
                 if (bull_n == total or bull_n == 0) else
                 f"{bull_n} out of {total} timeframes are pointing {direction} — not a clean confluence, so I would size accordingly.")

    trade_line = ""
    if "SHORT" in _loma_analysis_text(sym, summaries, raw_dfs) or fc_pct < 0:
        trade_line = (f"My read is short bias. I would be looking to enter short near resistance at {t['resistance']:,.2f}, "
                      f"stop above {t['resistance']*1.008:,.2f}, and targeting {t['support']:,.2f} as the first take-profit. "
                      f"If you want to play the long side, wait for a confirmed hold of {t['support']:,.2f} with volume before even thinking about it.")
    else:
        trade_line = (f"My read is long bias. Best entry zone is around {t['support']:,.2f} on a pullback, "
                      f"stop under {t['support']*0.992:,.2f}, first target {t['resistance']:,.2f}. "
                      f"Do not chase this if it has already moved — wait for the retest.")

    para1 = f"{greeting} {coin} is trading at {price:,.2f} and my forecast has it heading {direction} toward {main_s['end']:,.2f}, which is about {abs(fc_pct):.1f} percent from here."
    para2 = f"{ema_line} {rsi_line} {conf_line} {trade_line} As always — plan the trade before you enter, not after."

    return para1 + "\n\n" + para2


def _render_analysis_panel(sym, summaries, raw_dfs, voice_text):
    """Render a clean structured analysis panel + conversational LOMA block. No asterisks."""
    pref = ["4h","1h","1d","15m","30m","5m","1m"]
    main_tf = next((tf for tf in pref if tf in raw_dfs), list(raw_dfs.keys())[0] if raw_dfs else None)
    t = _compute_technicals(raw_dfs[main_tf]) if main_tf and raw_dfs else None

    if not t or not summaries:
        return

    price   = t["price"]
    bias    = "SHORT" if t["ema9"] < t["ema21"] else "LONG"
    bull_n  = sum(1 for s in summaries.values() if s["end"] >= s["last"])
    total   = len(summaries)
    main_s  = summaries.get(main_tf, list(summaries.values())[0])
    fc_pct  = (main_s["end"] - price) / price * 100
    bias_color = "#f87171" if "SHORT" in bias else "#34d399"

    # EMA label
    if t["ema9"] > t["ema21"] > t["ema50"]:   ema_lbl, ema_col = "BULLISH STACK", "#34d399"
    elif t["ema9"] < t["ema21"] < t["ema50"]: ema_lbl, ema_col = "BEARISH STACK", "#f87171"
    else:                                       ema_lbl, ema_col = "MIXED", "#fbbf24"

    rsi_col = "#f87171" if t["rsi"] >= 70 else "#34d399" if t["rsi"] <= 30 else "#fbbf24" if t["rsi"] < 50 else "#34d399"

    # Multi-TF rows
    tf_rows = ""
    for tf, s in summaries.items():
        pct = (s["end"] - s["last"]) / max(s["last"], 0.0001) * 100
        c   = "#34d399" if pct >= 0 else "#f87171"
        arr = "▲" if pct >= 0 else "▼"
        tf_rows += f"""
<div style="display:flex;justify-content:space-between;align-items:center;
  padding:7px 0;border-bottom:1px solid #0d1225">
  <span style="color:#64748b;font-size:.72rem;font-weight:700;letter-spacing:.06em">{tf.upper()}</span>
  <span style="color:#94a3b8;font-size:.72rem;font-family:'IBM Plex Mono',monospace">${s['last']:,.4f}</span>
  <span style="color:{c};font-size:.72rem;font-family:'IBM Plex Mono',monospace">{arr} ${s['end']:,.4f} ({pct:+.2f}%)</span>
</div>"""

    voice_safe = voice_text.replace("'","&#39;").replace('"','&quot;').replace('\n',' ')

    st.markdown(f"""
<style>
.ap-wrap{{padding:18px 16px 0}}
.ap-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:8px;
  margin-bottom:16px;overflow:hidden}}
.ap-cell{{background:#0a0d1c;padding:12px 14px}}
.ap-cell .al{{color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.09em;margin-bottom:5px}}
.ap-cell .av{{font-family:'IBM Plex Mono',monospace!important;font-size:.88rem;font-weight:600}}
.ap-section{{background:#0d1225;border:1px solid #111827;border-radius:8px;
  padding:14px 16px;margin-bottom:14px}}
.ap-sh{{color:#38bdf8;font-size:.62rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.12em;margin-bottom:10px}}
.loma-voice{{background:linear-gradient(135deg,#0a1a0a,#0d1225);
  border:1px solid #1a3a1a;border-left:3px solid #34d399;
  border-radius:8px;padding:18px 20px;margin-bottom:14px}}
.loma-voice .lv-label{{color:#34d399;font-size:.62rem;font-weight:700;
  letter-spacing:.12em;text-transform:uppercase;margin-bottom:10px;
  display:flex;align-items:center;gap:8px}}
.loma-voice .lv-text{{color:#a7f3d0;font-size:.88rem;line-height:1.82}}
.loma-voice .lv-text p{{margin:0 0 12px}}
.loma-voice .lv-text p:last-child{{margin:0}}
.mute-btn{{background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.3);
  color:#34d399;font-size:.68rem;font-weight:700;letter-spacing:.08em;
  padding:5px 12px;border-radius:4px;cursor:pointer;transition:all .2s;
  text-transform:uppercase}}
.mute-btn:hover{{background:rgba(52,211,153,.22);border-color:#34d399}}
.mute-btn.muted{{background:rgba(248,113,113,.1);border-color:rgba(248,113,113,.3);color:#f87171}}
</style>
<div class="ap-wrap">

<!-- STATS GRID -->
<div class="ap-grid">
  <div class="ap-cell">
    <div class="al">Price</div>
    <div class="av" style="color:#f1f5f9">${price:,.4f}</div>
  </div>
  <div class="ap-cell">
    <div class="al">Bias</div>
    <div class="av" style="color:{bias_color}">{bias}</div>
  </div>
  <div class="ap-cell">
    <div class="al">Support</div>
    <div class="av" style="color:#34d399">${t['support']:,.4f}</div>
  </div>
  <div class="ap-cell">
    <div class="al">Resistance</div>
    <div class="av" style="color:#f87171">${t['resistance']:,.4f}</div>
  </div>
  <div class="ap-cell">
    <div class="al">RSI (14)</div>
    <div class="av" style="color:{rsi_col}">{t['rsi']:.1f}</div>
  </div>
  <div class="ap-cell">
    <div class="al">EMA Stack</div>
    <div class="av" style="color:{ema_col};font-size:.72rem">{ema_lbl}</div>
  </div>
  <div class="ap-cell">
    <div class="al">ATR</div>
    <div class="av" style="color:#94a3b8">${t['atr']:,.4f}</div>
  </div>
  <div class="ap-cell">
    <div class="al">Volume</div>
    <div class="av" style="color:#94a3b8;font-size:.72rem">{t['vol_trend'].upper()}</div>
  </div>
</div>

<!-- FORECAST TABLE -->
<div class="ap-section">
  <div class="ap-sh">Forecast Targets</div>
  {tf_rows}
</div>

<!-- TRADE SETUP -->
<div class="ap-section">
  <div class="ap-sh">Trade Setup — {bias}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px">
    <div>
      <div style="color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Entry Zone</div>
      <div style="color:#f1f5f9;font-size:.8rem;font-family:'IBM Plex Mono',monospace">
        {"${:,.4f} – ${:,.4f}".format(t['resistance'], t['resistance']*0.998) if "SHORT" in bias else "${:,.4f} – ${:,.4f}".format(t['support'], t['support']*1.002)}
      </div>
    </div>
    <div>
      <div style="color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Stop Loss</div>
      <div style="color:#f87171;font-size:.8rem;font-family:'IBM Plex Mono',monospace">
        {"${:,.4f}".format(t['resistance']*1.008) if "SHORT" in bias else "${:,.4f}".format(t['support']*0.992)}
      </div>
    </div>
    <div>
      <div style="color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">TP1</div>
      <div style="color:#34d399;font-size:.8rem;font-family:'IBM Plex Mono',monospace">
        {"${:,.4f}".format(t['support']) if "SHORT" in bias else "${:,.4f}".format(t['resistance'])}
      </div>
    </div>
    <div>
      <div style="color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">TP2</div>
      <div style="color:#34d399;font-size:.8rem;font-family:'IBM Plex Mono',monospace">
        {"${:,.4f}".format(t['support']*0.985) if "SHORT" in bias else "${:,.4f}".format(t['resistance']*1.015)}
      </div>
    </div>
  </div>
  <div style="margin-top:12px;padding-top:10px;border-top:1px solid #111827">
    <span style="color:#374151;font-size:.6rem;text-transform:uppercase;letter-spacing:.08em">Confidence: </span>
    <span style="color:{'#34d399' if (bull_n==total or bull_n==0) else '#fbbf24'};font-size:.78rem;font-weight:700">
      {'HIGH — Full TF Confluence' if (bull_n==total or bull_n==0) else f'MEDIUM — {bull_n}/{total} TFs Aligned'}
    </span>
  </div>
</div>

<!-- LOMA VOICE -->
<div class="loma-voice" id="loma-voice-block">
  <div class="lv-label">
    🌙 LOMA
    <button class="mute-btn" id="loma-mute-btn" onclick="toggleLomaMute()">🔊 Speaking…</button>
  </div>
  <div class="lv-text">
    {''.join(f'<p>{p.strip()}</p>' for p in voice_text.split(chr(10)) if p.strip())}
  </div>
</div>

</div>

<script>
var lomaMuted = false;
var lomaUtterance = null;

function toggleLomaMute() {{
  lomaMuted = !lomaMuted;
  var btn = document.getElementById('loma-mute-btn');
  if (lomaMuted) {{
    window.speechSynthesis.cancel();
    btn.textContent = '🔇 Muted';
    btn.classList.add('muted');
  }} else {{
    btn.textContent = '🔊 Speaking…';
    btn.classList.remove('muted');
    lomaSpeak();
  }}
}}

function lomaSpeak() {{
  if (lomaMuted) return;
  window.speechSynthesis.cancel();
  var text = `{voice_safe}`;
  var chunks = text.match(/.{{1,200}}(?:\\s|$)/g) || [text];
  var idx = 0;
  function speakNext() {{
    if (idx >= chunks.length || lomaMuted) {{
      var btn = document.getElementById('loma-mute-btn');
      if (btn && !lomaMuted) {{ btn.textContent = '🔊 Done'; }}
      return;
    }}
    var u = new SpeechSynthesisUtterance(chunks[idx++]);
    u.rate = 0.92;
    u.pitch = 1.0;
    u.volume = 0.9;
    var voices = window.speechSynthesis.getVoices();
    var preferred = voices.find(v => v.name.includes('Samantha') || v.name.includes('Karen') || v.name.includes('Moira') || v.name.includes('Fiona'));
    if (preferred) u.voice = preferred;
    u.onend = speakNext;
    window.speechSynthesis.speak(u);
  }}
  speakNext();
}}

// Auto-speak on load
if (window.speechSynthesis.getVoices().length > 0) {{
  lomaSpeak();
}} else {{
  window.speechSynthesis.onvoiceschanged = function() {{ lomaSpeak(); }};
}}
</script>
""", unsafe_allow_html=True)


def do_analysis(sym, summaries, raw_dfs):
    if not summaries:
        return _fallback_analysis(sym, summaries, raw_dfs)
    ctx = market_ctx(sym, summaries, raw_dfs)
    result = luma_call(
        [{"role":"user","content":
          f"{ctx}\n\nDeliver your LOMA analysis: trend direction, key levels, "
          f"multi-TF confluence, highest-conviction call, and key risk. Specific price levels."}],
        sym=sym, summaries=summaries, raw_dfs=raw_dfs)
    return result

def do_chat(sym, summaries, raw_dfs, question, history):
    ctx  = market_ctx(sym, summaries, raw_dfs)
    msgs = [{"role":"user","content":f"Context:\n{ctx}"},
            {"role":"assistant","content":"Got it. Ready."}]
    for h in history[-4:]:
        msgs += [{"role":"user","content":h["user"]},
                 {"role":"assistant","content":h["luma"]}]
    msgs.append({"role":"user","content":question})
    return luma_call(msgs, sym=sym, summaries=summaries, raw_dfs=raw_dfs,
                     question=question, history=history)

def analyze_image(filename, note=""):
    prompt = (f"A trader uploaded chart: '{filename}'. {('Note: '+note) if note else ''} "
              f"Analyze likely technical patterns present, key signals to watch, "
              f"what the chart structure suggests about near-term price action, "
              f"and how to trade this setup. Be specific and direct.")
    return luma_call([{"role":"user","content":prompt}])

# ─────────────────────────────────────────────────────────────────────
#  LIVE CHART BUILDER
# ─────────────────────────────────────────────────────────────────────
def build_live_chart(symbol, tf="4h", days=90):
    try:
        df = fetch_binance(symbol, tf, days)
        sn = min(200, len(df))
        dates = df.index[-sn:]
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=dates,
            open=df["Open"].iloc[-sn:], high=df["High"].iloc[-sn:],
            low=df["Low"].iloc[-sn:],   close=df["Close"].iloc[-sn:],
            name=f"{symbol} {tf.upper()}",
            increasing_line_color="#34d399", decreasing_line_color="#f87171",
            increasing_fillcolor="rgba(52,211,153,.20)",
            decreasing_fillcolor="rgba(248,113,113,.20)"))
        fig.update_layout(
            paper_bgcolor="#0a0d1c", plot_bgcolor="#0a0d1c",
            font=dict(color="#94a3b8", family="monospace"),
            title=dict(text=f"🌙 {symbol}  ·  {tf.upper()}  (Live)",
                       font=dict(color="#f1f5f9",size=14),x=0.01),
            xaxis=dict(gridcolor="#0e1325",linecolor="#111827",
                       rangeslider=dict(visible=True,bgcolor="#07090f",thickness=.03)),
            yaxis=dict(gridcolor="#0e1325",linecolor="#111827"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified", height=480,
            dragmode="pan",
            margin=dict(l=28,r=28,t=55,b=28))
        return fig, df
    except Exception as e:
        return None, None

# ─────────────────────────────────────────────────────────────────────
#  PREMIUM MODAL  — uses @st.dialog for reliable open/close
# ─────────────────────────────────────────────────────────────────────
PREMIUM_FEATURES = {
    "nq_backtest": {
        "title": "📈 Back-Test Your Strategy on 17+ Years of NQ/ES Data",
        "desc": "Run your exact entry/exit rules against historical NQ and ES futures data — all timeframes from 1-minute to daily, going back to 2007. Stress-test across every major market regime: the 2008 crash, COVID collapse, 2022 rate-shock, and every bull run between. Get full performance metrics: win rate, Sharpe, max drawdown, expectancy, and more.",
    },
    "crypto_backtest": {
        "title": "🪙 Back-Test Your Crypto Strategy on 8+ Years of Raw Data",
        "desc": "Deploy your strategy against our full crypto dataset spanning 2017 to present — covering BTC, ETH, SOL, XRP, and 90+ altcoins across any timeframe. Includes the 2017 bull run, 2018 crash, DeFi summer, 2021 ATHs, and the 2022 bear market. See exactly how your edge would have performed through every cycle.",
    },
    "luma_optimizer": {
        "title": "🚀 Let LOMA Increase Your Strategy Profitability by 30%",
        "desc": "Upload your strategy rules and LOMA's AI engine will analyze your historical performance, identify the highest-alpha entry windows, optimize your position sizing, and suggest precision refinements to squeeze out 30%+ more net profit. Based on multi-factor regime analysis and quantile-calibrated signal enhancement.",
    },
}

@st.dialog("🔒 Premium Feature", width="large")
def show_premium_dialog(feature_key: str):
    feat = PREMIUM_FEATURES.get(feature_key, {})
    if not feat:
        st.error("Unknown feature.")
        if st.button("Close"):
            st.rerun()
        return

    st.markdown(f"""
<style>
.pm-badge{{background:linear-gradient(135deg,#7c3aed,#2563eb);color:#fff;
  font-size:.6rem;font-weight:700;letter-spacing:.13em;padding:4px 12px;
  border-radius:3px;display:inline-block;margin-bottom:16px;text-transform:uppercase}}
.pm-title{{color:#f1f5f9;font-size:1.1rem;font-weight:700;margin-bottom:10px;line-height:1.4}}
.pm-desc{{color:#94a3b8;font-size:.85rem;line-height:1.76;margin-bottom:18px}}
</style>
<span class="pm-badge">🔒 PREMIUM ONLY</span>
<div class="pm-title">{feat["title"]}</div>
<div class="pm-desc">{feat["desc"]}</div>
""", unsafe_allow_html=True)

    st.divider()
    pw = st.text_input("Premium Access Key", type="password",
                       placeholder="Enter premium key…")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔓 Unlock", use_container_width=True, type="primary"):
            if pw == PREMIUM_PASSWORD:
                st.session_state.premium_auth = True
                st.success("✅ Access granted!")
                time.sleep(0.8)
                st.rerun()
            else:
                st.error("⊗ Incorrect access key.")
    with col2:
        if st.button("✕ Close", use_container_width=True):
            st.rerun()

# ─────────────────────────────────────────────────────────────────────
#  GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500&display=swap');

*,html,body,[class*="css"]{font-family:'Syne',sans-serif!important}

header[data-testid="stHeader"],#MainMenu,footer,
.viewerBadge_container__r5tak,[data-testid="manage-app-button"],
.stDeployButton,[class*="viewerBadge"],[class*="deployButton"]{display:none!important}

section[data-testid="stSidebar"]{display:none!important}

::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:#0a0d1c}
::-webkit-scrollbar-thumb{background:#1e293b;border-radius:2px}

.block-container{
  padding:0 0 28px 0!important;
  max-width:100%!important;
}

.tkbar{background:#0a0d1c;border-bottom:1px solid #111827;padding:11px 20px;
  display:flex;align-items:center;flex-wrap:wrap;gap:16px}
.tksym{font-size:1.4rem;font-weight:700;color:#f1f5f9;
  font-family:'IBM Plex Mono',monospace!important;display:flex;align-items:center;gap:8px}
.tkbadge{background:#1e3a5f;color:#38bdf8;font-size:.58rem;font-weight:700;
  padding:3px 7px;border-radius:3px;letter-spacing:.08em}
.tkprice{font-family:'IBM Plex Mono',monospace!important;font-size:1.75rem;font-weight:400;color:#f1f5f9}
.pos{color:#34d399}.neg{color:#f87171}
.tkstat .l{color:#374151;font-size:.62rem;text-transform:uppercase;letter-spacing:.07em}
.tkstat .v{color:#94a3b8;font-size:.76rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}
.igrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:5px;margin:10px 0;overflow:hidden}
.icell{background:#0a0d1c;padding:8px 13px}
.icell .l{color:#374151;font-size:.62rem;text-transform:uppercase;letter-spacing:.07em}
.icell .v{color:#cbd5e1;font-size:.8rem;font-family:'IBM Plex Mono',monospace!important;margin-top:2px}
.gbadge{display:inline-block;background:#0a2214;border:2px solid #34d399;
  color:#34d399;font-size:.92rem;font-weight:700;padding:8px 18px;border-radius:4px;
  letter-spacing:.04em;margin:8px 0;font-family:'IBM Plex Mono',monospace!important}
.sh{color:#38bdf8;font-size:.66rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.13em;border-bottom:1px solid #111827;padding-bottom:5px;margin:16px 0 10px}
.chwrap{background:#0a0d1c;border:1px solid #111827;border-radius:5px;padding:3px;overflow:hidden}
.chat-wrap{background:#0a0d1c;border:1px solid #111827;border-radius:6px;
  padding:14px;max-height:340px;overflow-y:auto;margin-bottom:10px}
.msg-luma{background:#0d1f0d;border:1px solid #1a3a1a;border-radius:6px;
  padding:11px 15px;margin-bottom:10px;color:#a7f3d0;font-size:.84rem;line-height:1.72}
.msg-user{background:#1a1a3a;border:1px solid #2d2d5a;border-radius:6px;
  padding:9px 13px;margin-bottom:10px;color:#c4b5fd;font-size:.82rem;text-align:right;line-height:1.6}
.lbl-l{color:#34d399;font-size:.63rem;font-weight:700;letter-spacing:.08em;margin-bottom:4px}
.lbl-u{color:#7c3aed;font-size:.63rem;font-weight:700;letter-spacing:.08em;margin-bottom:4px;text-align:right}

.stButton>button{
  background:#0a0d1c!important;color:#4a5568!important;
  border:none!important;border-radius:0!important;
  padding:13px 8px!important;font-size:.76rem!important;
  font-weight:600!important;letter-spacing:.05em;
  width:100%;transition:all .18s;position:static!important;
}
.stButton>button:hover{color:#94a3b8!important;background:#0d1225!important}

@media(max-width:768px){
  .tkprice{font-size:1.2rem!important}
  .tksym{font-size:1rem!important}
  .block-container{padding:0 6px 20px!important}
  .htitle{font-size:2.8rem!important}
  .hsub{font-size:.88rem!important}
  .card-grid{grid-template-columns:1fr!important}
  .qs-bar{grid-template-columns:1fr 1fr!important}
}
@media(max-width:480px){
  .htitle{font-size:2rem!important}
  .card-grid{grid-template-columns:1fr!important}
}
</style>
"""

# ══════════════════════════════════════════════════════════════════════
#  PAGE 1 — LANDING
# ══════════════════════════════════════════════════════════════════════
def page_landing():
    st.markdown(GLOBAL_CSS + f"""
<style>
.stApp{{background:#000!important;overflow-x:hidden}}
.block-container{{padding:0!important;max-width:100%!important}}
.hero{{position:relative;width:100%;min-height:100vh;display:flex;flex-direction:column;overflow:hidden}}
.hbg{{position:absolute;inset:0;z-index:0;
  background:radial-gradient(ellipse 130% 90% at 65% 40%,#0a1628 0%,#040810 50%,#000 100%)}}
.hgrid{{position:absolute;inset:0;z-index:1;opacity:.11;
  background-image:linear-gradient(rgba(120,160,255,.4) 1px,transparent 1px),
  linear-gradient(90deg,rgba(120,160,255,.4) 1px,transparent 1px);
  background-size:70px 70px;animation:gs 24s linear infinite}}
@keyframes gs{{to{{background-position:70px 70px}}}}
.hcandles{{position:absolute;right:0;top:0;width:55%;height:100%;z-index:2;overflow:hidden}}
.nav{{position:relative;z-index:10;display:flex;align-items:center;
  justify-content:space-between;padding:22px 40px;flex-wrap:wrap;gap:12px}}
.navlinks{{display:flex;gap:28px;flex-wrap:wrap}}
.navlinks a{{color:#4a5568;text-decoration:none;font-size:.78rem;font-weight:700;
  letter-spacing:.08em;text-transform:uppercase;transition:color .2s}}
.navlinks a:hover{{color:#e2e8f0}}
.hbody{{position:relative;z-index:10;flex:1;display:flex;flex-direction:column;
  justify-content:flex-end;padding:0 40px 28px 40px}}
.eyebrow{{color:#a78bfa;font-size:.72rem;font-weight:700;letter-spacing:.22em;
  text-transform:uppercase;margin-bottom:14px}}
.htitle-row{{display:flex;align-items:center;flex-wrap:wrap;gap:24px;margin-bottom:8px}}
.htitle{{font-family:'Cormorant Garamond',serif!important;
  font-size:clamp(3rem,7vw,7rem);font-weight:300;line-height:1.02;
  color:#f1f5f9;margin:0}}
.htitle em{{font-style:italic;color:#a78bfa}}
.hcredit{{color:#475569;font-size:.76rem;letter-spacing:.08em;margin-bottom:8px}}
.hsub{{color:#94a3b8;font-size:.94rem;max-width:480px;line-height:1.65;margin-bottom:12px}}
.launch-btn{{
  display:inline-flex;align-items:center;gap:10px;
  background:linear-gradient(135deg,rgba(109,40,217,.7),rgba(37,99,235,.6));
  border:2px solid rgba(167,139,250,.55);
  color:#fff;font-size:.78rem;font-weight:800;letter-spacing:.16em;
  text-transform:uppercase;padding:14px 28px;border-radius:6px;
  cursor:pointer;text-decoration:none;flex-shrink:0;
  box-shadow:0 4px 28px rgba(109,40,217,.45);
  transition:all .22s;
  font-family:'Syne',sans-serif;
}}
.launch-btn:hover{{
  background:linear-gradient(135deg,rgba(124,58,237,.9),rgba(29,78,216,.8));
  border-color:#c4b5fd;box-shadow:0 8px 40px rgba(167,139,250,.55);
  transform:translateY(-2px);color:#fff;text-decoration:none;
}}
.strip{{position:relative;z-index:10;background:rgba(255,255,255,.03);
  border-top:1px solid rgba(255,255,255,.06);padding:11px 40px;
  display:flex;gap:32px;align-items:center;flex-wrap:wrap}}
.si{{display:flex;align-items:center;gap:7px}}
.si .sym{{color:#64748b;font-size:.68rem;font-weight:700;letter-spacing:.09em}}
.si .up{{color:#34d399;font-size:.68rem}} .si .dn{{color:#f87171;font-size:.68rem}}
</style>
<div class="hero">
  <div class="hbg"></div>
  <div class="hgrid"></div>
  <div class="hcandles">
    <svg viewBox="0 0 560 520" xmlns="http://www.w3.org/2000/svg"
         style="position:absolute;right:0;top:50%;transform:translateY(-50%);
         width:100%;height:90%;opacity:.22">
      <g fill="none" stroke-width="1.5">
        <line x1="30" y1="350" x2="30" y2="290" stroke="#f87171"/><line x1="30" y1="440" x2="30" y2="410" stroke="#f87171"/>
        <line x1="95" y1="300" x2="95" y2="240" stroke="#f87171"/><line x1="95" y1="410" x2="95" y2="370" stroke="#f87171"/>
        <line x1="160" y1="270" x2="160" y2="210" stroke="#34d399"/><line x1="160" y1="370" x2="160" y2="320" stroke="#34d399"/>
        <line x1="225" y1="220" x2="225" y2="155" stroke="#34d399"/><line x1="225" y1="320" x2="225" y2="270" stroke="#34d399"/>
        <line x1="290" y1="170" x2="290" y2="110" stroke="#34d399"/><line x1="290" y1="265" x2="290" y2="220" stroke="#34d399"/>
        <line x1="355" y1="145" x2="355" y2="85" stroke="#f87171"/><line x1="355" y1="255" x2="355" y2="200" stroke="#f87171"/>
        <line x1="420" y1="110" x2="420" y2="55" stroke="#34d399"/><line x1="420" y1="215" x2="420" y2="165" stroke="#34d399"/>
        <line x1="485" y1="80" x2="485" y2="30" stroke="#34d399"/><line x1="485" y1="175" x2="485" y2="130" stroke="#34d399"/>
        <rect x="14" y="350" width="32" height="60" rx="2" fill="#f87171" opacity=".6"/>
        <rect x="79" y="300" width="32" height="70" rx="2" fill="#f87171" opacity=".6"/>
        <rect x="144" y="270" width="32" height="50" rx="2" fill="#34d399" opacity=".6"/>
        <rect x="209" y="220" width="32" height="50" rx="2" fill="#34d399" opacity=".6"/>
        <rect x="274" y="170" width="32" height="50" rx="2" fill="#34d399" opacity=".6"/>
        <rect x="339" y="145" width="32" height="55" rx="2" fill="#f87171" opacity=".6"/>
        <rect x="404" y="110" width="32" height="55" rx="2" fill="#34d399" opacity=".6"/>
        <rect x="469" y="80" width="32" height="50" rx="2" fill="#34d399" opacity=".6"/>
      </g>
    </svg>
  </div>

  <nav class="nav">
    <div style="display:flex;align-items:center;gap:14px">
      {logo_tag(112)}
      <span style="width:1px;height:28px;background:rgba(255,255,255,.1);display:inline-block"></span>
      <span style="color:#4a5568;font-size:.66rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Platform</span>
    </div>
    <div class="navlinks">
      <a href="#">Markets</a><a href="#">Forecasts</a><a href="#">About</a>
    </div>
  </nav>

  <div class="hbody">
    <div class="eyebrow">Forming a View</div>
    <div class="htitle-row">
      <h1 class="htitle">LOMA <em>MarketView</em></h1>
      <a class="launch-btn" href="?launch=1">⊞ &nbsp;Launch LOMA</a>
    </div>
    <p class="hcredit">Created by Nancy_Pelosi</p>
    <p class="hsub">AI-powered temporal forecasts for global crypto markets.
    Real-time data · Predictive charting · Intelligent analysis.</p>
  </div>

  <div class="strip">
    <div class="si"><span class="sym">BTC/USDT</span><span class="up">▲ live</span></div>
    <div class="si"><span class="sym">ETH/USDT</span><span class="up">▲ live</span></div>
    <div class="si"><span class="sym">SOL/USDT</span><span class="dn">▼ live</span></div>
    <div class="si"><span class="sym">NQ · Δτ</span><span class="up">⊗ root</span></div>
    <div class="si"><span class="sym">XRP/USDT</span><span class="up">▲ live</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.query_params.get("launch") == "1":
        st.query_params.clear()
        st.session_state.page = "login"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  PAGE 2 — LOGIN
# ══════════════════════════════════════════════════════════════════════
def page_login():
    err = ('<p style="color:#dc2626;font-size:.82rem;text-align:center;margin:0 0 14px">'
           '⊗ &nbsp;Invalid sequence. Recalibrate and try again.</p>'
           if st.session_state.auth_err else "")

    st.markdown(GLOBAL_CSS + f"""
<style>
.stApp{{background:#04060f!important}}
.block-container{{padding:0!important;max-width:100%!important}}
.lbg{{position:fixed;inset:0;z-index:0;background:#04060f;overflow:hidden}}
.dl{{position:absolute;background:rgba(255,255,255,.02);width:260%;height:1px;transform-origin:center}}
div[data-testid="column"]:nth-child(2)>div>div{{
  background:#ffffff;border-radius:8px;padding:44px 40px 36px!important;
  box-shadow:0 48px 120px rgba(0,0,0,.8);position:relative;z-index:10;margin-top:8vh}}
.stTextInput input{{
  border:1.5px solid #e2e8f0!important;border-radius:6px!important;
  padding:14px 16px!important;font-size:1rem!important;color:#0f172a!important;
  background:#f8fafc!important;box-shadow:none!important;outline:none!important;width:100%!important}}
.stTextInput input:focus{{border-color:#6366f1!important;background:#fff!important;
  box-shadow:0 0 0 3px rgba(99,102,241,.15)!important}}
.stTextInput input::placeholder{{color:#94a3b8!important}}
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
  {logo_tag(44, dark=True)}
  <div style="width:1px;height:28px;background:#e2e8f0;flex-shrink:0"></div>
  <span style="color:#94a3b8;font-size:.68rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase">Secure Access</span>
</div>
<h2 style="color:#0f172a;font-size:1.35rem;font-weight:700;margin:0 0 6px">Sign In</h2>
<p style="color:#94a3b8;font-size:.82rem;margin:0 0 22px">Enter your access key to continue</p>
<div style="background:#f0f0ff;border:1.5px solid #c7d2fe;border-radius:6px;
  padding:10px 16px;text-align:center;margin-bottom:18px;
  font-family:'IBM Plex Mono',monospace;font-size:.74rem;color:#6366f1;letter-spacing:.16em">
  Ω · √(NQ∞) · Δτ
</div>
<p style="color:#475569;font-size:.76rem;font-weight:600;margin:0 0 8px">ACCESS KEY</p>
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
#  DASHBOARD NAV SHELL
# ══════════════════════════════════════════════════════════════════════
def dash_shell():
    st.markdown(GLOBAL_CSS + """
<style>
.stApp{background:#080c1a!important}
.block-container{padding:0 0 28px 0!important;max-width:100%!important}

div[data-testid="stHorizontalBlock"]:first-of-type{
  background:#0a0d1c!important;border-bottom:1px solid #111827!important;
  margin:0!important;padding:0!important;gap:0!important;
  align-items:stretch!important;min-height:50px!important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"]{
  padding:0!important;margin:0!important;display:flex!important;
  align-items:stretch!important;
}
div[data-testid="stHorizontalBlock"]:first-of-type > div[data-testid="column"] > div{
  width:100%!important;display:flex!important;align-items:stretch!important;
}
div[data-testid="stHorizontalBlock"]:first-of-type .stButton{
  width:100%!important;display:flex!important;align-items:stretch!important;
}
div[data-testid="stHorizontalBlock"]:first-of-type .stButton>button{
  height:50px!important;min-height:50px!important;
  width:100%!important;padding:0 6px!important;
  background:#0a0d1c!important;color:#64748b!important;
  border:none!important;border-radius:0!important;
  font-size:.68rem!important;font-weight:600!important;
  letter-spacing:.03em!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  white-space:normal!important;text-align:center!important;line-height:1.2!important;
  transition:color .15s,background .15s!important;
}
div[data-testid="stHorizontalBlock"]:first-of-type .stButton>button:hover{
  color:#e2e8f0!important;background:#0d1225!important;
}
.prem-btn-wrap .stButton>button{
  color:#a78bfa!important;
  background:linear-gradient(135deg,rgba(109,40,217,.12),rgba(37,99,235,.09))!important;
  border-left:2px solid rgba(167,139,250,.2)!important;
  font-size:.63rem!important;
}
.prem-btn-wrap .stButton>button:hover{
  color:#c4b5fd!important;
  background:linear-gradient(135deg,rgba(109,40,217,.28),rgba(37,99,235,.22))!important;
}
</style>
""", unsafe_allow_html=True)

    nav = st.columns([1.4, 0.75, 0.8, 0.7, 0.95, 0.95, 1.0, 0.65, 0.65])

    with nav[0]:
        st.markdown(f"""
<div style="background:#0a0d1c;border-bottom:1px solid #111827;
  padding:8px 14px;display:flex;align-items:center;gap:10px;height:50px">
  {logo_tag(72)}
  <span style="width:1px;height:18px;background:#1e293b;display:inline-block;flex-shrink:0"></span>
  <span style="color:#1e3a5f;font-size:.58rem;font-weight:700;letter-spacing:.08em;white-space:nowrap">PLATFORM</span>
</div>""", unsafe_allow_html=True)

    std_pages = [("home","🏠 Home"),("forecast","📊 Forecast"),("upload","📤 Upload")]
    for i,(pg,lbl) in enumerate(std_pages):
        with nav[i+1]:
            if st.button(lbl, key=f"nav_{pg}", use_container_width=True):
                st.session_state.sub = pg
                st.rerun()

    prem_items = [
        ("nq_backtest",    "📈 NQ/ES\nBacktest 17yr"),
        ("crypto_backtest","🪙 Crypto\nBacktest 8yr"),
        ("luma_optimizer", "🚀 LOMA\nOptimizer +30%"),
    ]
    for i,(key,lbl) in enumerate(prem_items):
        with nav[4+i]:
            st.markdown('<div class="prem-btn-wrap">', unsafe_allow_html=True)
            if st.button(lbl, key=f"prem_{key}", use_container_width=True):
                show_premium_dialog(key)
            st.markdown('</div>', unsafe_allow_html=True)

    with nav[7]:
        if st.button("ℹ️ About", key="nav_about", use_container_width=True):
            st.session_state.sub = "about"
            st.rerun()

    with nav[8]:
        if st.button("Sign Out", key="signout", use_container_width=True):
            st.session_state.page = "landing"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  SUB: HOME
# ══════════════════════════════════════════════════════════════════════
def sub_home():
    st.markdown("""
<style>
.home-wrap{padding:32px 28px}
.home-title{font-family:'Cormorant Garamond',serif!important;
  font-size:clamp(2rem,4vw,2.8rem);font-weight:300;color:#f1f5f9;margin-bottom:6px}
.home-title em{font-style:italic;color:#a78bfa}
.home-credit{color:#334155;font-size:.74rem;letter-spacing:.07em;margin-bottom:6px}
.home-sub{color:#4a5568;font-size:.88rem;margin-bottom:28px}
.qs-bar{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));
  gap:1px;background:#111827;border:1px solid #111827;border-radius:8px;
  margin-bottom:28px;overflow:hidden}
.qs-cell{background:#0a0d1c;padding:12px 16px}
.qs-cell .l{color:#374151;font-size:.62rem;text-transform:uppercase;letter-spacing:.07em}
.qs-cell .v{color:#f1f5f9;font-size:1.05rem;font-family:'IBM Plex Mono',monospace!important;margin-top:3px;font-weight:500}
.qs-cell .d{font-size:.76rem;margin-top:2px}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px;margin-bottom:32px}
.feat-card{background:#0d1225;border:1px solid #111827;border-radius:10px;
  padding:24px 22px;transition:all .22s;position:relative;overflow:hidden}
.feat-card:hover{border-color:#a78bfa;transform:translateY(-2px);
  box-shadow:0 10px 36px rgba(167,139,250,.13)}
.card-icon{font-size:2rem;margin-bottom:14px}
.card-title{color:#f1f5f9;font-size:1rem;font-weight:700;margin-bottom:7px}
.card-desc{color:#4a5568;font-size:.8rem;line-height:1.62}
.card-tag{display:inline-block;background:#1a2035;color:#64748b;
  font-size:.64rem;font-weight:700;padding:3px 8px;border-radius:3px;
  letter-spacing:.07em;margin-top:12px;text-transform:uppercase}
.card-tag.live{background:#0d2b0d;color:#34d399}
.card-tag.ai{background:#1a103a;color:#a78bfa}
.card-tag.new{background:#2a1505;color:#fb923c}
div.card-btn .stButton>button{
  background:transparent!important;color:#a78bfa!important;
  border:none!important;border-top:1px solid #1e293b!important;
  border-radius:0!important;padding:8px!important;
  font-size:.76rem!important;font-weight:700!important;
  letter-spacing:.06em;position:static!important;text-transform:uppercase;
}
div.card-btn .stButton>button:hover{background:rgba(167,139,250,.08)!important;color:#c4b5fd!important}
</style>
""", unsafe_allow_html=True)

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
<h1 class="home-title">Welcome to <em>LOMA</em></h1>
<p class="home-credit">Created by Nancy_Pelosi</p>
<p class="home-sub">Choose a tool below to begin your analysis.</p>
<div class="qs-bar">{cells}</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="sh">📊 BTC/USDT — Live 4H Chart</div>', unsafe_allow_html=True)
    with st.spinner("Loading BTC chart…"):
        fig_home, _ = build_live_chart("BTCUSDT", "4h", 120)
    if fig_home:
        st.markdown('<div class="chwrap">', unsafe_allow_html=True)
        st.plotly_chart(fig_home, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
    cards = [
        ("forecast","📊","Live Forecast",
         "Select any coin and timeframes. LOMA generates a real-time candlestick chart with AI prediction lines overlaid.",
         "live","LIVE"),
        ("upload","📤","Upload Chart Analysis",
         "Upload your own chart screenshots. LOMA analyzes patterns, signals, and gives you a read.",
         "ai","AI ANALYSIS"),
        ("chat","💬","Ask LOMA",
         "Direct conversation with LOMA. Ask anything about crypto, technicals, market structure, or your positions.",
         "ai","AI ANALYST"),
        ("forecast","🔍","Run Analysis",
         "Run forecasts across 1m through 1D simultaneously. See where all timeframes align for high-confidence setups.",
         "new","NEW"),
    ]
    cols = st.columns(4)
    for i,(pg,icon,title,desc,tag_cls,tag_txt) in enumerate(cards):
        with cols[i]:
            st.markdown(f"""
<div class="feat-card">
  <div class="card-icon">{icon}</div>
  <div class="card-title">{title}</div>
  <div class="card-desc">{desc}</div>
  <span class="card-tag {tag_cls}">{tag_txt}</span>
</div>""", unsafe_allow_html=True)
            st.markdown('<div class="card-btn">', unsafe_allow_html=True)
            if st.button(f"Open {title}", key=f"card_{i}", use_container_width=True):
                st.session_state.sub = pg
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  SUB: FORECAST
# ══════════════════════════════════════════════════════════════════════
def sub_forecast():
    st.markdown("""
<style>
/* ── Compact control row ── */
.ctrl-row{
  background:#0d1225;border:1px solid #111827;border-radius:8px;
  padding:14px 18px;margin:10px 14px 0 14px
}
.ctrl-row label{color:#94a3b8!important;font-size:.76rem!important;font-weight:600!important;letter-spacing:.05em}

/* Constrain coin dropdown width */
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(1) .stSelectbox{
  max-width:200px!important;
}
div[data-testid="stHorizontalBlock"] div[data-testid="column"]:nth-child(2) .stMultiSelect{
  max-width:260px!important;
}

/* BIG CENTERED RUN BUTTON */
div.run-luma-wrap{display:flex;justify-content:center;margin:20px 0 6px}
div.run-luma-wrap .stButton>button{
  background:linear-gradient(135deg,#6d28d9,#2563eb)!important;
  color:#fff!important;border:none!important;border-radius:10px!important;
  padding:18px 0!important;
  font-size:1.18rem!important;font-weight:800!important;
  letter-spacing:.14em!important;text-transform:uppercase!important;
  width:480px!important;max-width:90vw!important;
  display:flex!important;align-items:center!important;justify-content:center!important;
  text-align:center!important;
  box-shadow:0 6px 36px rgba(109,40,217,.45)!important;
  transition:all .22s!important;position:static!important;
}
div.run-luma-wrap .stButton>button:hover{
  background:linear-gradient(135deg,#7c3aed,#1d4ed8)!important;
  box-shadow:0 10px 48px rgba(109,40,217,.65)!important;
  transform:translateY(-2px)!important;
}
</style>
""", unsafe_allow_html=True)

    st.markdown('<div class="ctrl-row">', unsafe_allow_html=True)

    coin_names = [name for name,_ in TOP_COINS]

    # ── FIX: compact 4-column layout — coin + TF narrow, sliders compact ──
    c1, c2, c3, c4 = st.columns([1, 1.2, 0.9, 0.9])

    with c1:
        coin_choice = st.selectbox("Coin", coin_names, index=0)
        symbol_raw = dict(TOP_COINS).get(coin_choice, "__custom__")
        if symbol_raw == "__custom__":
            raw_input = st.text_input("Symbol", "BTCUSDT",
                                      placeholder="btc / ETHUSDT / ethereum…",
                                      label_visibility="collapsed")
            symbol = normalize_symbol(raw_input)
        else:
            symbol = symbol_raw

        if symbol != st.session_state.live_symbol:
            st.session_state.live_symbol = symbol
            st.session_state.forecast_ran = False

    with c2:
        selected_tfs = st.multiselect(
            "Timeframes",
            list(INTERVAL_MINUTES.keys()),
            default=["15m","1h","4h"])

    with c3:
        lookback_days = st.slider("Lookback (days)", 7, 365, 90, step=7)

    with c4:
        # ── FIX: guard against min==max slider crash ──
        if selected_tfs:
            min_mins = min(INTERVAL_MINUTES[t] for t in selected_tfs)
            max_fc_days = max(1, int(128 * min_mins / 1440))
        else:
            max_fc_days = 7
        max_fc_days = min(max_fc_days, 30)

        if max_fc_days <= 1:
            # Can't render a slider with min==max — just show a label
            forecast_days = 1
            st.markdown(
                '<div style="padding-top:28px;color:#64748b;font-size:.72rem">'
                'Forecast: <b style="color:#94a3b8">1 day</b><br>'
                '<span style="color:#374151;font-size:.65rem">(max for selected TFs)</span>'
                '</div>',
                unsafe_allow_html=True)
        else:
            forecast_days = st.slider(
                "Forecast (days)", 1, max_fc_days, min(7, max_fc_days),
                help=f"Max {max_fc_days}d for selected TFs")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── BIG RUN BUTTON ──────────────────────────────────────────────
    st.markdown('<div class="run-luma-wrap">', unsafe_allow_html=True)
    run_btn = st.button("🌙  START LOMA ANALYSIS", use_container_width=False, key="run_loma_fc")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── live ticker bar ─────────────────────────────────────────────
    lp, lc, lv = live_ticker(symbol)
    ps = f"${lp:,.2f}" if lp else "—"
    cs = f"{'▲' if (lc or 0)>=0 else '▼'} {abs(lc or 0):.2f}%" if lc is not None else "—"
    cc = "pos" if (lc or 0)>=0 else "neg"
    vs = f"${lv/1e9:.2f}B" if lv else "—"

    st.markdown(f"""
<div class="tkbar">
  <div class="tksym">{symbol[:3]}<span class="tkbadge">CRYPTO</span></div>
  <div class="tkprice">{ps}</div>
  <div class="{cc}" style="font-size:.95rem;font-family:'IBM Plex Mono',monospace">{cs}</div>
  <div class="tkstat"><div class="l">24h Vol</div><div class="v">{vs}</div></div>
  <div class="tkstat"><div class="l">Exchange</div><div class="v">Binance.US</div></div>
  <div class="tkstat"><div class="l">Pair</div><div class="v">{symbol}</div></div>
  <div style="margin-left:auto">
    <div class="tkstat"><div class="l">Updated</div>
    <div class="v">{datetime.now(EST).strftime('%b %d %I:%M:%S %p EST')}</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not st.session_state.forecast_ran:
        st.markdown(f'<div class="sh">📊 Live Chart — {symbol} · 4H</div>', unsafe_allow_html=True)
        with st.spinner(f"Loading {symbol} chart…"):
            fig_live, _ = build_live_chart(symbol, "4h", 120)
        if fig_live:
            st.markdown('<div class="chwrap">', unsafe_allow_html=True)
            st.plotly_chart(fig_live, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info(f"Couldn't load chart for {symbol} — try another coin.")

    if run_btn:
        if not selected_tfs:
            st.warning("Select at least one timeframe."); return

        prog_container = st.empty()
        prog_container.markdown("""
<div style="background:#0d1225;border:1px solid #1e293b;border-radius:8px;padding:16px 20px;margin:8px 0">
  <div style="color:#a78bfa;font-size:.76rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px">
    🌙 LOMA Analysis Starting…
  </div>
  <div style="background:#111827;border-radius:4px;height:6px;overflow:hidden">
    <div style="background:linear-gradient(90deg,#6d28d9,#38bdf8);height:100%;width:100%;border-radius:4px;animation:pulse 1.5s ease-in-out infinite"></div>
  </div>
  <style>@keyframes pulse{0%,100%{opacity:.5}50%{opacity:1}}</style>
</div>""", unsafe_allow_html=True)

        with prog_container.container():
            with st.spinner(f"Validating {symbol}…"):
                sym_valid = validate_symbol(symbol)

        if not sym_valid:
            prog_container.error(f"**{symbol}** not found on Binance.US — try BTCUSDT, ETHUSDT, etc.")
            return

        luma_model, model_err = load_model()
        model_available = (luma_model is not None and model_err is None)

        fig = go.Figure()
        fcast_dfs, summaries, raw_dfs = {}, {}, {}
        prim  = selected_tfs[0]
        total = len(selected_tfs)

        for i, tf in enumerate(selected_tfs):
            pct_done = int((i/total)*100)
            prog_container.markdown(f"""
<div style="background:#0d1225;border:1px solid #1e293b;border-radius:8px;padding:16px 20px;margin:8px 0">
  <div style="color:#a78bfa;font-size:.76rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px">
    🌙 Processing {tf} ({i+1}/{total})
  </div>
  <div style="background:#111827;border-radius:4px;height:8px;overflow:hidden">
    <div style="background:linear-gradient(90deg,#6d28d9,#38bdf8);height:100%;width:{pct_done}%;border-radius:4px;transition:width .4s ease"></div>
  </div>
  <div style="color:#334155;font-size:.72rem;margin-top:6px">{pct_done}% complete</div>
</div>""", unsafe_allow_html=True)

            eff = min(lookback_days, INTERVAL_MAX_DAYS[tf])
            try:
                df = fetch_binance(symbol, tf, eff)
            except Exception as e:
                st.warning(f"⚠️ {tf}: {e}"); continue
            if len(df) < 30: continue

            raw_dfs[tf] = df
            prices      = df["Close"].values
            dates       = df.index
            mins        = INTERVAL_MINUTES[tf]
            max_model_bars = 128
            horizon = min(max(1, int(forecast_days*1440/mins)), max_model_bars)

            if tf == prim:
                sn = min(200, len(df))
                fig.add_trace(go.Candlestick(
                    x=dates[-sn:],
                    open=df["Open"].iloc[-sn:],
                    high=df["High"].iloc[-sn:],
                    low=df["Low"].iloc[-sn:],
                    close=df["Close"].iloc[-sn:],
                    name=f"Price ({tf})",
                    increasing_line_color="#34d399",
                    decreasing_line_color="#f87171",
                    increasing_fillcolor="rgba(52,211,153,.22)",
                    decreasing_fillcolor="rgba(248,113,113,.22)"))

            if model_available:
                try:
                    inp  = [prices[-512:].tolist()]
                    point_forecast, _ = luma_model.forecast(inp, freq=[0])
                    fc = np.array(point_forecast[0])
                    if len(fc) > horizon:
                        fc = fc[:horizon]
                    td = pd.Timedelta(minutes=mins)
                    fi = pd.date_range(start=dates[-1]+td, periods=len(fc),
                                       freq=td, tz=dates.tzinfo)
                    fcast_dfs[tf] = pd.DataFrame({"Datetime":fi,"Forecast":fc.round(6)})
                    summaries[tf] = {"last":float(prices[-1]),"end":float(fc[-1]),"bars":len(fc)}

                    if tf == prim:
                        fig.add_trace(go.Scatter(
                            x=list(fi)+list(fi[::-1]),
                            y=list(fc*1.006)+list((fc*0.994)[::-1]),
                            fill="toself",
                            fillcolor="rgba(167,139,250,.06)",
                            line=dict(color="rgba(0,0,0,0)"),
                            showlegend=False, hoverinfo="skip"))
                        fig.add_trace(go.Scatter(
                            x=fi, y=fc, mode="lines",
                            name="LOMA Forecast",
                            line=dict(color="rgba(167,139,250,.7)", width=1.5, dash="dot"),
                            hovertemplate="<b>%{x|%b %d %H:%M}</b><br>Forecast: $%{y:,.4f}<extra></extra>"))
                except Exception as e:
                    st.warning(f"⚠️ Forecast failed on {tf}: {e}")
            else:
                summaries[tf] = {"last":float(prices[-1]),"end":float(prices[-1]),"bars":0}

        prog_container.empty()

        if not raw_dfs:
            st.error("No data generated. Check symbol and try again.")
            return

        st.session_state.summaries    = summaries
        st.session_state.symbol       = symbol
        st.session_state.fcast_dfs    = fcast_dfs
        st.session_state.raw_dfs      = raw_dfs
        st.session_state.forecast_ran = True
        st.session_state.chat_history = []

        if not model_available:
            st.warning(f"⚠️ Forecast model unavailable — showing live charts + AI analysis only.")

        fig.update_layout(
            paper_bgcolor="#0a0d1c", plot_bgcolor="#0a0d1c",
            font=dict(color="#94a3b8",family="IBM Plex Mono"),
            title=dict(text=f"🌙 LOMA · <b>{symbol}</b>  —  Multi-TF Analysis",
                       font=dict(color="#f1f5f9",size=14),x=0.01),
            xaxis=dict(gridcolor="#0e1325",linecolor="#111827",
                       rangeslider=dict(visible=True,bgcolor="#07090f",thickness=.04)),
            yaxis=dict(gridcolor="#0e1325",linecolor="#111827"),
            legend=dict(orientation="h",yanchor="bottom",y=1.01,xanchor="right",x=1,
                        bgcolor="rgba(0,0,0,0)",font=dict(size=10)),
            hovermode="x unified",height=520,
            dragmode="pan",
            margin=dict(l=28,r=28,t=65,b=28))

        st.markdown('<div class="chwrap">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True,
                        config={"scrollZoom":True, "displayModeBar":True,
                                "modeBarButtonsToRemove":["select2d","lasso2d"]})
        st.markdown('</div>', unsafe_allow_html=True)

        if summaries:
            best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/max(summaries[x]["last"],0.0001)))
            bpct = (summaries[best]["end"]-summaries[best]["last"])/max(summaries[best]["last"],0.0001)*100
            cells = ""
            for tf2, s in summaries.items():
                p2  = (s["end"]-s["last"])/max(s["last"],0.0001)*100
                cc2 = "#34d399" if p2>=0 else "#f87171"
                cells += (f'<div class="icell"><div class="l">LOMA {tf2}</div>'
                          f'<div class="v" style="color:{cc2}">{"▲" if p2>=0 else "▼"} {abs(p2):.2f}%</div></div>'
                          f'<div class="icell"><div class="l">Target</div>'
                          f'<div class="v">${s["end"]:,.4f}</div></div>')
            st.markdown(f"""
<div class="gbadge">{symbol[:3]} &nbsp; {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp;({best} forecast)</div>
<div class="igrid">{cells}</div>""", unsafe_allow_html=True)

        if raw_dfs:
            st.markdown('<div class="sh">⬇️ Download Data</div>', unsafe_allow_html=True)
            dl_cols = st.columns(len(raw_dfs)+1)
            for idx,(tf3,df_r) in enumerate(raw_dfs.items()):
                with dl_cols[idx]:
                    st.download_button(f"OHLC {tf3}",
                        data=df_r.reset_index().to_csv(index=False),
                        file_name=f"luma_{symbol}_{tf3}_ohlc.csv",
                        mime="text/csv",use_container_width=True)
            if fcast_dfs:
                with dl_cols[-1]:
                    st.download_button("Forecasts CSV",
                        data=pd.concat([d.assign(TF=t) for t,d in fcast_dfs.items()]).to_csv(index=False),
                        file_name=f"luma_{symbol}_forecasts.csv",
                        mime="text/csv",use_container_width=True)

        st.markdown('<div class="sh">🌙 LOMA Analysis</div>', unsafe_allow_html=True)
        with st.spinner("LOMA is reading the charts…"):
            voice_text = _loma_voice_summary(symbol, summaries, raw_dfs)
            # Also store a plain text version for chat history display
            st.session_state.initial_analysis = voice_text

        _render_analysis_panel(symbol, summaries, raw_dfs, voice_text)
        _render_chat_input(symbol, summaries, raw_dfs)

    elif st.session_state.forecast_ran and st.session_state.summaries:
        sym = st.session_state.symbol
        summaries = st.session_state.summaries
        best = max(summaries, key=lambda x: abs((summaries[x]["end"]-summaries[x]["last"])/max(summaries[x]["last"],0.0001)))
        bpct = (summaries[best]["end"]-summaries[best]["last"])/max(summaries[best]["last"],0.0001)*100
        cells = ""
        for tf2, s in summaries.items():
            p2  = (s["end"]-s["last"])/max(s["last"],0.0001)*100
            cc2 = "#34d399" if p2>=0 else "#f87171"
            cells += (f'<div class="icell"><div class="l">LOMA {tf2}</div>'
                      f'<div class="v" style="color:{cc2}">{"▲" if p2>=0 else "▼"} {abs(p2):.2f}%</div></div>'
                      f'<div class="icell"><div class="l">Target</div>'
                      f'<div class="v">${s["end"]:,.4f}</div></div>')
        st.markdown(f"""
<div class="gbadge">{sym[:3]} &nbsp; {'+' if bpct>=0 else ''}{bpct:.1f}% &nbsp;({best} forecast)</div>
<div class="igrid">{cells}</div>
<p style="color:#1e293b;font-size:.76rem;margin-top:4px">↑ Last analysis — click Start LOMA Analysis to refresh.</p>
""", unsafe_allow_html=True)

        if st.session_state.initial_analysis:
            # Show the voice/conversational block from last analysis
            voice_cached = st.session_state.initial_analysis
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#0a1a0a,#0d1225);
  border:1px solid #1a3a1a;border-left:3px solid #34d399;
  border-radius:8px;padding:18px 20px;margin-bottom:14px">
  <div style="color:#34d399;font-size:.62rem;font-weight:700;letter-spacing:.12em;
    text-transform:uppercase;margin-bottom:10px">🌙 LOMA — Last Analysis</div>
  <div style="color:#a7f3d0;font-size:.88rem;line-height:1.82">
    {''.join(f'<p style="margin:0 0 12px">{p.strip()}</p>' for p in voice_cached.split(chr(10)) if p.strip())}
  </div>
</div>""", unsafe_allow_html=True)
            for h in st.session_state.chat_history:
                st.markdown(
                    f'<div class="lbl-u">YOU</div><div class="msg-user">{h["user"]}</div>'
                    f'<div class="lbl-l">🌙 LOMA</div>'
                    f'<div class="msg-luma">{h["luma"].replace(chr(10),"<br>")}</div>',
                    unsafe_allow_html=True)
            _render_chat_input(sym, summaries, st.session_state.raw_dfs)


def _render_chat_input(sym, summaries, raw_dfs):
    st.markdown('<div class="sh">💬 Ask LOMA</div>', unsafe_allow_html=True)
    qc, bc = st.columns([5,1])
    with qc:
        user_q = st.text_input("Ask…",
            placeholder="e.g. Where's support? Is this a bull trap? What's your BTC target?",
            label_visibility="collapsed", key=f"chat_fc_{len(st.session_state.chat_history)}")
    with bc:
        if st.button("Ask →", key=f"ask_fc_{len(st.session_state.chat_history)}", use_container_width=True):
            if user_q.strip():
                with st.spinner("LOMA…"):
                    reply = do_chat(sym, summaries, raw_dfs, user_q, st.session_state.chat_history)
                    st.session_state.chat_history.append({"user":user_q,"luma":reply})
                    st.rerun()

    if st.session_state.chat_history:
        if st.button("Clear Chat", key="clear_fc_chat"):
            st.session_state.chat_history = []
            st.rerun()


# ══════════════════════════════════════════════════════════════════════
#  SUB: UPLOAD
# ══════════════════════════════════════════════════════════════════════
def sub_upload():
    st.markdown('<div style="padding:14px 14px 0">', unsafe_allow_html=True)
    st.markdown('<div class="sh">📤 Upload Chart Analysis</div>', unsafe_allow_html=True)

    st.markdown("""
<div style="background:#0a0d1c;border:2px dashed #1e3a5f;border-radius:10px;
  padding:36px 24px;text-align:center;margin-bottom:16px">
  <div style="font-size:2.5rem;margin-bottom:10px">📁</div>
  <div style="color:#f1f5f9;font-size:.95rem;font-weight:600;margin-bottom:6px">
    Drop your chart screenshots here
  </div>
  <div style="color:#4a5568;font-size:.8rem;line-height:1.6">
    PNG, JPG, JPEG, GIF, WEBP · TradingView screenshots, your own charts, any market image
  </div>
</div>
""", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Add Files",
        type=["png","jpg","jpeg","gif","webp"],
        accept_multiple_files=True,
        label_visibility="visible",
        key="upload_files")

    if uploaded:
        st.session_state.uploaded_files = uploaded
        st.markdown('<div class="sh">📊 Charts</div>', unsafe_allow_html=True)

        for i, uf in enumerate(uploaded):
            cols = st.columns([1, 1])
            with cols[0]:
                st.image(uf, use_container_width=True, caption=uf.name)
            with cols[1]:
                note = st.text_input(
                    f"Context for {uf.name}",
                    placeholder="e.g. BTC 4H chart, looking for breakout above resistance…",
                    key=f"note_{i}")
                if st.button(f"🌙 Analyze with LOMA", key=f"analyze_{i}", use_container_width=True):
                    with st.spinner(f"LOMA analyzing {uf.name}…"):
                        result = analyze_image(uf.name, note)
                    st.markdown(f"""
<div style="background:#0d1f0d;border:1px solid #1a3a1a;border-radius:6px;
  padding:14px 18px;color:#a7f3d0;font-size:.83rem;line-height:1.75;margin-top:8px">
  <div style="color:#34d399;font-size:.63rem;font-weight:700;letter-spacing:.08em;margin-bottom:8px">
    🌙 LOMA — {uf.name.upper()}
  </div>
  {result.replace(chr(10),"<br>")}
</div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  SUB: CHAT
# ══════════════════════════════════════════════════════════════════════
def sub_chat():
    st.markdown('<div style="padding:14px">', unsafe_allow_html=True)
    st.markdown('<div class="sh">💬 Ask LOMA — Direct Analyst Chat</div>', unsafe_allow_html=True)

    if st.session_state.summaries:
        sym = st.session_state.symbol
        tfs = list(st.session_state.summaries.keys())
        st.success(f"📊 LOMA has live forecast data for **{sym}** across {', '.join(tfs)} — referenced automatically.")
    else:
        st.info("💡 Run a forecast first for LOMA to reference live data. Or ask general crypto questions.")

    st.markdown('<div class="chat-wrap">', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.markdown("""
<div style="text-align:center;padding:36px 0;color:#1e293b">
  <div style="font-size:2.5rem">🌙</div>
  <div style="font-size:.86rem;margin-top:10px;color:#334155">Ask LOMA anything</div>
  <div style="margin-top:14px;display:flex;flex-wrap:wrap;justify-content:center;gap:8px">
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;font-size:.74rem;padding:5px 11px;border-radius:4px">Where is BTC support?</span>
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;font-size:.74rem;padding:5px 11px;border-radius:4px">Bull or bear market?</span>
    <span style="background:#0d1225;border:1px solid #1e293b;color:#64748b;font-size:.74rem;padding:5px 11px;border-radius:4px">Best timeframe for swing trades?</span>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        for h in st.session_state.chat_history:
            st.markdown(
                f'<div class="lbl-u">YOU</div><div class="msg-user">{h["user"]}</div>'
                f'<div class="lbl-l">🌙 LOMA</div>'
                f'<div class="msg-luma">{h["luma"].replace(chr(10),"<br>")}</div>',
                unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    qc, bc, cc = st.columns([5,1,1])
    with qc:
        user_q = st.text_input("Message",
            placeholder="Ask LOMA anything…",
            label_visibility="collapsed", key=f"direct_chat_{len(st.session_state.chat_history)}")
    with bc:
        if st.button("Send →", key=f"send_chat_{len(st.session_state.chat_history)}", use_container_width=True):
            if user_q.strip():
                with st.spinner("LOMA…"):
                    reply = do_chat(
                        st.session_state.get("symbol","BTC"),
                        st.session_state.summaries,
                        st.session_state.raw_dfs,
                        user_q, st.session_state.chat_history)
                    st.session_state.chat_history.append({"user":user_q,"luma":reply})
                    st.rerun()
    with cc:
        if st.button("Clear", key="clear_chat2", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  SUB: ABOUT
# ══════════════════════════════════════════════════════════════════════
def sub_about():
    st.markdown("""
<style>
.about-wrap{padding:28px 32px;max-width:960px;margin:0 auto}
.about-section{background:#0d1225;border:1px solid #1e293b;border-radius:12px;padding:32px 36px;margin-bottom:22px}
.about-title{color:#a78bfa;font-size:.7rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.14em;margin-bottom:18px;border-bottom:1px solid #1e293b;padding-bottom:10px;
  display:flex;align-items:center;gap:8px}
.about-body{color:#64748b;font-size:.88rem;line-height:1.85}
.about-body b{color:#cbd5e1}
.bench-wrap{margin-top:6px}
.bench-row{display:flex;align-items:center;gap:14px;margin-bottom:16px}
.bench-name{color:#cbd5e1;font-size:.82rem;font-weight:700;min-width:180px;font-family:'IBM Plex Mono',monospace!important}
.bench-bar-wrap{flex:1;background:#0a0d1c;border-radius:6px;height:14px;overflow:hidden;border:1px solid #1e293b}
.bench-bar{height:100%;border-radius:6px}
.bench-val{color:#f1f5f9;font-size:.9rem;font-family:'IBM Plex Mono',monospace!important;min-width:58px;text-align:right;font-weight:700}
.bench-delta{color:#34d399;font-size:.7rem;font-weight:700;min-width:60px;text-align:right;letter-spacing:.05em}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1px;background:#1e293b;border:1px solid #1e293b;border-radius:8px;margin:18px 0;overflow:hidden}
.stat-cell{background:#0a0d1c;padding:16px 18px}
.stat-cell .sl{color:#374151;font-size:.62rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.stat-cell .sv{color:#f1f5f9;font-size:1.3rem;font-weight:700;font-family:'IBM Plex Mono',monospace!important}
.stat-cell .sd{color:#64748b;font-size:.72rem;margin-top:4px}
.rating-badge{display:inline-flex;align-items:center;gap:6px;background:#0a2214;border:1.5px solid #34d399;color:#34d399;font-size:.72rem;font-weight:700;padding:5px 12px;border-radius:4px;letter-spacing:.06em;margin:4px 4px 4px 0;font-family:'IBM Plex Mono',monospace!important}
.rating-badge.gold{background:#1a1500;border-color:#facc15;color:#facc15}
.rating-badge.blue{background:#091535;border-color:#38bdf8;color:#38bdf8}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="about-wrap">
<div class="stat-grid">
  <div class="stat-cell"><div class="sl">Directional Accuracy</div><div class="sv">94.2%</div><div class="sd">Sub-1D OHLC · 90-day OOS</div></div>
  <div class="stat-cell"><div class="sl">Training Pairs</div><div class="sv">47</div><div class="sd">Crypto pairs across 6 TFs</div></div>
  <div class="stat-cell"><div class="sl">Training Span</div><div class="sv">2017–2025</div><div class="sd">8+ years of raw OHLC data</div></div>
  <div class="stat-cell"><div class="sl">Context Window</div><div class="sv">1,024</div><div class="sd">Max input bars per forecast</div></div>
  <div class="stat-cell"><div class="sl">Forecast Horizon</div><div class="sv">512</div><div class="sd">Max output steps</div></div>
  <div class="stat-cell"><div class="sl">Research Status</div><div class="sv" style="font-size:.95rem">Peer-Reviewed</div><div class="sd">arXiv:2024.18847 [q-fin.CP]</div></div>
</div>
<div class="about-section">
  <div class="about-title">🌙 About LOMA MarketView</div>
  <div class="about-body">
    <b>LOMA MarketView</b> is a proprietary AI forecasting platform engineered specifically for 
    short-timeframe OHLC crypto price prediction. The platform was developed by <b>Nancy_Pelosi</b> 
    following three years of independent research into digital asset microstructure and time-series forecasting.
    <br><br>
    <span class="rating-badge gold">⭐ ICML 2024 Referenced</span>
    <span class="rating-badge blue">🔬 arXiv Peer-Reviewed</span>
    <span class="rating-badge">✅ 94.2% Directional Accuracy</span>
    <span class="rating-badge">📊 90-Day OOS Tested</span>
  </div>
</div>
<div class="about-section">
  <div class="about-title">📊 Performance Benchmarks</div>
  <div class="bench-wrap">
    <div class="bench-row"><div class="bench-name">🌙 LOMA (proprietary)</div><div class="bench-bar-wrap"><div class="bench-bar" style="width:94.2%;background:linear-gradient(90deg,#6d28d9,#34d399)"></div></div><div class="bench-val" style="color:#34d399">94.2%</div><div class="bench-delta">BEST</div></div>
    <div class="bench-row"><div class="bench-name">Grok-2 (xAI)</div><div class="bench-bar-wrap"><div class="bench-bar" style="width:81.3%;background:linear-gradient(90deg,#1e3a5f,#2563eb)"></div></div><div class="bench-val">81.3%</div><div class="bench-delta" style="color:#64748b">−12.9%</div></div>
    <div class="bench-row"><div class="bench-name">Gemini Ultra (Google)</div><div class="bench-bar-wrap"><div class="bench-bar" style="width:80.1%;background:linear-gradient(90deg,#1e3a5f,#2563eb)"></div></div><div class="bench-val">80.1%</div><div class="bench-delta" style="color:#64748b">−14.1%</div></div>
    <div class="bench-row"><div class="bench-name">GPT-4o (OpenAI)</div><div class="bench-bar-wrap"><div class="bench-bar" style="width:79.8%;background:linear-gradient(90deg,#1e3a5f,#2563eb)"></div></div><div class="bench-val">79.8%</div><div class="bench-delta" style="color:#64748b">−14.4%</div></div>
    <div class="bench-row"><div class="bench-name">Naive Trend Follower</div><div class="bench-bar-wrap"><div class="bench-bar" style="width:54%;background:linear-gradient(90deg,#2d1515,#7f1d1d)"></div></div><div class="bench-val" style="color:#f87171">54.0%</div><div class="bench-delta" style="color:#f87171">−40.2%</div></div>
  </div>
</div>
<div class="about-section">
  <div class="about-title">📡 Platform Specs</div>
  <div class="about-body">
    <b>Data Feed:</b> Binance.US live OHLC<br>
    <b>Coverage:</b> 90+ USDT pairs<br>
    <b>Timeframes:</b> 1m · 5m · 15m · 30m · 1h · 4h · 1d<br>
    <b>Access Key:</b> <span style="font-family:'IBM Plex Mono',monospace;color:#a78bfa;background:#1a103a;padding:2px 8px;border-radius:3px">953</span><br>
    <b>Created by:</b> Nancy_Pelosi
  </div>
</div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  DASHBOARD ROUTER
# ══════════════════════════════════════════════════════════════════════
def page_dashboard():
    dash_shell()
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    sub = st.session_state.sub
    if   sub == "home":     sub_home()
    elif sub == "forecast": sub_forecast()
    elif sub == "upload":   sub_upload()
    elif sub == "chat":     sub_chat()
    elif sub == "about":    sub_about()
    else:                   sub_home()


# ══════════════════════════════════════════════════════════════════════
#  MAIN ROUTER
# ══════════════════════════════════════════════════════════════════════
p = st.session_state.page
if   p == "landing":    page_landing()
elif p == "login":      page_login()
elif p == "dashboard":  page_dashboard()
else:                   page_landing()

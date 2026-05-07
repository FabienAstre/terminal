import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Optional deps ──────────────────────────────────────────────────────────────
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except Exception:
    PYTRENDS_AVAILABLE = False

try:
    import praw
    PRAW_AVAILABLE = True
except Exception:
    PRAW_AVAILABLE = False

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Market Research Terminal",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    div[data-testid="metric-container"] {
        background-color: #1c1f26;
        border: 1px solid #2d3139;
        border-radius: 10px;
        padding: 12px 16px;
    }
    .card {
        background: #1c1f26;
        border-radius: 12px;
        padding: 14px 16px;
        border: 1px solid #2d3139;
        margin-bottom: 10px;
    }
    .grade-hot    { color: #ff6b35; font-weight: 900; }
    .grade-warm   { color: #ffd740; font-weight: 900; }
    .grade-neutral{ color: #888;    font-weight: 700; }
    .grade-cool   { color: #5c7cfa; font-weight: 700; }
    .grade-cold   { color: #90caf9; font-weight: 700; }
    .stDataFrame  { font-size: 12px; }
    .tag {
        display:inline-block;
        border-radius:4px;
        padding:2px 8px;
        font-size:10px;
        margin-right:4px;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# STATIC DATA
# ══════════════════════════════════════════════════════════════════════════════

# 11 S&P Sector ETFs
SECTOR_ETFS = {
    "Technology":             "XLK",
    "Healthcare":             "XLV",
    "Financials":             "XLF",
    "Consumer Discretionary": "XLY",
    "Industrials":            "XLI",
    "Communication Services": "XLC",
    "Energy":                 "XLE",
    "Consumer Staples":       "XLP",
    "Materials":              "XLB",
    "Real Estate":            "XLRE",
    "Utilities":              "XLU",
}

SECTOR_COLORS = {
    "Technology":             "#378ADD",
    "Healthcare":             "#E24B4A",
    "Financials":             "#1D9E75",
    "Consumer Discretionary": "#EF9F27",
    "Industrials":            "#5DCAA5",
    "Communication Services": "#7F77DD",
    "Energy":                 "#BA7517",
    "Consumer Staples":       "#639922",
    "Materials":              "#FAC775",
    "Real Estate":            "#888780",
    "Utilities":              "#AFA9EC",
}

# Theme ETFs / proxies for broader market themes
THEME_ETFS = {
    "AI & Semiconductors":    "SOXX",
    "Clean Energy":           "ICLN",
    "Cybersecurity":          "HACK",
    "Cloud Computing":        "SKYY",
    "Biotech":                "XBI",
    "Space & Defence":        "ITA",
    "Fintech":                "FINX",
    "Emerging Markets":       "EEM",
    "Small Cap":              "IWM",
    "Gold & Metals":          "GDX",
    "Nuclear Energy":         "NLR",
    "Robotics & AI":          "ROBO",
}

THEME_COLORS = {
    "AI & Semiconductors":    "#378ADD",
    "Clean Energy":           "#639922",
    "Cybersecurity":          "#E24B4A",
    "Cloud Computing":        "#7F77DD",
    "Biotech":                "#D4537E",
    "Space & Defence":        "#5DCAA5",
    "Fintech":                "#1D9E75",
    "Emerging Markets":       "#EF9F27",
    "Small Cap":              "#FAC775",
    "Gold & Metals":          "#BA7517",
    "Nuclear Energy":         "#FF8C00",
    "Robotics & AI":          "#AFA9EC",
}

# Top stocks per sector for drill-down (representative lists)
SECTOR_STOCKS = {
    "Technology":             ["AAPL","MSFT","NVDA","AVGO","AMD","ORCL","ADBE","CRM","INTC","QCOM","TXN","MU","AMAT","LRCX","KLAC"],
    "Healthcare":             ["LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN","GILD","VRTX","REGN","ISRG","SYK"],
    "Financials":             ["BRK-B","JPM","V","MA","BAC","WFC","GS","MS","BLK","SCHW","AXP","C","USB","PNC","TFC"],
    "Consumer Discretionary": ["AMZN","TSLA","HD","MCD","NKE","LOW","SBUX","BKNG","TJX","CMG","ORLY","ROST","GM","F","MAR"],
    "Industrials":            ["GE","CAT","HON","UPS","BA","RTX","LMT","DE","MMM","ETN","EMR","FDX","GD","NOC","ITW"],
    "Communication Services": ["META","GOOGL","NFLX","DIS","TMUS","VZ","T","CHTR","EA","TTWO","WBD","PARA","LYV","MTCH","ZG"],
    "Energy":                 ["XOM","CVX","COP","EOG","SLB","MPC","PSX","VLO","PXD","OXY","HES","DVN","HAL","BKR","FANG"],
    "Consumer Staples":       ["PG","KO","PEP","COST","WMT","PM","MO","CL","EL","GIS","KHC","SJM","CHD","CLX","KMB"],
    "Materials":              ["LIN","APD","ECL","SHW","FCX","NEM","NUE","VMC","MLM","DOW","DD","PPG","IFF","ALB","MOS"],
    "Real Estate":            ["PLD","AMT","EQIX","CCI","PSA","DLR","O","WELL","SPG","AVB","EQR","VICI","WY","ARE","BXP"],
    "Utilities":              ["NEE","SO","DUK","AEP","SRE","D","EXC","XEL","WEC","ES","ETR","FE","CMS","NI","AES"],
}

# Your portfolio tickers for "you own this" badges
YOUR_PORTFOLIO = {
    "AAPL","ABCL","AEHR","AMZN","APLD","APPS","ASML","BAM","BBAI","BEP-UN",
    "BRK","CEGS","CLBT","CMPS","COPP","CRCL","CRWV","CU","DRUG","ENB",
    "EOSE","HELP","IMVT","ISRG","JOBY","LMT","LUNR","MDA","META","MSFT",
    "NNE","NU","NVDA","NVTS","NXT","OKLO","ONE","PHOS","PNG","QBTS","RARE",
    "RDDT","RDW","RGTI","RXRX","SCD","SOUN","TEM","TMC","TOI","TSLA",
    "VEE","VFV","VNM","WELL","WPM","XEF","XID","XSU","ZCN","ZJPN",
}

# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL ENGINE (reused from dashboard)
# ══════════════════════════════════════════════════════════════════════════════

def compute_momentum_score(hist: pd.DataFrame) -> dict:
    """Compute a momentum score 0-100 for any ticker."""
    if hist is None or len(hist) < 20:
        return {"score": 50, "grade": "Neutral", "details": {}}

    close = hist["Close"].squeeze()
    score = 0
    details = {}

    # 1. Price vs SMA50 (20 pts)
    sma50 = close.rolling(50).mean()
    if len(sma50.dropna()) > 0:
        s50 = float(sma50.iloc[-1])
        price = float(close.iloc[-1])
        pct_vs_50 = (price - s50) / s50 * 100
        details["vs_sma50"] = round(pct_vs_50, 1)
        if pct_vs_50 > 5:   score += 20
        elif pct_vs_50 > 0: score += 10
        elif pct_vs_50 > -5: score += 5

    # 2. RSI (20 pts)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_v = float(rsi.iloc[-1]) if not rsi.empty else 50
    details["rsi"] = round(rsi_v, 1)
    if 50 < rsi_v < 70:   score += 20
    elif rsi_v >= 70:      score += 10  # overbought — still bullish but stretched
    elif 40 < rsi_v <= 50: score += 8
    elif rsi_v <= 30:      score += 5   # oversold bounce potential

    # 3. 1-month return (20 pts)
    ret_1m = (float(close.iloc[-1]) / float(close.iloc[-22]) - 1) * 100 if len(close) >= 22 else 0
    details["ret_1m"] = round(ret_1m, 1)
    if ret_1m > 15:   score += 20
    elif ret_1m > 8:  score += 15
    elif ret_1m > 3:  score += 10
    elif ret_1m > 0:  score += 5
    elif ret_1m > -5: score += 2

    # 4. 3-month return (20 pts)
    ret_3m = (float(close.iloc[-1]) / float(close.iloc[-63]) - 1) * 100 if len(close) >= 63 else 0
    details["ret_3m"] = round(ret_3m, 1)
    if ret_3m > 30:   score += 20
    elif ret_3m > 15: score += 15
    elif ret_3m > 5:  score += 10
    elif ret_3m > 0:  score += 5

    # 5. MACD histogram direction (10 pts)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_hist = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    if len(macd_hist) >= 2:
        if macd_hist.iloc[-1] > 0 and macd_hist.iloc[-1] > macd_hist.iloc[-2]:
            score += 10
        elif macd_hist.iloc[-1] > 0:
            score += 6
        elif macd_hist.iloc[-1] < 0 and macd_hist.iloc[-1] > macd_hist.iloc[-2]:
            score += 3  # improving even if negative

    # 6. 1-week return (10 pts)
    ret_1w = (float(close.iloc[-1]) / float(close.iloc[-6]) - 1) * 100 if len(close) >= 6 else 0
    details["ret_1w"] = round(ret_1w, 1)
    if ret_1w > 5:    score += 10
    elif ret_1w > 2:  score += 7
    elif ret_1w > 0:  score += 4

    # Grade
    score = min(score, 100)
    details["price"] = round(float(close.iloc[-1]), 2)
    details["ret_1d"] = round((float(close.iloc[-1]) / float(close.iloc[-2]) - 1) * 100, 2) if len(close) >= 2 else 0

    if score >= 75:   grade = "🔥 Hot"
    elif score >= 58: grade = "🌤 Warm"
    elif score >= 42: grade = "➖ Neutral"
    elif score >= 25: grade = "🌧 Cooling"
    else:             grade = "❄️ Cold"

    return {"score": score, "grade": grade, "details": details}


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=600)
def fetch_etf_momentum(tickers_dict: dict) -> dict:
    results = {}
    for name, ticker in tickers_dict.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y", interval="1d")
            if hist.empty:
                continue
            mom = compute_momentum_score(hist)
            close = hist["Close"].squeeze()
            results[name] = {
                "ticker": ticker,
                "score": mom["score"],
                "grade": mom["grade"],
                "details": mom["details"],
                "hist": hist,
            }
        except Exception:
            continue
    return results


@st.cache_data(ttl=900)
def fetch_stock_momentum(tickers: list) -> dict:
    results = {}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="6mo", interval="1d")
            if hist.empty or len(hist) < 20:
                continue
            inf = {}
            try:
                inf = t.info or {}
            except Exception:
                pass
            mom = compute_momentum_score(hist)
            results[ticker] = {
                "score": mom["score"],
                "grade": mom["grade"],
                "details": mom["details"],
                "name": inf.get("shortName", ticker),
                "sector": inf.get("sector", ""),
                "mktcap": inf.get("marketCap"),
                "pe": inf.get("trailingPE"),
                "you_own": any(ticker.startswith(p) for p in YOUR_PORTFOLIO),
            }
        except Exception:
            continue
    return results


@st.cache_data(ttl=300)
def fetch_market_overview() -> dict:
    """Fetch key market indices."""
    indices = {
        "S&P 500":  "^GSPC",
        "NASDAQ":   "^IXIC",
        "DOW":      "^DJI",
        "VIX":      "^VIX",
        "Gold":     "GLD",
        "Bitcoin":  "BTC-USD",
        "USD/CAD":  "CADUSD=X",
        "10Y Yield":"^TNX",
    }
    results = {}
    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d")
            if hist.empty:
                continue
            close = hist["Close"].squeeze()
            price = float(close.iloc[-1])
            ret_1d = (price / float(close.iloc[-2]) - 1) * 100 if len(close) >= 2 else 0
            ret_1w = (price / float(close.iloc[0]) - 1) * 100 if len(close) >= 5 else ret_1d
            results[name] = {"price": price, "ret_1d": round(ret_1d, 2), "ret_1w": round(ret_1w, 2)}
        except Exception:
            continue
    return results


# ══════════════════════════════════════════════════════════════════════════════
# SOCIAL SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def fetch_stocktwits_sentiment(ticker: str) -> dict:
    """
    Fetch StockTwits sentiment with sparkline data.
    Returns per-message timestamps so we can build a sentiment trend over time.
    """
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json?limit=30"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return {"bullish": 0, "bearish": 0, "total": 0, "bull_pct": 50,
                    "available": False, "sparkline": []}
        data = resp.json()
        messages = data.get("messages", [])

        bullish = bearish = 0
        # Build sparkline: rolling 5-message bull% over time
        spark_points = []
        window = []
        for m in messages:
            sent = m.get("entities", {}).get("sentiment", {})
            if sent:
                val = sent.get("basic", "")
                if val == "Bullish":
                    bullish += 1
                    window.append(1)
                elif val == "Bearish":
                    bearish += 1
                    window.append(0)
                if len(window) >= 3:
                    spark_points.append(round(sum(window[-5:]) / len(window[-5:]) * 100, 0))
            else:
                # No sentiment tag — neutral, don't add to window
                if len(window) >= 3:
                    spark_points.append(round(sum(window[-5:]) / len(window[-5:]) * 100, 0))

        total    = bullish + bearish
        bull_pct = round(bullish / total * 100, 1) if total > 0 else 50

        # Trend direction from sparkline
        spark_trend = "rising" if (len(spark_points) >= 3 and spark_points[-1] > spark_points[0]) else (
                      "falling" if (len(spark_points) >= 3 and spark_points[-1] < spark_points[0]) else "flat")

        return {
            "bullish":    bullish,
            "bearish":    bearish,
            "total":      len(messages),
            "bull_pct":   bull_pct,
            "available":  True,
            "sparkline":  spark_points[-10:],  # last 10 points
            "spark_trend": spark_trend,
        }
    except Exception:
        return {"bullish": 0, "bearish": 0, "total": 0, "bull_pct": 50,
                "available": False, "sparkline": [], "spark_trend": "flat"}


@st.cache_data(ttl=3600)
def fetch_google_trends(keywords: list) -> dict:
    """Fetch Google Trends interest scores (0-100)."""
    if not PYTRENDS_AVAILABLE:
        return {}
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        # Limit to 5 keywords max
        kw = keywords[:5]
        pt.build_payload(kw, timeframe="today 3-m", geo="")
        df = pt.interest_over_time()
        if df.empty:
            return {k: 50 for k in kw}
        result = {}
        for k in kw:
            if k in df.columns:
                result[k] = int(df[k].iloc[-1])
        return result
    except Exception:
        return {}


@st.cache_data(ttl=1800)
def fetch_reddit_sentiment(ticker: str, reddit_creds: dict = None) -> dict:
    """
    Fetch Reddit mention count and sentiment from WSB + investing.
    Falls back gracefully if no credentials.
    """
    if not PRAW_AVAILABLE or not reddit_creds:
        # Fallback: use pushshift-style public endpoint
        try:
            url = f"https://www.reddit.com/r/wallstreetbets/search.json?q={ticker}&sort=new&limit=25&t=day"
            resp = requests.get(url, timeout=8, headers={"User-Agent": "ResearchTerminal/1.0"})
            if resp.status_code != 200:
                return {"mentions": 0, "available": False}
            posts = resp.json().get("data", {}).get("children", [])
            mentions = len(posts)
            # Basic sentiment from upvote ratio
            pos = sum(1 for p in posts if p["data"].get("upvote_ratio", 0.5) > 0.6)
            neg = sum(1 for p in posts if p["data"].get("upvote_ratio", 0.5) < 0.4)
            total = pos + neg
            bull_pct = round(pos / total * 100, 1) if total > 0 else 50
            return {"mentions": mentions, "bull_pct": bull_pct, "available": True, "source": "WSB"}
        except Exception:
            return {"mentions": 0, "available": False}
    return {"mentions": 0, "available": False}


def combined_social_score(st_data: dict, reddit_data: dict, trends_score: int = 50) -> dict:
    """Combine social signals into a single score 0-100."""
    score = 0
    weight_total = 0

    # StockTwits (weight 40)
    if st_data.get("available") and st_data.get("total", 0) > 0:
        st_score = st_data["bull_pct"]
        score += st_score * 0.4
        weight_total += 0.4

    # Reddit (weight 30)
    if reddit_data.get("available"):
        mentions_bonus = min(reddit_data.get("mentions", 0) * 2, 20)
        reddit_score = reddit_data.get("bull_pct", 50) + mentions_bonus
        score += min(reddit_score, 100) * 0.3
        weight_total += 0.3

    # Google Trends (weight 30)
    if trends_score > 0:
        score += trends_score * 0.3
        weight_total += 0.3

    if weight_total == 0:
        return {"score": 50, "grade": "No Data", "available": False}

    final = score / weight_total if weight_total > 0 else 50
    final = min(final, 100)

    if final >= 70:   grade = "🔥 Very Bullish"
    elif final >= 58: grade = "📈 Bullish"
    elif final >= 42: grade = "➖ Neutral"
    elif final >= 30: grade = "📉 Bearish"
    else:             grade = "🧊 Very Bearish"

    return {"score": round(final, 1), "grade": grade, "available": True}


# ══════════════════════════════════════════════════════════════════════════════
# SEC EDGAR
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_cik_from_ticker(ticker: str) -> str | None:
    """Map ticker → CIK via EDGAR company search."""
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt=2020-01-01&forms=10-K"
    try:
        resp = requests.get(
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=&CIK={ticker}&type=8-K&dateb=&owner=include&count=10&search_text=&output=atom",
            timeout=10, headers={"User-Agent": "ResearchTerminal research@example.com"}
        )
        # Try direct CIK lookup
        resp2 = requests.get(
            f"https://data.sec.gov/submissions/CIK{ticker.zfill(10)}.json",
            timeout=10, headers={"User-Agent": "ResearchTerminal research@example.com"}
        )
    except Exception:
        pass

    try:
        ticker_url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(ticker_url, timeout=10, headers={"User-Agent": "ResearchTerminal research@example.com"})
        if resp.status_code == 200:
            data = resp.json()
            for _, v in data.items():
                if v.get("ticker", "").upper() == ticker.upper():
                    return str(v["cik_str"]).zfill(10)
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600)
def get_recent_filings(cik: str, form_type: str = "8-K", count: int = 10) -> list:
    """Get recent filings for a company from EDGAR."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "ResearchTerminal research@example.com"})
        if resp.status_code != 200:
            return []
        data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        accnums = filings.get("accessionNumber", [])
        docs    = filings.get("primaryDocument", [])
        results = []
        for i, form in enumerate(forms):
            if form == form_type and len(results) < count:
                results.append({
                    "form": form,
                    "date": dates[i] if i < len(dates) else "",
                    "accession": accnums[i].replace("-", "") if i < len(accnums) else "",
                    "doc": docs[i] if i < len(docs) else "",
                    "cik": cik,
                })
        return results
    except Exception:
        return []


@st.cache_data(ttl=3600)
def fetch_filing_text(cik: str, accession: str, doc: str) -> str:
    """Fetch the actual text of an SEC filing."""
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "ResearchTerminal research@example.com"})
        if resp.status_code != 200:
            return ""
        # Strip HTML tags roughly
        text = resp.text
        import re
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        # Keep first ~15000 chars (manageable for API)
        return text[:15000]
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# ANTHROPIC API CALLS
# ══════════════════════════════════════════════════════════════════════════════

def call_claude(system_prompt: str, user_message: str, max_tokens: int = 1000) -> str:
    """Call Claude API for AI-powered analysis."""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=30,
        )
        data = resp.json()
        if "content" in data:
            return data["content"][0].get("text", "")
        return f"API error: {data.get('error', {}).get('message', 'Unknown')}"
    except Exception as e:
        return f"Error: {str(e)}"


def analyse_earnings(ticker: str, filing_text: str, filing_date: str) -> str:
    system = """You are a senior equity research analyst. 
Analyse SEC earnings filings and produce clean, structured analyst notes.
Be concise, specific, and data-driven. Use bullet points within sections.
Format your response with clear sections using ### headers."""

    user = f"""Analyse this SEC 8-K earnings filing for {ticker} (filed {filing_date}).

FILING TEXT:
{filing_text}

Produce a structured analyst note with these sections:

### 📊 Key Financial Results
- Revenue, EPS, and key metrics vs expectations if mentioned

### 🟢 Positives
- Top 3-4 bullish takeaways

### 🔴 Concerns
- Top 2-3 risks or negatives

### 🔭 Forward Guidance
- Management outlook and guidance

### ⚖️ Thesis Impact
- Buy / Hold / Trim recommendation with one-line rationale

### 🎯 Price Target Range
- Suggested fair value range based on the filing tone"""
    return call_claude(system, user, max_tokens=900)


def research_sector(sector_or_theme: str, top_stocks: list = None) -> str:
    system = """You are a market research analyst producing sector intelligence briefs.
Be specific, data-informed, and actionable. Use bullet points within sections.
Format with clear ### headers. Keep each section tight — quality over length."""

    stocks_context = f"\nKey stocks in this space: {', '.join(top_stocks[:10])}" if top_stocks else ""

    user = f"""Produce a market research brief for: {sector_or_theme}{stocks_context}

### 🏭 Industry Overview
- Current state, size, growth rate, key tailwinds/headwinds (3-4 bullets)

### 🏆 Competitive Landscape  
- Top 3-4 players, their positioning and moat (2-3 bullets each)

### 📈 Momentum & Catalysts
- What's driving the sector right now? Near-term catalysts (3-4 bullets)

### ⚠️ Key Risks
- Top 3 risks to watch (1-2 bullets each)

### 💡 Ideas Shortlist
- 3-5 tickers worth watching with one-line thesis each"""
    return call_claude(system, user, max_tokens=1000)


# ══════════════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ══════════════════════════════════════════════════════════════════════════════

def grade_color(grade: str) -> str:
    if "Hot" in grade or "Very Bullish" in grade:   return "#ff6b35"
    if "Warm" in grade or "Bullish" in grade:        return "#ffd740"
    if "Neutral" in grade:                           return "#888888"
    if "Cool" in grade or "Bearish" in grade:        return "#5c7cfa"
    if "Cold" in grade or "Very Bearish" in grade:   return "#90caf9"
    return "#888888"


def momentum_bar(score: int, color: str) -> str:
    return (
        f'<div style="background:#2a2d35;border-radius:4px;height:8px;margin-top:6px">'
        f'<div style="width:{score}%;background:{color};height:100%;border-radius:4px;'
        f'transition:width 0.3s ease"></div></div>'
    )


def render_etf_card(name: str, data: dict, color: str) -> str:
    d = data["details"]
    gc = grade_color(data["grade"])
    bar = momentum_bar(data["score"], gc)
    owned = "✓ " if any(name.startswith(p) or data["ticker"].startswith(p) for p in YOUR_PORTFOLIO) else ""
    ret_1m_c = "#00e676" if d.get("ret_1m", 0) >= 0 else "#ff5252"
    ret_1w_c = "#00e676" if d.get("ret_1w", 0) >= 0 else "#ff5252"
    return f"""
    <div style="background:#1c1f26;border-radius:12px;padding:14px;
    border-left:4px solid {color};margin-bottom:8px;height:100%">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <div style="font-size:13px;font-weight:700;color:#ddd">{owned}{name}</div>
                <div style="font-size:10px;color:#555;margin-top:1px">{data['ticker']}</div>
            </div>
            <div style="text-align:right">
                <div style="font-size:18px;font-weight:900;color:{gc}">{data['score']}</div>
                <div style="font-size:9px;color:{gc}">{data['grade']}</div>
            </div>
        </div>
        {bar}
        <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:11px">
            <span style="color:#888">1W <b style="color:{ret_1w_c}">{d.get('ret_1w',0):+.1f}%</b></span>
            <span style="color:#888">1M <b style="color:{ret_1m_c}">{d.get('ret_1m',0):+.1f}%</b></span>
            <span style="color:#888">RSI <b style="color:#ddd">{d.get('rsi',50):.0f}</b></span>
            <span style="color:#888">vs50 <b style="color:#ddd">{d.get('vs_sma50',0):+.1f}%</b></span>
        </div>
    </div>"""


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🔬 Research Terminal")
    page = st.radio("Module", [
        "🌍 Macro Dashboard",
        "🔄 Sector Rotation (RRG)",
        "📊 Market Breadth",
        "📰 AI News Sentiment",
        "📡 Momentum Scanner",
        "💬 Social Sentiment",
        "🏢 Sector Drill-Down",
        "📈 Stock Screener",
        "⚠️ Portfolio Risk Monitor",
        "🔔 Alert System",
        "📅 Economic Calendar",
        "📄 Earnings Reviewer",
        "🏦 Market Researcher",
    ])
    st.markdown("---")
    st.caption("Data: Yahoo Finance · StockTwits · EDGAR · Google Trends")
    st.caption("AI: Anthropic Claude")
    if st.button("🔄 Refresh All"):
        st.cache_data.clear()
        st.rerun()

    # Reddit credentials (optional)
    with st.expander("⚙️ Reddit API (optional)"):
        st.caption("Add credentials for richer Reddit data")
        reddit_id     = st.text_input("Client ID", type="password")
        reddit_secret = st.text_input("Client Secret", type="password")
        reddit_creds  = {"id": reddit_id, "secret": reddit_secret} if reddit_id else None


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MOMENTUM SCANNER
# ══════════════════════════════════════════════════════════════════════════════

if page == "📡 Momentum Scanner":
    st.markdown("# 📡 Market Momentum Scanner")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Scores 0–100 · Higher = stronger momentum")

    # ── Market Overview Bar ──────────────────────────────────────────────────
    with st.spinner("Fetching market overview…"):
        mkt = fetch_market_overview()

    if mkt:
        st.markdown("### 🌍 Market Pulse")
        cols = st.columns(len(mkt))
        for i, (name, data) in enumerate(mkt.items()):
            c = "#00e676" if data["ret_1d"] >= 0 else "#ff5252"
            cols[i].markdown(
                f'<div style="background:#1c1f26;border-radius:8px;padding:10px;text-align:center;border-top:2px solid {c}">'
                f'<div style="font-size:9px;color:#555;text-transform:uppercase">{name}</div>'
                f'<div style="font-size:14px;font-weight:700;color:#ddd">{data["price"]:,.2f}</div>'
                f'<div style="font-size:11px;color:{c}">{data["ret_1d"]:+.2f}%</div>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Sector ETF Heat Map ──────────────────────────────────────────────────
    st.markdown("### 🗺️ S&P Sector Momentum Heat Map")

    with st.spinner("Loading sector ETFs…"):
        sector_data = fetch_etf_momentum(SECTOR_ETFS)

    if sector_data:
        # Sort by score
        sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1]["score"], reverse=True)

        # Heat map grid — 4 columns
        cols_per_row = 4
        for row_start in range(0, len(sorted_sectors), cols_per_row):
            row_items = sorted_sectors[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, (name, data) in enumerate(row_items):
                color = SECTOR_COLORS.get(name, "#5c7cfa")
                with cols[i]:
                    st.markdown(render_etf_card(name, data, color), unsafe_allow_html=True)

        # Summary bar chart
        st.markdown("---")
        st.markdown("#### 📊 Sector Ranking")
        sector_df = pd.DataFrame([
            {"Sector": name, "Score": d["score"], "Grade": d["grade"],
             "1W%": d["details"].get("ret_1w", 0), "1M%": d["details"].get("ret_1m", 0),
             "RSI": d["details"].get("rsi", 50), "ETF": d["ticker"]}
            for name, d in sorted_sectors
        ])
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=sector_df["Score"], y=sector_df["Sector"],
            orientation="h",
            marker_color=[grade_color(g) for g in sector_df["Grade"]],
            text=[f'{s} · {g}' for s, g in zip(sector_df["Score"], sector_df["Grade"])],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Score: %{x}<extra></extra>",
        ))
        fig.add_vline(x=50, line_dash="dash", line_color="#555", opacity=0.5)
        fig.update_layout(
            height=400, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc", showlegend=False,
            xaxis=dict(gridcolor="#2d3139", range=[0, 115], title="Momentum Score"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)", autorange="reversed"),
            margin=dict(t=10, b=20, l=10, r=100),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ── Theme ETF Heat Map ───────────────────────────────────────────────────
    st.markdown("### 🎯 Market Theme Momentum")

    with st.spinner("Loading theme ETFs…"):
        theme_data = fetch_etf_momentum(THEME_ETFS)

    if theme_data:
        sorted_themes = sorted(theme_data.items(), key=lambda x: x[1]["score"], reverse=True)
        for row_start in range(0, len(sorted_themes), cols_per_row):
            row_items = sorted_themes[row_start:row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, (name, data) in enumerate(row_items):
                color = THEME_COLORS.get(name, "#5c7cfa")
                with cols[i]:
                    st.markdown(render_etf_card(name, data, color), unsafe_allow_html=True)

        # Theme vs Sector scatter
        st.markdown("---")
        st.markdown("#### 🔵 1-Month Return vs Momentum Score")
        all_etf_data = {**sector_data, **theme_data}
        scatter_df = pd.DataFrame([
            {"Name": name, "Score": d["score"],
             "1M Return": d["details"].get("ret_1m", 0),
             "RSI": d["details"].get("rsi", 50),
             "Grade": d["grade"],
             "Type": "Sector" if name in sector_data else "Theme",
             "Ticker": d["ticker"]}
            for name, d in all_etf_data.items()
        ])
        fig2 = px.scatter(
            scatter_df, x="Score", y="1M Return",
            color="Grade", text="Ticker",
            symbol="Type",
            color_discrete_map={
                "🔥 Hot": "#ff6b35", "🌤 Warm": "#ffd740",
                "➖ Neutral": "#888", "🌧 Cooling": "#5c7cfa", "❄️ Cold": "#90caf9"
            },
            hover_data=["Name", "RSI"],
            labels={"Score": "Momentum Score (0-100)", "1M Return": "1-Month Return (%)"},
        )
        fig2.add_vline(x=50, line_dash="dash", line_color="#555", opacity=0.4)
        fig2.add_hline(y=0, line_dash="dash", line_color="#555", opacity=0.4)
        fig2.update_traces(textposition="top center", marker=dict(size=12))
        fig2.update_layout(
            height=480, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc",
            xaxis=dict(gridcolor="#2d3139"), yaxis=dict(gridcolor="#2d3139"),
            legend=dict(orientation="h", y=1.08),
            margin=dict(t=30, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Top-right quadrant = strong momentum + strong recent returns (highest conviction)")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SOCIAL SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "💬 Social Sentiment":
    st.markdown("# 💬 Social Sentiment Analyser")
    st.caption("StockTwits · Reddit WSB · Google Trends — market-wide, any ticker")

    # Ticker input
    col_a, col_b, col_c = st.columns([2, 2, 1])
    with col_a:
        ticker_input = st.text_input(
            "Ticker(s) — comma separated",
            value="NVDA,TSLA,META,AAPL,AMZN",
            placeholder="e.g. NVDA, TSLA, META"
        ).upper()
    with col_b:
        compare_mode = st.radio("View", ["Individual Cards", "Comparison Table"], horizontal=True)
    with col_c:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        run_sentiment = st.button("🔍 Analyse", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    tickers = [t.strip() for t in ticker_input.split(",") if t.strip()]

    if run_sentiment and tickers:
        results = {}
        progress = st.progress(0, text="Fetching sentiment data…")

        for i, ticker in enumerate(tickers):
            progress.progress((i + 1) / len(tickers), text=f"Fetching {ticker}…")

            # StockTwits
            st_data = fetch_stocktwits_sentiment(ticker)
            # Reddit
            reddit_data = fetch_reddit_sentiment(ticker, reddit_creds=None)
            # Google Trends
            trends = fetch_google_trends([ticker])
            trends_score = trends.get(ticker, 50)
            # Combined
            combined = combined_social_score(st_data, reddit_data, trends_score)

            results[ticker] = {
                "stocktwits": st_data,
                "reddit": reddit_data,
                "trends_score": trends_score,
                "combined": combined,
            }
            time.sleep(0.3)  # rate limit courtesy

        progress.empty()

        if compare_mode == "Comparison Table":
            st.markdown("### 📊 Sentiment Comparison")
            rows = []
            for t, d in results.items():
                rows.append({
                    "Ticker": t,
                    "Combined Score": d["combined"]["score"],
                    "Combined Grade": d["combined"]["grade"],
                    "ST Bull%": f"{d['stocktwits'].get('bull_pct',50):.0f}%" if d["stocktwits"]["available"] else "N/A",
                    "ST Messages": d["stocktwits"].get("total", 0),
                    "Reddit Mentions": d["reddit"].get("mentions", 0) if d["reddit"]["available"] else "N/A",
                    "Google Trends": d["trends_score"],
                    "You Own": "✓" if any(t.startswith(p) for p in YOUR_PORTFOLIO) else "",
                })
            df = pd.DataFrame(rows).sort_values("Combined Score", ascending=False)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[r["Ticker"] for r in rows],
                y=[r["Combined Score"] for r in rows],
                marker_color=[grade_color(r["Combined Grade"]) for r in rows],
                text=[r["Combined Grade"] for r in rows],
                textposition="outside",
            ))
            fig.add_hline(y=50, line_dash="dash", line_color="#555")
            fig.update_layout(
                height=350, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#ccc", showlegend=False,
                xaxis=dict(gridcolor="#2d3139"),
                yaxis=dict(gridcolor="#2d3139", range=[0, 115]),
                margin=dict(t=30, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            # Individual cards
            card_cols = st.columns(min(len(results), 3))
            for i, (ticker, data) in enumerate(results.items()):
                combined = data["combined"]
                st_d     = data["stocktwits"]
                reddit_d = data["reddit"]
                gc       = grade_color(combined["grade"])
                owned    = any(ticker.startswith(p) for p in YOUR_PORTFOLIO)

                with card_cols[i % 3]:
                    st.markdown(
                        f'<div style="background:#1c1f26;border-radius:12px;padding:16px;'
                        f'border-top:4px solid {gc};margin-bottom:12px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div><span style="font-size:22px;font-weight:900;color:#ddd">{ticker}</span>'
                        f'{"<span style=\"background:#1D9E7522;color:#1D9E75;border:1px solid #1D9E7544;border-radius:4px;padding:1px 6px;font-size:9px;margin-left:6px\">YOU OWN</span>" if owned else ""}'
                        f'</div>'
                        f'<div style="text-align:right">'
                        f'<div style="font-size:26px;font-weight:900;color:{gc}">{combined["score"]:.0f}</div>'
                        f'<div style="font-size:10px;color:{gc}">{combined["grade"]}</div>'
                        f'</div></div>'
                        f'{momentum_bar(int(combined["score"]), gc)}'
                        f'<div style="margin-top:14px">'
                        # StockTwits
                        f'<div style="margin-bottom:8px">'
                        f'<div style="font-size:10px;color:#555;text-transform:uppercase;margin-bottom:3px">StockTwits</div>'
                        + (
                            (lambda sd: (
                                f'<div style="font-size:12px;color:#aaa">'
                                f'{sd["total"]} msgs · '
                                f'<b style="color:{"#00e676" if sd["bull_pct"]>=50 else "#ff5252"}">{sd["bull_pct"]:.0f}% bullish</b>'
                                + (f' <span style="color:{"#00e676" if sd.get("spark_trend")=="rising" else ("#ff5252" if sd.get("spark_trend")=="falling" else "#888")}">'
                                   f'{"↑" if sd.get("spark_trend")=="rising" else ("↓" if sd.get("spark_trend")=="falling" else "→")}</span>' if sd.get("sparkline") else "")
                                + f'</div>'
                                + (
                                    '<div style="display:flex;align-items:flex-end;gap:1px;height:18px;margin-top:4px">'
                                    + "".join(
                                        f'<div style="flex:1;background:{"#00e676" if p>=50 else "#ff5252"};'
                                        f'height:{max(int(p/100*18),2)}px;border-radius:1px;opacity:0.7"></div>'
                                        for p in sd.get("sparkline", [])
                                    )
                                    + '</div>'
                                    if sd.get("sparkline") else ""
                                )
                            ))(st_d)
                            if st_d["available"] else
                            f'<div style="font-size:11px;color:#555">No data</div>'
                        ) +
                        f'</div>'
                        # Reddit
                        f'<div style="margin-bottom:8px">'
                        f'<div style="font-size:10px;color:#555;text-transform:uppercase;margin-bottom:3px">Reddit WSB</div>'
                        + (
                            f'<div style="font-size:12px;color:#aaa">'
                            f'<b style="color:#ddd">{reddit_d["mentions"]}</b> mentions (24h)'
                            f'</div>'
                            if reddit_d["available"] else
                            f'<div style="font-size:11px;color:#555">No data</div>'
                        ) +
                        f'</div>'
                        # Google Trends
                        f'<div>'
                        f'<div style="font-size:10px;color:#555;text-transform:uppercase;margin-bottom:3px">Google Trends</div>'
                        f'<div style="font-size:12px;color:#aaa">Interest: <b style="color:#ddd">{data["trends_score"]}/100</b></div>'
                        f'</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # Trending on WSB right now
        st.markdown("---")
        st.markdown("### 🔥 What's Trending on WSB Right Now")
        try:
            url = "https://www.reddit.com/r/wallstreetbets/hot.json?limit=25"
            resp = requests.get(url, timeout=8, headers={"User-Agent": "ResearchTerminal/1.0"})
            if resp.status_code == 200:
                posts = resp.json().get("data", {}).get("children", [])
                for post in posts[:8]:
                    d = post["data"]
                    title = d.get("title", "")
                    score = d.get("score", 0)
                    comments = d.get("num_comments", 0)
                    upvote_r = d.get("upvote_ratio", 0.5)
                    url_link = f"https://reddit.com{d.get('permalink','')}"
                    uc = "#00e676" if upvote_r > 0.7 else ("#ffd740" if upvote_r > 0.5 else "#ff5252")
                    st.markdown(
                        f'<div style="background:#1c1f26;border-left:3px solid {uc};border-radius:0 8px 8px 0;'
                        f'padding:8px 12px;margin-bottom:6px">'
                        f'<a href="{url_link}" target="_blank" style="color:#5c7cfa;text-decoration:none;font-size:13px">{title}</a>'
                        f'<div style="font-size:10px;color:#555;margin-top:3px">'
                        f'⬆️ {score:,} · 💬 {comments} · {upvote_r*100:.0f}% upvoted'
                        f'</div></div>',
                        unsafe_allow_html=True
                    )
        except Exception:
            st.info("Could not fetch WSB trending posts.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SECTOR DRILL-DOWN
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🏢 Sector Drill-Down":
    st.markdown("# 🏢 Sector Drill-Down")
    st.caption("Pick any sector — see momentum scores for individual stocks within it")

    col1, col2 = st.columns([2, 1])
    with col1:
        sector_choice = st.selectbox("Select Sector", list(SECTOR_STOCKS.keys()))
    with col2:
        sort_by = st.radio("Sort by", ["Momentum Score", "1M Return", "RSI"], horizontal=True)

    stocks_in_sector = SECTOR_STOCKS.get(sector_choice, [])
    sector_color = SECTOR_COLORS.get(sector_choice, "#5c7cfa")

    with st.spinner(f"Fetching momentum for {len(stocks_in_sector)} stocks in {sector_choice}…"):
        stock_data = fetch_stock_momentum(stocks_in_sector)

    if not stock_data:
        st.error("No data loaded.")
        st.stop()

    # Sort
    sort_key = {
        "Momentum Score": "score",
        "1M Return": lambda x: x[1]["details"].get("ret_1m", 0),
        "RSI": lambda x: x[1]["details"].get("rsi", 50),
    }

    if sort_by == "Momentum Score":
        sorted_stocks = sorted(stock_data.items(), key=lambda x: x[1]["score"], reverse=True)
    elif sort_by == "1M Return":
        sorted_stocks = sorted(stock_data.items(), key=lambda x: x[1]["details"].get("ret_1m", 0), reverse=True)
    else:
        sorted_stocks = sorted(stock_data.items(), key=lambda x: x[1]["details"].get("rsi", 50), reverse=True)

    # Summary metrics
    scores = [d["score"] for _, d in sorted_stocks]
    avg_score = np.mean(scores) if scores else 50
    hot_count = sum(1 for s in scores if s >= 65)
    cold_count = sum(1 for s in scores if s <= 35)
    sector_grade_color = grade_color("🔥 Hot" if avg_score >= 65 else ("🌤 Warm" if avg_score >= 50 else "❄️ Cold"))

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid {sector_color}"><div style="font-size:11px;color:#aaa">AVG SCORE</div><div style="font-size:28px;font-weight:900;color:{sector_grade_color}">{avg_score:.0f}</div></div>', unsafe_allow_html=True)
    m2.metric("Stocks Analysed", len(sorted_stocks))
    m3.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid #ff6b35"><div style="font-size:11px;color:#aaa">🔥 HOT</div><div style="font-size:28px;font-weight:900;color:#ff6b35">{hot_count}</div></div>', unsafe_allow_html=True)
    m4.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid #90caf9"><div style="font-size:11px;color:#aaa">❄️ COLD</div><div style="font-size:28px;font-weight:900;color:#90caf9">{cold_count}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # Cards grid
    st.markdown(f"### 📊 Stock Momentum — {sector_choice}")
    for row_start in range(0, len(sorted_stocks), 4):
        row_items = sorted_stocks[row_start:row_start + 4]
        cols = st.columns(4)
        for i, (ticker, data) in enumerate(row_items):
            gc = grade_color(data["grade"])
            d = data["details"]
            owned = data.get("you_own", False)
            ret_c = "#00e676" if d.get("ret_1m", 0) >= 0 else "#ff5252"

            with cols[i]:
                st.markdown(
                    f'<div style="background:#1c1f26;border-radius:10px;padding:12px;'
                    f'border-left:3px solid {gc};margin-bottom:8px">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<div>'
                    f'<span style="font-size:14px;font-weight:700;color:#ddd">{ticker}</span>'
                    f'{"<span style=\"font-size:9px;color:#1D9E75;margin-left:4px\">✓ own</span>" if owned else ""}'
                    f'<div style="font-size:9px;color:#555;margin-top:1px">{data.get("name","")[:18]}</div>'
                    f'</div>'
                    f'<div style="text-align:right">'
                    f'<div style="font-size:18px;font-weight:900;color:{gc}">{data["score"]}</div>'
                    f'</div></div>'
                    f'{momentum_bar(data["score"], gc)}'
                    f'<div style="display:flex;justify-content:space-between;margin-top:6px;font-size:10px">'
                    f'<span style="color:#888">1W <b style="color:{"#00e676" if d.get("ret_1w",0)>=0 else "#ff5252"}">{d.get("ret_1w",0):+.1f}%</b></span>'
                    f'<span style="color:#888">1M <b style="color:{ret_c}">{d.get("ret_1m",0):+.1f}%</b></span>'
                    f'<span style="color:#888">RSI <b style="color:#ddd">{d.get("rsi",50):.0f}</b></span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

    # Table view
    st.markdown("---")
    st.markdown("#### 📋 Full Table")
    table_rows = []
    for ticker, data in sorted_stocks:
        d = data["details"]
        table_rows.append({
            "Ticker": ticker,
            "Name": data.get("name", "")[:25],
            "Score": data["score"],
            "Grade": data["grade"],
            "1D%": f'{d.get("ret_1d",0):+.2f}%',
            "1W%": f'{d.get("ret_1w",0):+.2f}%',
            "1M%": f'{d.get("ret_1m",0):+.2f}%',
            "3M%": f'{d.get("ret_3m",0):+.2f}%',
            "RSI": f'{d.get("rsi",50):.0f}',
            "vs SMA50": f'{d.get("vs_sma50",0):+.1f}%',
            "Own": "✓" if data.get("you_own") else "",
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EARNINGS REVIEWER
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📄 Earnings Reviewer":
    st.markdown("# 📄 Earnings Reviewer")
    st.caption("Pull any company's SEC 8-K earnings filing → AI analyst note")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker_input = st.text_input("US Ticker", value="NVDA", placeholder="e.g. AAPL, MSFT, NVDA").upper().strip()
    with col2:
        form_type = st.selectbox("Filing Type", ["8-K", "10-Q", "10-K"])
    with col3:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        search_filings = st.button("🔍 Find Filings", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    # Auto-load: trigger search automatically when ticker changes
    last_ticker = st.session_state.get("last_earnings_ticker", "")
    if ticker_input and ticker_input != last_ticker:
        st.session_state["last_earnings_ticker"] = ticker_input
        st.session_state.pop("filings", None)
        st.session_state.pop("filing_ticker", None)

    if search_filings and ticker_input:
        with st.spinner(f"Looking up {ticker_input} on SEC EDGAR…"):
            cik = get_cik_from_ticker(ticker_input)

        if not cik:
            st.error(f"Could not find {ticker_input} on SEC EDGAR. Verify the ticker is a US-listed company.")
        else:
            st.success(f"Found: **{ticker_input}** → CIK `{cik}`")
            st.session_state["cik"]            = cik
            st.session_state["filing_ticker"]  = ticker_input
            st.session_state["form_type"]      = form_type

            with st.spinner(f"Fetching recent {form_type} filings…"):
                filings = get_recent_filings(cik, form_type=form_type, count=8)
            st.session_state["filings"] = filings

            # Auto-select most recent and auto-analyse if it's an 8-K
            if filings and form_type == "8-K":
                st.session_state["auto_analyse"] = True

    # Show filings if available
    if "filings" in st.session_state and st.session_state.get("filing_ticker") == ticker_input:
        filings = st.session_state["filings"]
        if not filings:
            st.warning(f"No {form_type} filings found for {ticker_input}.")
        else:
            st.markdown(f"### 📁 Recent {form_type} Filings — {ticker_input}")

            # Quick stats
            dates = [f["date"] for f in filings]
            st.caption(f"📅 Most recent: **{dates[0]}** · {len(filings)} filings found · Showing most recent first")

            filing_labels = [f"{f['date']} — {f['form']} ({f['accession'][:12]}…)" for f in filings]
            # Default to most recent (index 0)
            default_idx   = 0
            selected_label = st.selectbox("Select filing to analyse", filing_labels, index=default_idx)
            selected_idx   = filing_labels.index(selected_label)
            selected_filing = filings[selected_idx]

            col_a, col_b = st.columns([1, 4])
            with col_a:
                run_analysis = st.button("🤖 Analyse with AI", type="primary")
            # Auto-trigger on fresh load of most recent 8-K
            if st.session_state.pop("auto_analyse", False) and selected_idx == 0:
                run_analysis = True
            with col_b:
                acc = selected_filing["accession"]
                cik_val = int(selected_filing["cik"])
                edgar_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_val}&type={form_type}&dateb=&owner=include&count=10"
                st.markdown(f'<div style="margin-top:8px"><a href="{edgar_url}" target="_blank" style="color:#5c7cfa;font-size:12px">📎 View on EDGAR ↗</a></div>', unsafe_allow_html=True)

            if run_analysis:
                with st.spinner("Fetching filing text from EDGAR…"):
                    text = fetch_filing_text(
                        selected_filing["cik"],
                        selected_filing["accession"],
                        selected_filing["doc"],
                    )

                if not text or len(text) < 100:
                    st.error("Could not retrieve filing text. The document may be in a format that can't be parsed directly.")
                    st.info("💡 Try a different filing date, or paste the filing text manually below.")
                else:
                    st.success(f"Retrieved {len(text):,} characters of filing text.")

                    with st.spinner("Claude is reading the filing and drafting the analyst note…"):
                        note = analyse_earnings(ticker_input, text, selected_filing["date"])

                    st.markdown("---")
                    st.markdown(f"## 📋 Analyst Note — {ticker_input} · {selected_filing['date']}")

                    owned = any(ticker_input.startswith(p) for p in YOUR_PORTFOLIO)
                    if owned:
                        st.info("📌 **You hold a position in this stock.** Review against your current thesis.")

                    st.markdown(note)

                    # Save note
                    st.markdown("---")
                    st.download_button(
                        label="📥 Download Note (.md)",
                        data=f"# {ticker_input} — Analyst Note\n**Filing Date:** {selected_filing['date']}\n\n{note}",
                        file_name=f"{ticker_input}_earnings_{selected_filing['date']}.md",
                        mime="text/markdown",
                    )

    # Manual paste fallback
    st.markdown("---")
    with st.expander("📋 Manual Text Input (paste filing text directly)"):
        manual_ticker = st.text_input("Ticker for manual analysis", placeholder="e.g. TSLA")
        manual_text   = st.text_area("Paste filing or earnings release text here", height=200)
        manual_date   = st.text_input("Filing date", value=datetime.now().strftime("%Y-%m-%d"))
        if st.button("🤖 Analyse Manual Text") and manual_text and manual_ticker:
            with st.spinner("Analysing…"):
                note = analyse_earnings(manual_ticker.upper(), manual_text, manual_date)
            st.markdown(note)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKET RESEARCHER
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🏦 Market Researcher":
    st.markdown("# 🏦 Market Researcher")
    st.caption("AI-powered sector and theme deep dives — any topic, not just your holdings")

    col1, col2 = st.columns([3, 1])
    with col1:
        # Quick presets
        preset_options = (
            ["Custom…"] +
            list(SECTOR_ETFS.keys()) +
            list(THEME_ETFS.keys()) +
            ["Real World Assets (RWA)", "AI Agents", "Quantum Computing",
             "Small Nuclear Reactors", "Autonomous Vehicles", "Longevity Biotech",
             "Satellite Internet", "Deep Sea Mining", "Carbon Credits"]
        )
        preset = st.selectbox("Quick Select or type below", preset_options)
        if preset != "Custom…":
            research_topic = preset
        else:
            research_topic = st.text_input(
                "Custom sector or theme",
                placeholder="e.g. 'AI Infrastructure 2025', 'Canadian gold miners', 'Psychedelic biotech'"
            )
    with col2:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        run_research = st.button("🔬 Research", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    # Show relevant stocks for context
    relevant_stocks = None
    if research_topic and research_topic in SECTOR_STOCKS:
        relevant_stocks = SECTOR_STOCKS[research_topic]
    elif research_topic in ["AI & Semiconductors", "AI Agents", "Robotics & AI"]:
        relevant_stocks = ["NVDA", "MSFT", "META", "GOOGL", "AMZN", "AMD", "AVGO", "ARM", "SMCI", "PLTR"]
    elif "Nuclear" in research_topic:
        relevant_stocks = ["NNE", "OKLO", "CEG", "CCJ", "UEC", "DNN", "NXE", "SMR"]

    if run_research and research_topic:
        with st.spinner(f"Researching {research_topic}… (AI is reading the market)"):
            brief = research_sector(research_topic, relevant_stocks)

        st.markdown(f"## 🔬 Research Brief: {research_topic}")
        st.markdown(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Powered by Claude*")
        st.markdown("---")
        st.markdown(brief)
        st.markdown("---")

        # Check if any of the ideas are in your portfolio
        st.markdown("### 🔗 Portfolio Overlap")
        mentioned_owned = [t for t in YOUR_PORTFOLIO if t in brief.upper()]
        if mentioned_owned:
            st.success(f"You already hold: **{', '.join(mentioned_owned)}** — mentioned in this brief.")
        else:
            st.info("No overlap with your current holdings detected in this brief.")

        # Download
        st.download_button(
            label="📥 Download Brief (.md)",
            data=f"# Market Research Brief: {research_topic}\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n{brief}",
            file_name=f"research_{research_topic.replace(' ','_').lower()}.md",
            mime="text/markdown",
        )

        # Momentum check on relevant stocks
        if relevant_stocks:
            st.markdown("---")
            st.markdown("### 📡 Momentum Check — Key Stocks in This Space")
            with st.spinner("Fetching momentum data…"):
                momentum_check = fetch_stock_momentum(relevant_stocks[:12])

            if momentum_check:
                sorted_check = sorted(momentum_check.items(), key=lambda x: x[1]["score"], reverse=True)
                for row_start in range(0, len(sorted_check), 4):
                    row_items = sorted_check[row_start:row_start + 4]
                    cols = st.columns(4)
                    for i, (ticker, data) in enumerate(row_items):
                        gc = grade_color(data["grade"])
                        d = data["details"]
                        owned = data.get("you_own", False)
                        with cols[i]:
                            st.markdown(
                                f'<div style="background:#1c1f26;border-radius:10px;padding:12px;'
                                f'border-left:3px solid {gc};margin-bottom:8px">'
                                f'<div style="display:flex;justify-content:space-between">'
                                f'<div><span style="font-size:14px;font-weight:700;color:#ddd">{ticker}</span>'
                                f'{"<span style=\" font-size:9px;color:#1D9E75;margin-left:4px\">✓ own</span>" if owned else ""}</div>'
                                f'<div style="font-size:18px;font-weight:900;color:{gc}">{data["score"]}</div>'
                                f'</div>'
                                f'{momentum_bar(data["score"], gc)}'
                                f'<div style="display:flex;justify-content:space-between;margin-top:6px;font-size:10px">'
                                f'<span style="color:#888">1M <b style="color:{"#00e676" if d.get("ret_1m",0)>=0 else "#ff5252"}">{d.get("ret_1m",0):+.1f}%</b></span>'
                                f'<span style="color:#888">RSI <b style="color:#ddd">{d.get("rsi",50):.0f}</b></span>'
                                f'</div></div>',
                                unsafe_allow_html=True
                            )

    # History of recent researches (session)
    if not run_research:
        st.markdown("### 💡 Suggested Research Topics")
        suggestions = [
            ("🤖 AI Infrastructure", "AI & Semiconductors"),
            ("⚡ Nuclear Energy Revival", "Small Nuclear Reactors"),
            ("🔐 Cybersecurity 2025", "Cybersecurity"),
            ("🧬 Biotech Catalysts", "Biotech"),
            ("🏦 Fintech Disruption", "Fintech"),
            ("🌍 Emerging Markets", "Emerging Markets"),
            ("🪙 Real World Assets", "Real World Assets (RWA)"),
            ("🚀 Space Economy", "Space & Defence"),
        ]
        cols = st.columns(4)
        for i, (label, topic) in enumerate(suggestions):
            with cols[i % 4]:
                if st.button(label, key=f"suggest_{i}", use_container_width=True):
                    st.session_state["auto_topic"] = topic
                    st.rerun()

        if "auto_topic" in st.session_state:
            research_topic = st.session_state.pop("auto_topic")
            with st.spinner(f"Researching {research_topic}…"):
                brief = research_sector(research_topic)
            st.markdown(f"## 🔬 {research_topic}")
            st.markdown(brief)


# ══════════════════════════════════════════════════════════════════════════════
# NEW DATA LAYERS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch_macro_data() -> dict:
    """Fetch macro indicators — rates, dollar, commodities, volatility."""
    tickers = {
        # Rates & Bonds
        "10Y Yield":      "^TNX",
        "2Y Yield":       "^IRX",
        "30Y Yield":      "^TYX",
        "HYG (Junk)":     "HYG",
        "IEI (IG Bond)":  "IEI",
        # Volatility
        "VIX":            "^VIX",
        "VIX3M":          "^VIX3M",
        "VVIX":           "^VVIX",
        # Dollar & FX
        "DXY (USD)":      "DX-Y.NYB",
        "USD/CAD":        "CADUSD=X",
        "EUR/USD":        "EURUSD=X",
        # Commodities
        "Gold":           "GLD",
        "Oil (WTI)":      "USO",
        "Copper":         "CPER",
        "Silver":         "SLV",
        # Risk appetite
        "Bitcoin":        "BTC-USD",
        "S&P 500":        "^GSPC",
        "Russell 2000":   "IWM",
        "Nasdaq":         "^IXIC",
    }
    results = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="3mo", interval="1d")
            if hist.empty:
                continue
            close = hist["Close"].squeeze()
            price = float(close.iloc[-1])
            ret_1d = (price / float(close.iloc[-2]) - 1) * 100 if len(close) >= 2 else 0
            ret_1w = (price / float(close.iloc[-6]) - 1) * 100 if len(close) >= 6 else ret_1d
            ret_1m = (price / float(close.iloc[-22]) - 1) * 100 if len(close) >= 22 else ret_1w
            ret_3m = (price / float(close.iloc[0]) - 1) * 100 if len(close) >= 60 else ret_1m
            results[name] = {
                "ticker": ticker, "price": price,
                "ret_1d": round(ret_1d, 2), "ret_1w": round(ret_1w, 2),
                "ret_1m": round(ret_1m, 2), "ret_3m": round(ret_3m, 2),
                "hist": hist,
            }
        except Exception:
            continue
    return results


@st.cache_data(ttl=600)
def fetch_fear_greed() -> dict:
    """Fetch CNN Fear & Greed index via public API."""
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            score = data.get("fear_and_greed", {}).get("score", 50)
            rating = data.get("fear_and_greed", {}).get("rating", "Neutral")
            prev_close = data.get("fear_and_greed", {}).get("previous_close", score)
            prev_1w = data.get("fear_and_greed", {}).get("previous_1_week", score)
            prev_1m = data.get("fear_and_greed", {}).get("previous_1_month", score)
            return {
                "score": round(float(score), 1),
                "rating": rating,
                "prev_close": round(float(prev_close), 1),
                "prev_1w": round(float(prev_1w), 1),
                "prev_1m": round(float(prev_1m), 1),
                "available": True,
            }
    except Exception:
        pass
    return {"score": 50, "rating": "Neutral", "available": False}


def _scrape_finviz_page(url: str, headers: dict) -> list:
    """Scrape one page of Finviz screener results. Returns list of row dicts."""
    import re
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return []
        # Parse the table rows from Finviz HTML
        from html.parser import HTMLParser

        class FinvizParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.rows = []
                self.current_row = []
                self.in_table = False
                self.in_row = False
                self.in_cell = False
                self.cell_data = ""
                self.row_count = 0

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "tr":
                    cls = attrs_dict.get("class", "")
                    if "screener-row" in cls or "row-" in cls:
                        self.in_row = True
                        self.current_row = []
                if tag == "td" and self.in_row:
                    self.in_cell = True
                    self.cell_data = ""

            def handle_endtag(self, tag):
                if tag == "td" and self.in_cell:
                    self.current_row.append(self.cell_data.strip())
                    self.in_cell = False
                if tag == "tr" and self.in_row:
                    if len(self.current_row) > 5:
                        self.rows.append(self.current_row)
                    self.in_row = False
                    self.current_row = []

            def handle_data(self, data):
                if self.in_cell:
                    self.cell_data += data

        parser = FinvizParser()
        parser.feed(resp.text)
        return parser.rows
    except Exception:
        return []


@st.cache_data(ttl=900)
def fetch_finviz_breadth() -> dict:
    """
    Full market breadth from Finviz screener.
    Covers 8,000+ US stocks (NYSE + NASDAQ + AMEX).
    Uses Finviz export CSV — most reliable method.
    Returns breadth broken down by market cap tier and sector.
    """
    import csv, io

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://finviz.com/screener.ashx",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Finviz export URL — columns: Ticker, Company, Sector, Industry, Country,
    # Market Cap, P/E, Price, Change, Volume, SMA20, SMA50, SMA200, 52W High, 52W Low
    # v=152 = technical view, o=-marketcap = sorted by market cap desc
    base_export = "https://finviz.com/export.ashx?v=152&f=geo_usa&o=-marketcap&c=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68"

    all_rows = []
    try:
        resp = requests.get(base_export, headers=HEADERS, timeout=25)
        if resp.status_code == 200 and len(resp.text) > 500:
            reader = csv.DictReader(io.StringIO(resp.text))
            all_rows = list(reader)
    except Exception:
        pass

    # If CSV export blocked, try scraping the screener pages
    if not all_rows:
        # Fallback: scrape multiple pages of screener
        # Each page = 20 stocks, we scrape up to 50 pages = 1000 stocks
        screener_base = "https://finviz.com/screener.ashx?v=152&f=geo_usa&o=-marketcap"
        for offset in range(0, 1001, 20):
            url = f"{screener_base}&r={offset + 1}"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code != 200:
                    break
                rows = _scrape_finviz_page(url, HEADERS)
                if not rows:
                    break
                all_rows.extend(rows)
                time.sleep(0.15)
            except Exception:
                break

    if not all_rows:
        # Final fallback: use yfinance batch for broader universe
        return _fetch_breadth_yfinance_batch()

    # Parse the data
    return _parse_finviz_breadth(all_rows)


def _parse_finviz_breadth(rows: list) -> dict:
    """Parse Finviz rows into breadth metrics."""
    # Market cap tiers (USD)
    CAP_TIERS = {
        "Mega Cap (>$200B)":    200e9,
        "Large Cap ($10-200B)": 10e9,
        "Mid Cap ($2-10B)":     2e9,
        "Small Cap ($300M-2B)": 300e6,
        "Micro Cap (<$300M)":   0,
    }

    total = 0
    above_50 = above_200 = new_highs = new_lows = advancing = declining = 0

    # By cap tier
    tier_data = {tier: {"total": 0, "above_50": 0, "above_200": 0,
                        "new_highs": 0, "new_lows": 0, "advancing": 0, "declining": 0}
                 for tier in CAP_TIERS}

    # By sector
    sector_data = {}

    for row in rows:
        try:
            # Handle both dict (CSV) and list (scraped) formats
            if isinstance(row, dict):
                ticker   = row.get("Ticker", "")
                sector   = row.get("Sector", "Unknown")
                mktcap_s = row.get("Market Cap", "0")
                price_s  = row.get("Price", "0")
                change_s = row.get("Change", "0")
                sma50_s  = row.get("SMA50", "") or row.get("50D High", "")
                sma200_s = row.get("SMA200", "") or row.get("200D High", "")
                high52_s = row.get("52W High", "") or row.get("52W High From Price", "")
                low52_s  = row.get("52W Low", "")  or row.get("52W Low From Price", "")
            else:
                # List format from scraper — column order varies
                if len(row) < 10:
                    continue
                ticker   = row[0] if len(row) > 0 else ""
                sector   = row[3] if len(row) > 3 else "Unknown"
                mktcap_s = row[5] if len(row) > 5 else "0"
                price_s  = row[7] if len(row) > 7 else "0"
                change_s = row[8] if len(row) > 8 else "0"
                sma50_s  = ""
                sma200_s = ""
                high52_s = ""
                low52_s  = ""

            if not ticker or ticker == "Ticker":
                continue

            # Parse market cap
            mktcap = _parse_finviz_number(mktcap_s)
            price  = _parse_finviz_number(price_s)
            change = _parse_finviz_pct(change_s)

            if price <= 0:
                continue

            # Parse SMA distance (Finviz shows % from SMA)
            sma50_dist  = _parse_finviz_pct(sma50_s)   # % above/below SMA50
            sma200_dist = _parse_finviz_pct(sma200_s)  # % above/below SMA200
            high52_dist = _parse_finviz_pct(high52_s)  # % from 52W high (negative = below)
            low52_dist  = _parse_finviz_pct(low52_s)   # % from 52W low (positive = above)

            # Breadth flags
            is_above_50  = sma50_dist  > 0  if sma50_s  else None
            is_above_200 = sma200_dist > 0  if sma200_s else None
            is_new_high  = high52_dist >= -2 if high52_s else False  # within 2% of 52W high
            is_new_low   = low52_dist  <= 2  if low52_s  else False  # within 2% of 52W low
            is_advancing = change > 0
            is_declining = change < 0

            # Totals
            total += 1
            if is_above_50  is True:  above_50  += 1
            if is_above_200 is True:  above_200 += 1
            if is_new_high:           new_highs += 1
            if is_new_low:            new_lows  += 1
            if is_advancing:          advancing += 1
            if is_declining:          declining += 1

            # Cap tier breakdown
            tier = _get_cap_tier(mktcap, CAP_TIERS)
            if tier in tier_data:
                td = tier_data[tier]
                td["total"] += 1
                if is_above_50  is True: td["above_50"]  += 1
                if is_above_200 is True: td["above_200"] += 1
                if is_new_high:          td["new_highs"] += 1
                if is_new_low:           td["new_lows"]  += 1
                if is_advancing:         td["advancing"] += 1
                if is_declining:         td["declining"] += 1

            # Sector breakdown
            if sector not in sector_data:
                sector_data[sector] = {"total": 0, "above_50": 0, "above_200": 0,
                                       "advancing": 0, "declining": 0}
            sd = sector_data[sector]
            sd["total"] += 1
            if is_above_50  is True: sd["above_50"]  += 1
            if is_above_200 is True: sd["above_200"] += 1
            if is_advancing:         sd["advancing"] += 1
            if is_declining:         sd["declining"] += 1

        except Exception:
            continue

    if total == 0:
        return _fetch_breadth_yfinance_batch()

    # Compute percentages for tier data
    tier_summary = {}
    for tier, td in tier_data.items():
        if td["total"] == 0:
            continue
        tier_summary[tier] = {
            "total":         td["total"],
            "above_50_pct":  round(td["above_50"]  / td["total"] * 100, 1),
            "above_200_pct": round(td["above_200"] / td["total"] * 100, 1),
            "new_highs":     td["new_highs"],
            "new_lows":      td["new_lows"],
            "ad_ratio":      round(td["advancing"] / max(td["declining"], 1), 2),
        }

    # Sector summary
    sector_summary = {}
    for sec, sd in sector_data.items():
        if sd["total"] < 5 or sec in ("", "Unknown"):
            continue
        sector_summary[sec] = {
            "total":         sd["total"],
            "above_50_pct":  round(sd["above_50"]  / sd["total"] * 100, 1),
            "above_200_pct": round(sd["above_200"] / sd["total"] * 100, 1),
            "ad_ratio":      round(sd["advancing"] / max(sd["declining"], 1), 2),
        }

    return {
        "source":        "Finviz",
        "total":         total,
        "above_50_pct":  round(above_50  / total * 100, 1),
        "above_200_pct": round(above_200 / total * 100, 1),
        "new_highs":     new_highs,
        "new_lows":      new_lows,
        "advancing":     advancing,
        "declining":     declining,
        "ad_ratio":      round(advancing / max(declining, 1), 2),
        "hl_ratio":      round(new_highs / max(new_lows, 1), 2),
        "tier_summary":  tier_summary,
        "sector_summary": sector_summary,
    }


def _parse_finviz_number(s: str) -> float:
    """Parse Finviz number strings like '1.23B', '456M', '12.3K'."""
    if not s or s in ("-", "N/A", ""):
        return 0.0
    s = s.strip().replace(",", "").replace("%", "")
    multipliers = {"T": 1e12, "B": 1e9, "M": 1e6, "K": 1e3}
    for suffix, mult in multipliers.items():
        if s.upper().endswith(suffix):
            try:
                return float(s[:-1]) * mult
            except ValueError:
                return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_finviz_pct(s: str) -> float:
    """Parse percentage string like '+12.34%' or '-5.67%'."""
    if not s or s in ("-", "N/A", ""):
        return 0.0
    try:
        return float(str(s).replace("%", "").replace("+", "").strip())
    except ValueError:
        return 0.0


def _get_cap_tier(mktcap: float, tiers: dict) -> str:
    """Classify market cap into tier."""
    if mktcap >= 200e9: return "Mega Cap (>$200B)"
    if mktcap >= 10e9:  return "Large Cap ($10-200B)"
    if mktcap >= 2e9:   return "Mid Cap ($2-10B)"
    if mktcap >= 300e6: return "Small Cap ($300M-2B)"
    return "Micro Cap (<$300M)"


@st.cache_data(ttl=900)
def _fetch_breadth_yfinance_batch() -> dict:
    """
    Fallback breadth engine using yfinance batch download.
    Downloads all tickers in chunks of 100 — covers ~500 stocks efficiently.
    Much faster than one-by-one because yfinance.download() parallelises.
    """
    # Extended universe — S&P500 + Russell 1000 proxies across all sectors
    FULL_UNIVERSE = {
        "Technology": [
            "AAPL","MSFT","NVDA","AVGO","AMD","ORCL","ADBE","CRM","INTC","QCOM",
            "TXN","MU","AMAT","LRCX","KLAC","MRVL","FTNT","CDNS","SNPS","ANSS",
            "KEYS","TRMB","EPAM","OKTA","ZS","CRWD","NET","DDOG","MDB","SNOW",
        ],
        "Healthcare": [
            "LLY","UNH","JNJ","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN",
            "GILD","VRTX","REGN","ISRG","SYK","MDT","ZBH","BAX","HOLX","HSIC",
            "IQV","CRL","CTLT","PDCO","PRGO","JAZZ","INCY","ALKS","EXEL","RARE",
        ],
        "Financials": [
            "BRK-B","JPM","V","MA","BAC","WFC","GS","MS","BLK","SCHW",
            "AXP","C","USB","PNC","TFC","COF","MTB","KEY","RF","HBAN",
            "CFG","FITB","WBS","EWBC","IBOC","FHN","SNV","BOKF","UMBF","FFIN",
        ],
        "Consumer Discretionary": [
            "AMZN","TSLA","HD","MCD","NKE","LOW","SBUX","BKNG","TJX","CMG",
            "ORLY","ROST","GM","F","MAR","HLT","YUM","DRI","POOL","WSM",
            "RH","BBWI","PVH","RL","TPR","HBI","UAA","SKX","CROX","DECK",
        ],
        "Industrials": [
            "GE","CAT","HON","UPS","BA","RTX","LMT","DE","MMM","ETN",
            "EMR","FDX","GD","NOC","ITW","PH","ROK","CMI","IR","XYL",
            "GNRC","CARR","OTIS","TT","JCI","SWK","GWW","MSM","FAST","WSO",
        ],
        "Communication Services": [
            "META","GOOGL","GOOG","NFLX","DIS","TMUS","VZ","T","CHTR","EA",
            "TTWO","WBD","PARA","LYV","MTCH","SNAP","PINS","RDDT","ZM","TWLO",
        ],
        "Energy": [
            "XOM","CVX","COP","EOG","SLB","MPC","PSX","VLO","PXD","OXY",
            "HES","DVN","HAL","BKR","FANG","MRO","APA","CTRA","MTDR","CHX",
        ],
        "Consumer Staples": [
            "PG","KO","PEP","COST","WMT","PM","MO","CL","EL","GIS",
            "KHC","SJM","CHD","CLX","KMB","CAG","CPB","MKC","HRL","SMPL",
        ],
        "Materials": [
            "LIN","APD","ECL","SHW","FCX","NEM","NUE","VMC","MLM","DOW",
            "DD","PPG","IFF","ALB","MOS","CF","ICL","SCCO","MP","USLM",
        ],
        "Real Estate": [
            "PLD","AMT","EQIX","CCI","PSA","DLR","O","WELL","SPG","AVB",
            "EQR","VICI","WY","ARE","BXP","HST","EXR","CUBE","REXR","COLD",
        ],
        "Utilities": [
            "NEE","SO","DUK","AEP","SRE","D","EXC","XEL","WEC","ES",
            "ETR","FE","CMS","NI","AES","AWK","ATO","CNP","OGE","PNW",
        ],
        # Extended — Mid & Small caps for better breadth signal
        "Mid Cap Growth": [
            "CELH","SAIA","UFPI","TREX","AXON","MEDP","HLNE","CSWI","AAON","CVCO",
            "MGNI","RELY","SFM","PTCT","INSP","TMDX","NTRA","RXST","ENSG","ATGE",
        ],
        "Small Cap": [
            "SMTC","ARIS","GRBK","BOOT","KTOS","POWL","DXPE","GKOS","PRCT","HIMS",
            "ACVA","BRZE","SOUN","LUNR","RDW","JOBY","NNE","OKLO","QBTS","RGTI",
        ],
        "Canada TSX": [
            "SHOP.TO","RY.TO","TD.TO","ENB.TO","CNR.TO","CP.TO","BCE.TO","BMO.TO",
            "BNS.TO","MFC.TO","SU.TO","ABX.TO","TRI.TO","WPM.TO","ATD.TO","NTR.TO",
            "CNQ.TO","IMO.TO","AEM.TO","K.TO","FM.TO","CS.TO","ERO.TO","TECK-B.TO",
        ],
    }

    all_tickers = []
    ticker_sector = {}
    for sector, tickers in FULL_UNIVERSE.items():
        for t in tickers:
            if t not in ticker_sector:
                all_tickers.append(t)
                ticker_sector[t] = sector

    # Batch download in chunks of 100
    CHUNK_SIZE = 100
    all_close  = {}

    for i in range(0, len(all_tickers), CHUNK_SIZE):
        chunk = all_tickers[i:i + CHUNK_SIZE]
        try:
            data = yf.download(
                chunk, period="1y", interval="1d",
                group_by="ticker", auto_adjust=True,
                progress=False, threads=True,
            )
            for ticker in chunk:
                try:
                    if len(chunk) == 1:
                        close_s = data["Close"].squeeze()
                    else:
                        close_s = data[ticker]["Close"].squeeze()
                    if not close_s.empty and len(close_s) >= 20:
                        all_close[ticker] = close_s
                except Exception:
                    continue
        except Exception:
            continue

    # Compute breadth
    above_50 = above_200 = new_highs = new_lows = advancing = declining = total = 0

    CAP_TIERS = [
        "Mega Cap (>$200B)", "Large Cap ($10-200B)",
        "Mid Cap ($2-10B)", "Small Cap ($300M-2B)", "Micro Cap (<$300M)"
    ]
    # Rough tier by sector grouping
    SECTOR_TIER_MAP = {
        "Technology": "Large Cap ($10-200B)",
        "Healthcare": "Large Cap ($10-200B)",
        "Financials": "Large Cap ($10-200B)",
        "Consumer Discretionary": "Large Cap ($10-200B)",
        "Industrials": "Large Cap ($10-200B)",
        "Communication Services": "Large Cap ($10-200B)",
        "Energy": "Large Cap ($10-200B)",
        "Consumer Staples": "Large Cap ($10-200B)",
        "Materials": "Large Cap ($10-200B)",
        "Real Estate": "Large Cap ($10-200B)",
        "Utilities": "Large Cap ($10-200B)",
        "Mid Cap Growth": "Mid Cap ($2-10B)",
        "Small Cap": "Small Cap ($300M-2B)",
        "Canada TSX": "Large Cap ($10-200B)",
    }

    tier_data   = {t: {"total": 0, "above_50": 0, "above_200": 0,
                       "new_highs": 0, "new_lows": 0,
                       "advancing": 0, "declining": 0} for t in CAP_TIERS}
    sector_data = {}

    for ticker, close_s in all_close.items():
        try:
            price = float(close_s.iloc[-1])
            prev  = float(close_s.iloc[-2]) if len(close_s) >= 2 else price
            sec   = ticker_sector.get(ticker, "Unknown")

            a50 = a200 = False
            if len(close_s) >= 50:
                sma50 = float(close_s.rolling(50).mean().iloc[-1])
                a50   = price > sma50
            if len(close_s) >= 200:
                sma200 = float(close_s.rolling(200).mean().iloc[-1])
                a200   = price > sma200

            high_52w = float(close_s.max())
            low_52w  = float(close_s.min())
            is_nh = price >= high_52w * 0.98
            is_nl = price <= low_52w  * 1.02
            adv   = price > prev
            dec   = price < prev

            total    += 1
            if a50:  above_50  += 1
            if a200: above_200 += 1
            if is_nh: new_highs += 1
            if is_nl: new_lows  += 1
            if adv:  advancing += 1
            if dec:  declining += 1

            # Tier
            tier = SECTOR_TIER_MAP.get(sec, "Mid Cap ($2-10B)")
            td   = tier_data[tier]
            td["total"] += 1
            if a50:   td["above_50"]  += 1
            if a200:  td["above_200"] += 1
            if is_nh: td["new_highs"] += 1
            if is_nl: td["new_lows"]  += 1
            if adv:   td["advancing"] += 1
            if dec:   td["declining"] += 1

            # Sector
            if sec not in sector_data:
                sector_data[sec] = {"total": 0, "above_50": 0, "above_200": 0,
                                    "advancing": 0, "declining": 0}
            sd = sector_data[sec]
            sd["total"] += 1
            if a50:  sd["above_50"]  += 1
            if a200: sd["above_200"] += 1
            if adv:  sd["advancing"] += 1
            if dec:  sd["declining"] += 1

        except Exception:
            continue

    if total == 0:
        return {}

    tier_summary = {}
    for tier, td in tier_data.items():
        if td["total"] == 0:
            continue
        tier_summary[tier] = {
            "total":         td["total"],
            "above_50_pct":  round(td["above_50"]  / td["total"] * 100, 1),
            "above_200_pct": round(td["above_200"] / td["total"] * 100, 1),
            "new_highs":     td["new_highs"],
            "new_lows":      td["new_lows"],
            "ad_ratio":      round(td["advancing"] / max(td["declining"], 1), 2),
        }

    sector_summary = {}
    for sec, sd in sector_data.items():
        if sd["total"] < 3 or sec in ("", "Unknown"):
            continue
        sector_summary[sec] = {
            "total":         sd["total"],
            "above_50_pct":  round(sd["above_50"]  / sd["total"] * 100, 1),
            "above_200_pct": round(sd["above_200"] / sd["total"] * 100, 1),
            "ad_ratio":      round(sd["advancing"] / max(sd["declining"], 1), 2),
        }

    return {
        "source":         "yfinance batch",
        "total":          total,
        "above_50_pct":   round(above_50  / total * 100, 1),
        "above_200_pct":  round(above_200 / total * 100, 1),
        "new_highs":      new_highs,
        "new_lows":       new_lows,
        "advancing":      advancing,
        "declining":      declining,
        "ad_ratio":       round(advancing / max(declining, 1), 2),
        "hl_ratio":       round(new_highs / max(new_lows, 1), 2),
        "tier_summary":   tier_summary,
        "sector_summary": sector_summary,
    }


# Public alias — always try Finviz first, fall back to yfinance batch
@st.cache_data(ttl=900)
def fetch_breadth_data() -> dict:
    """
    Full market breadth.
    Primary: Finviz (8,000+ US stocks, pre-computed, fast).
    Fallback: yfinance batch download (~400 stocks across all sectors + TSX).
    """
    result = fetch_finviz_breadth()
    if result and result.get("total", 0) > 100:
        return result
    return _fetch_breadth_yfinance_batch()


def _fetch_history_robust(ticker: str) -> pd.Series:
    """
    Fetch daily close and resample to weekly.
    More reliable than requesting weekly interval directly from yfinance.
    """
    for kwargs in [{"period": "2y", "interval": "1d"}, {"period": "1y", "interval": "1d"}]:
        try:
            hist = yf.Ticker(ticker).history(**kwargs)
            if hist is not None and not hist.empty and len(hist) >= 20:
                close  = hist["Close"].squeeze()
                weekly = close.resample("W-FRI").last().dropna()
                if len(weekly) >= 10:
                    return weekly
        except Exception:
            continue
    return pd.Series(dtype=float)


@st.cache_data(ttl=900)
def fetch_sector_rs_data() -> dict:
    """
    Compute Relative Strength of each sector vs S&P 500.
    Fetches daily data and resamples to weekly — avoids yfinance
    weekly interval issues. Returns RS value + momentum for RRG.
    """
    spy_close = _fetch_history_robust("SPY")
    if spy_close.empty:
        spy_close = _fetch_history_robust("^GSPC")
    if spy_close.empty:
        return {}

    results = {}
    for sector, etf in SECTOR_ETFS.items():
        try:
            etf_close = _fetch_history_robust(etf)
            if etf_close.empty:
                continue

            combined = pd.concat([etf_close, spy_close], axis=1).dropna()
            if len(combined) < 10:
                continue
            combined.columns = ["etf", "spy"]

            rs_ratio = combined["etf"] / combined["spy"]
            base     = rs_ratio.iloc[0]
            if base == 0:
                continue
            rs_norm  = (rs_ratio / base) * 100
            n        = len(rs_norm)

            rs_value    = float(rs_norm.iloc[-1])
            rs_4w       = float(rs_norm.iloc[-4])  if n >= 4  else rs_value
            rs_8w       = float(rs_norm.iloc[-8])  if n >= 8  else rs_4w
            rs_12w      = float(rs_norm.iloc[-12]) if n >= 12 else rs_8w
            rs_prior    = float(rs_norm.iloc[-5])  if n >= 5  else float(rs_norm.iloc[0])
            rs_momentum = (rs_value / rs_prior - 1) * 100 if rs_prior != 0 else 0.0

            ret_1w = float((combined["etf"].iloc[-1] / combined["etf"].iloc[-2]  - 1) * 100) if n >= 2  else 0
            ret_1m = float((combined["etf"].iloc[-1] / combined["etf"].iloc[-5]  - 1) * 100) if n >= 5  else 0
            ret_3m = float((combined["etf"].iloc[-1] / combined["etf"].iloc[-13] - 1) * 100) if n >= 13 else 0

            results[sector] = {
                "etf":         etf,
                "rs_value":    round(rs_value, 2),
                "rs_momentum": round(rs_momentum, 2),
                "rs_4w":       round(rs_4w, 2),
                "rs_8w":       round(rs_8w, 2),
                "rs_12w":      round(rs_12w, 2),
                "improving":   rs_value > rs_4w,
                "ret_1w":      round(ret_1w, 2),
                "ret_1m":      round(ret_1m, 2),
                "ret_3m":      round(ret_3m, 2),
                "weeks":       n,
            }
        except Exception:
            continue
    return results


@st.cache_data(ttl=1800)
def fetch_sector_news_and_sentiment(sectors: list) -> dict:
    """
    Fetch recent headlines for sector ETFs via yfinance
    then use Claude to score sentiment.
    """
    results = {}
    for sector in sectors:
        etf = SECTOR_ETFS.get(sector)
        if not etf:
            continue
        try:
            t = yf.Ticker(etf)
            news = t.news or []
            headlines = []
            for n in news[:6]:
                ct = n.get("content", {})
                title = ct.get("title") or n.get("title", "")
                if title:
                    headlines.append(title)

            if not headlines:
                results[sector] = {"score": 50, "grade": "Neutral", "headlines": [], "summary": "No headlines found."}
                continue

            # Ask Claude to score
            prompt = f"""Sector: {sector} (ETF: {etf})

Recent headlines:
{chr(10).join(f'• {h}' for h in headlines)}

Score the overall sentiment for this sector from these headlines.
Respond in JSON only, no other text:
{{"score": <0-100>, "grade": "<Very Bearish|Bearish|Neutral|Bullish|Very Bullish>", "summary": "<one sentence max>"}}"""

            response = call_claude(
                "You are a financial news sentiment analyser. Respond only with valid JSON.",
                prompt,
                max_tokens=120,
            )

            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    results[sector] = {
                        "score":     parsed.get("score", 50),
                        "grade":     parsed.get("grade", "Neutral"),
                        "summary":   parsed.get("summary", ""),
                        "headlines": headlines,
                    }
                else:
                    results[sector] = {"score": 50, "grade": "Neutral", "headlines": headlines, "summary": response[:120]}
            except Exception:
                results[sector] = {"score": 50, "grade": "Neutral", "headlines": headlines, "summary": "Parse error"}

        except Exception:
            results[sector] = {"score": 50, "grade": "Neutral", "headlines": [], "summary": "Error fetching data"}

    return results


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MACRO DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

if page == "🌍 Macro Dashboard":
    st.markdown("# 🌍 Macro Dashboard")
    st.caption(f"Global macro pulse — rates, dollar, commodities, volatility, risk appetite · {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with st.expander("ℹ️ How to read this dashboard — plain English guide"):
        st.markdown("""
**This dashboard gives you the macro backdrop before you make any trade. Think of it as the weather forecast — you wouldn't ignore a storm warning just because your stock looks bullish.**

| Signal | What it measures | Why it matters |
|--------|-----------------|----------------|
| **VIX** | Market's expectation of volatility over next 30 days | High VIX = fear and uncertainty = bad time to buy aggressively |
| **Yield Curve (2Y/10Y)** | Difference between short and long-term rates | Inverted = banks stop lending = recession risk |
| **Fear & Greed** | Composite of 7 market sentiment indicators | Extreme Greed = crowded trade, consider trimming. Extreme Fear = potential opportunity |
| **DXY (Dollar)** | US dollar strength vs basket of currencies | Strong dollar hurts commodities, gold, emerging markets |
| **Gold/Oil ratio** | Gold price divided by oil price | High ratio = defensive positioning. Low ratio = growth/risk-on |
| **Bitcoin** | Speculative risk appetite proxy | BTC rising strongly = risk appetite healthy across markets |
| **Credit Spread** | Junk bonds (HYG) vs investment grade (IEI) | Junk outperforming = credit markets confident = risk-on |
| **VIX Term Structure** | Near-term VIX vs 3-month VIX | Backwardation (near > far) = immediate fear spike, potential buying opportunity after resolution |
        """)

    with st.spinner("Fetching macro data…"):
        macro = fetch_macro_data()
        fg    = fetch_fear_greed()

    if not macro:
        st.error("Could not fetch macro data.")
        st.stop()

    # ── Fear & Greed ──────────────────────────────────────────────────────────
    st.markdown("### 😨 CNN Fear & Greed Index")
    st.caption("Composite of 7 indicators: stock momentum, put/call ratio, market breadth, junk bond demand, safe haven flows, stock price strength, and market volatility.")

    if fg["available"]:
        fg_score = fg["score"]
        if fg_score >= 75:   fg_c, fg_label = "#ff6b35", "Extreme Greed"
        elif fg_score >= 55: fg_c, fg_label = "#ffd740", "Greed"
        elif fg_score >= 45: fg_c, fg_label = "#888",    "Neutral"
        elif fg_score >= 25: fg_c, fg_label = "#5c7cfa", "Fear"
        else:                fg_c, fg_label = "#90caf9", "Extreme Fear"

        fgc1, fgc2, fgc3, fgc4, fgc5 = st.columns(5)
        fgc1.markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:16px;text-align:center;border-top:4px solid {fg_c}">'
            f'<div style="font-size:10px;color:#555;text-transform:uppercase">NOW</div>'
            f'<div style="font-size:36px;font-weight:900;color:{fg_c}">{fg_score:.0f}</div>'
            f'<div style="font-size:12px;color:{fg_c};font-weight:700">{fg_label}</div>'
            f'</div>', unsafe_allow_html=True)
        for col, label, val in [
            (fgc2, "Yesterday", fg["prev_close"]),
            (fgc3, "1 Week Ago", fg["prev_1w"]),
            (fgc4, "1 Month Ago", fg["prev_1m"]),
        ]:
            if val >= 75:   vc, vl = "#ff6b35", "Extreme Greed"
            elif val >= 55: vc, vl = "#ffd740", "Greed"
            elif val >= 45: vc, vl = "#888",    "Neutral"
            elif val >= 25: vc, vl = "#5c7cfa", "Fear"
            else:           vc, vl = "#90caf9", "Extreme Fear"
            col.markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:16px;text-align:center;border-top:2px solid {vc}">'
                f'<div style="font-size:10px;color:#555;text-transform:uppercase">{label}</div>'
                f'<div style="font-size:28px;font-weight:800;color:{vc}">{val:.0f}</div>'
                f'<div style="font-size:11px;color:{vc}">{vl}</div>'
                f'</div>', unsafe_allow_html=True)

        trend = fg_score - fg["prev_1w"]
        trend_c = "#00e676" if trend > 5 else ("#ff5252" if trend < -5 else "#ffd740")
        fgc5.markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:16px;text-align:center;border-top:2px solid {trend_c}">'
            f'<div style="font-size:10px;color:#555;text-transform:uppercase">1W TREND</div>'
            f'<div style="font-size:36px;font-weight:900;color:{trend_c}">{"▲" if trend > 0 else "▼"}</div>'
            f'<div style="font-size:13px;color:{trend_c}">{trend:+.1f} pts</div>'
            f'</div>', unsafe_allow_html=True)

        # Plain language interpretation
        fg_explain = {
            "Extreme Greed": "⚠️ **Extreme Greed** — everyone is bullish, which historically means the easy money has been made. This is not a time to chase — it's a time to trim winners and raise cash. Corrections tend to follow Extreme Greed readings within 2-4 weeks.",
            "Greed":         "🟡 **Greed** — markets are running hot. Still OK to hold positions but be selective about adding new ones. Watch for any catalyst that could flip sentiment.",
            "Neutral":       "➖ **Neutral** — no strong signal either way. Markets are balanced between buyers and sellers. Focus on individual stock setups rather than macro timing.",
            "Fear":          "🟢 **Fear** — investors are nervous. Historically this is a better time to be buying than selling. Fear creates opportunity — good stocks go on sale.",
            "Extreme Fear":  "🟢 **Extreme Fear** — historically one of the best times to buy quality assets. Most people are selling, which means prices are depressed. The hardest trade to make is often the right one.",
        }
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {fg_c};border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-top:10px;font-size:13px;color:#aaa">'
            f'{fg_explain.get(fg_label, "")}</div>', unsafe_allow_html=True)
    else:
        st.info("Fear & Greed data unavailable — CNN API may be rate limiting. Try refreshing in a few minutes.")
        st.markdown(
            '<div style="background:#1c1f26;border-left:4px solid #555;border-radius:0 10px 10px 0;'
            'padding:12px 16px;font-size:13px;color:#aaa">'
            '<b style="color:#ddd">What is the Fear & Greed Index?</b><br>'
            "CNN's composite sentiment indicator combines 7 signals: stock price momentum (S&P vs 125-day average), "
            'stock price strength (52W highs vs lows on NYSE), stock price breadth (advancing vs declining volume), '
            'put and call options ratio, junk bond demand (yield spread), market volatility (VIX), and safe haven demand (stocks vs bonds). '
            'Readings below 25 = Extreme Fear (historically good buying zones). Above 75 = Extreme Greed (historically time to be cautious).'
            '</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Volatility Regime ─────────────────────────────────────────────────────
    st.markdown("### ⚡ Volatility Regime")
    st.caption("VIX = the market's speedometer for fear. It measures how much movement options traders expect in the S&P 500 over the next 30 days.")

    vix_data  = macro.get("VIX", {})
    vvix_data = macro.get("VVIX", {})
    v3m_data  = macro.get("VIX3M", {})

    if vix_data:
        vix_val = vix_data["price"]
        if vix_val < 15:   vix_regime, vix_c = "LOW VOLATILITY — Risk On", "#00e676"
        elif vix_val < 20: vix_regime, vix_c = "NORMAL — Cautiously Bullish", "#69f0ae"
        elif vix_val < 25: vix_regime, vix_c = "ELEVATED — Risk Increasing", "#ffd740"
        elif vix_val < 35: vix_regime, vix_c = "HIGH — Risk Off", "#ff5252"
        else:              vix_regime, vix_c = "EXTREME FEAR — Capitulation Zone", "#ff1744"

        vc1, vc2, vc3, vc4 = st.columns(4)
        vc1.markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:4px solid {vix_c}">'
            f'<div style="font-size:10px;color:#555">VIX</div>'
            f'<div style="font-size:32px;font-weight:900;color:{vix_c}">{vix_val:.1f}</div>'
            f'<div style="font-size:10px;color:{vix_c}">{vix_regime}</div>'
            f'</div>', unsafe_allow_html=True)

        if v3m_data and vix_data:
            term_struct = vix_data["price"] - v3m_data["price"]
            ts_c = "#ff5252" if term_struct > 0 else "#00e676"
            ts_label = "BACKWARDATION ⚠️" if term_struct > 0 else "CONTANGO ✓"
            ts_desc  = "Near-term fear > future fear — acute stress event" if term_struct > 0 else "Near-term calm — normal healthy structure"
            vc2.markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {ts_c}">'
                f'<div style="font-size:10px;color:#555">VIX TERM STRUCTURE</div>'
                f'<div style="font-size:20px;font-weight:800;color:{ts_c}">{ts_label}</div>'
                f'<div style="font-size:11px;color:#aaa">VIX {vix_val:.1f} vs VIX3M {v3m_data["price"]:.1f}</div>'
                f'<div style="font-size:10px;color:#555">{ts_desc}</div>'
                f'</div>', unsafe_allow_html=True)

        if vvix_data:
            vvix_val = vvix_data["price"]
            vvix_c = "#ff5252" if vvix_val > 120 else ("#ffd740" if vvix_val > 100 else "#00e676")
            vc3.markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {vvix_c}">'
                f'<div style="font-size:10px;color:#555">VVIX (Vol of Vol)</div>'
                f'<div style="font-size:32px;font-weight:900;color:{vvix_c}">{vvix_val:.0f}</div>'
                f'<div style="font-size:10px;color:#555">Volatility of VIX itself</div>'
                f'</div>', unsafe_allow_html=True)

        vix_1w_c = "#ff5252" if vix_data["ret_1w"] > 0 else "#00e676"
        vc4.markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {vix_1w_c}">'
            f'<div style="font-size:10px;color:#555">VIX 1W CHANGE</div>'
            f'<div style="font-size:32px;font-weight:900;color:{vix_1w_c}">{vix_data["ret_1w"]:+.1f}%</div>'
            f'<div style="font-size:10px;color:#555">{"Rising fear" if vix_data["ret_1w"] > 0 else "Easing fear"}</div>'
            f'</div>', unsafe_allow_html=True)

        # VIX plain language
        vix_explanations = {
            (0, 15):   ("🟢", "#00e676", f"VIX at {vix_val:.1f} — Markets are calm. Options are cheap. This is the environment where momentum strategies work best and buying dips is rewarded. The risk here is complacency — low VIX often precedes spikes."),
            (15, 20):  ("🟡", "#69f0ae", f"VIX at {vix_val:.1f} — Normal market conditions. Nothing to worry about but nothing to be euphoric about either. Continue your normal strategy."),
            (20, 25):  ("⚠️", "#ffd740", f"VIX at {vix_val:.1f} — Volatility is elevated. Markets are nervous about something. Size down new positions, tighten stop losses, avoid leveraged bets."),
            (25, 35):  ("🚨", "#ff5252", f"VIX at {vix_val:.1f} — High fear. This is where most retail investors panic and sell at the bottom. Historically, buying quality assets when VIX is above 30 has been very profitable — but you need conviction and a multi-week horizon."),
            (35, 999): ("🔴", "#ff1744", f"VIX at {vix_val:.1f} — Extreme fear / capitulation. The market is pricing in a crisis. These are historically the best buying opportunities of a generation — but only for those with cash ready and nerves of steel."),
        }
        for (lo, hi), (icon, color, text) in vix_explanations.items():
            if lo <= vix_val < hi:
                st.markdown(
                    f'<div style="background:#1c1f26;border-left:4px solid {color};border-radius:0 10px 10px 0;'
                    f'padding:12px 16px;margin-top:10px;font-size:13px;color:#aaa">{icon} {text}</div>',
                    unsafe_allow_html=True)
                break

        # VIX Term Structure explanation
        if v3m_data:
            term_struct = vix_data["price"] - v3m_data["price"]
            if term_struct > 2:
                st.markdown(
                    '<div style="background:#1c1f26;border-left:4px solid #ff5252;border-radius:0 10px 10px 0;'
                    'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">'
                    '⚠️ <b style="color:#ff5252">VIX Backwardation</b> — Near-term VIX is higher than 3-month VIX. '
                    'This means traders are more scared about the next 30 days than the next 90 days — a specific, acute fear rather than chronic worry. '
                    'These situations tend to resolve quickly. Once the near-term event passes, VIX often drops sharply, '
                    'which is actually a tailwind for stocks. Watch for the catalyst (earnings, Fed meeting, geopolitical event) and the resolution.'
                    '</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="background:#1c1f26;border-left:4px solid #00e676;border-radius:0 10px 10px 0;'
                    'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">'
                    '✅ <b style="color:#00e676">VIX Contango</b> — The normal healthy state. 3-month VIX is higher than near-term VIX, '
                    'meaning traders expect more volatility in the future than right now. '
                    'This is the natural structure of the options market when there is no immediate crisis. '
                    'Think of it like car insurance being cheaper when roads are dry.'
                    '</div>', unsafe_allow_html=True)

        # VVIX explanation
        if vvix_data:
            vvix_val = vvix_data["price"]
            vvix_explain_c = "#ff5252" if vvix_val > 120 else ("#ffd740" if vvix_val > 100 else "#00e676")
            vvix_text = (
                f"VVIX at {vvix_val:.0f} — **Very elevated**. The market is not just fearful, it's uncertain about *how fearful to be*. "
                "This is the most dangerous macro environment — volatility of volatility spikes precede the biggest market dislocations. Reduce risk."
                if vvix_val > 120 else
                f"VVIX at {vvix_val:.0f} — **Moderately elevated**. Some nervousness about future volatility. "
                "Not a crisis signal but worth watching. If VVIX keeps climbing while VIX is still low, that's an early warning."
                if vvix_val > 100 else
                f"VVIX at {vvix_val:.0f} — **Normal**. The volatility market itself is calm. "
                "When even the fear-of-fear gauge is relaxed, the macro backdrop is genuinely benign."
            )
            st.markdown(
                f'<div style="background:#1c1f26;border-left:4px solid {vvix_explain_c};border-radius:0 10px 10px 0;'
                f'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">'
                f'📊 {vvix_text}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Yield Curve & Credit ──────────────────────────────────────────────────
    st.markdown("### 📈 Yield Curve & Credit")
    st.caption("The yield curve is the single most reliable recession predictor in financial history. Credit spreads tell you how confident the bond market is in corporate health.")

    y10 = macro.get("10Y Yield", {})
    y2  = macro.get("2Y Yield", {})
    y30 = macro.get("30Y Yield", {})
    hyg = macro.get("HYG (Junk)", {})
    iei = macro.get("IEI (IG Bond)", {})

    yc1, yc2, yc3, yc4 = st.columns(4)
    if y10 and y2:
        spread = y10["price"] - y2["price"]
        spread_c = "#00e676" if spread > 0.5 else ("#ffd740" if spread > 0 else "#ff5252")
        spread_label = "Normal ✓" if spread > 0.5 else ("Flat ⚠️" if spread > 0 else "INVERTED 🚨")
        yc1.markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:4px solid {spread_c}">'
            f'<div style="font-size:10px;color:#555">2Y/10Y SPREAD</div>'
            f'<div style="font-size:28px;font-weight:900;color:{spread_c}">{spread:+.2f}%</div>'
            f'<div style="font-size:11px;color:{spread_c}">{spread_label}</div>'
            f'<div style="font-size:10px;color:#555">2Y: {y2["price"]:.2f}% · 10Y: {y10["price"]:.2f}%</div>'
            f'</div>', unsafe_allow_html=True)

    for col, name, data in [(yc2, "10Y Yield", y10), (yc3, "2Y Yield", y2), (yc4, "30Y Yield", y30)]:
        if data:
            c = "#ff5252" if data["ret_1w"] > 0 else "#00e676"
            col.markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {c}">'
                f'<div style="font-size:10px;color:#555">{name}</div>'
                f'<div style="font-size:28px;font-weight:900;color:#ddd">{data["price"]:.2f}%</div>'
                f'<div style="font-size:11px;color:{c}">1W: {data["ret_1w"]:+.2f}%</div>'
                f'</div>', unsafe_allow_html=True)

    # Yield curve plain language
    if y10 and y2:
        spread = y10["price"] - y2["price"]
        if spread < 0:
            yc_text = (
                f"🚨 **Inverted yield curve** ({spread:+.2f}%) — Short-term rates are HIGHER than long-term rates. "
                "This is abnormal and historically has predicted every US recession since 1955, typically with a 12-24 month lag. "
                "What it means: banks borrow short-term and lend long-term — when this spread is negative, their margins are crushed and they stop lending, "
                "which slows the economy. **For your portfolio:** reduce cyclical exposure, favour defensive sectors (utilities, staples, healthcare), hold more cash."
            )
            yc_c = "#ff5252"
        elif spread < 0.3:
            yc_text = (
                f"⚠️ **Flat yield curve** ({spread:+.2f}%) — The spread between short and long rates is very thin. "
                "Not yet inverted but moving in a concerning direction. Banks are seeing compressed margins. "
                "Growth is likely to slow. Watch whether this flattens further or starts to steepen. "
                "**For your portfolio:** don't panic but start trimming the most speculative positions."
            )
            yc_c = "#ffd740"
        else:
            yc_text = (
                f"✅ **Normal yield curve** ({spread:+.2f}%) — Long-term rates are meaningfully higher than short-term. "
                "This is the healthy state. Banks can borrow cheaply short-term and lend at higher long-term rates, "
                "which incentivises lending and economic activity. "
                "**For your portfolio:** macro backdrop is supportive. Focus on stock-picking rather than macro hedging."
            )
            yc_c = "#00e676"
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {yc_c};border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-top:10px;font-size:13px;color:#aaa">{yc_text}</div>',
            unsafe_allow_html=True)

    # Rates direction explanation
    if y10:
        rate_dir = y10["ret_1w"]
        if abs(rate_dir) > 0.2:
            rate_dir_c = "#ff5252" if rate_dir > 0 else "#00e676"
            rate_dir_text = (
                f"📉 **Rates rising** (+{rate_dir:.2f}% this week) — Higher rates are generally bad for growth stocks and real estate "
                "(their future cash flows get discounted more heavily), and bad for bonds. They're good for banks and value stocks. "
                "Your AI/tech positions are most rate-sensitive — a rate spike is often what triggers a tech selloff."
                if rate_dir > 0 else
                f"📈 **Rates falling** ({rate_dir:.2f}% this week) — Lower rates are good for growth stocks, real estate, and bonds. "
                "They reduce the discount rate applied to future earnings, making high-multiple stocks more attractive. "
                "This is a tailwind for your AI/tech and speculative positions."
            )
            st.markdown(
                f'<div style="background:#1c1f26;border-left:4px solid {rate_dir_c};border-radius:0 10px 10px 0;'
                f'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">{rate_dir_text}</div>',
                unsafe_allow_html=True)

    # Credit spread
    if hyg and iei:
        credit_ratio = hyg["ret_1m"] - iei["ret_1m"]
        credit_c = "#00e676" if credit_ratio > 0 else "#ff5252"
        credit_label = "Risk-On — junk outperforming" if credit_ratio > 0 else "Risk-Off — flight to quality"
        st.markdown(
            f'<div style="background:#1c1f26;border-radius:8px;padding:10px 16px;border-left:4px solid {credit_c};font-size:13px;margin-top:8px">'
            f'<b style="color:{credit_c}">Credit Spread Signal:</b> '
            f'<span style="color:#aaa">HYG vs IEI 1M: <b style="color:{credit_c}">{credit_ratio:+.2f}%</b> — {credit_label}</span>'
            f'</div>', unsafe_allow_html=True)

        credit_text = (
            "✅ **Junk bonds outperforming investment grade** — This is a risk-on signal from the credit market. "
            "When investors are willing to hold lower-quality debt (junk) over safer debt (investment grade), "
            "it means confidence in corporate health is high. Credit markets are often smarter than equity markets "
            "— they tend to crack before stocks do. When this flips, pay attention."
            if credit_ratio > 0 else
            "⚠️ **Flight to quality in credit** — Investment grade outperforming junk bonds means credit investors are nervous. "
            "They're accepting lower yields in exchange for safety. This is an early warning signal that often precedes "
            "equity market weakness by 2-4 weeks. Watch whether this trend continues."
        )
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {credit_c};border-radius:0 10px 10px 0;'
            f'padding:10px 14px;margin-top:4px;font-size:12px;color:#aaa">{credit_text}</div>',
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Dollar & FX ───────────────────────────────────────────────────────────
    st.markdown("### 💵 Dollar & FX")
    st.caption("The dollar is the world's reserve currency — its direction affects almost every asset class.")

    fx_names = ["DXY (USD)", "USD/CAD", "EUR/USD"]
    fx_cols  = st.columns(len(fx_names))
    for i, name in enumerate(fx_names):
        data = macro.get(name, {})
        if not data:
            continue
        c1m = "#ff5252" if data["ret_1m"] > 0 else "#00e676"
        if "DXY" in name:
            dxy_regime = "Strong USD — headwind for commodities & EM" if data["ret_1m"] > 2 else (
                "Weak USD — tailwind for gold, EM, commodities" if data["ret_1m"] < -2 else "USD Neutral")
            fx_cols[i].markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {c1m}">'
                f'<div style="font-size:10px;color:#555">{name}</div>'
                f'<div style="font-size:24px;font-weight:900;color:#ddd">{data["price"]:.2f}</div>'
                f'<div style="font-size:11px;color:{c1m}">1M: {data["ret_1m"]:+.2f}%</div>'
                f'<div style="font-size:10px;color:#555">{dxy_regime}</div>'
                f'</div>', unsafe_allow_html=True)
        else:
            fx_cols[i].markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {c1m}">'
                f'<div style="font-size:10px;color:#555">{name}</div>'
                f'<div style="font-size:24px;font-weight:900;color:#ddd">{data["price"]:.4f}</div>'
                f'<div style="font-size:11px;color:{c1m}">1M: {data["ret_1m"]:+.2f}%</div>'
                f'</div>', unsafe_allow_html=True)

    # DXY plain language
    dxy = macro.get("DXY (USD)", {})
    usdcad = macro.get("USD/CAD", {})
    if dxy:
        dxy_1m = dxy["ret_1m"]
        if dxy_1m > 2:
            dxy_text = (
                f"🔴 **Strong dollar (+{dxy_1m:.1f}% 1M)** — A rising dollar is a headwind for several of your holdings. "
                "Commodities (gold, copper, oil) are priced in dollars — when the dollar rises, these fall in relative terms. "
                "Emerging market stocks (VEE.TO, VNM) face double pressure: their local currencies weaken AND foreign investors pull out. "
                "Multinational companies earn less when converting overseas profits back to dollars. "
                "Your gold position (WPM.TO) is most directly impacted."
            )
            dxy_c = "#ff5252"
        elif dxy_1m < -2:
            dxy_text = (
                f"🟢 **Weak dollar ({dxy_1m:.1f}% 1M)** — A falling dollar is a tailwind across multiple asset classes. "
                "Gold typically rises when the dollar falls. Emerging markets get a boost. "
                "Your WPM.TO, COPP.TO, and emerging market ETFs (VEE.TO, VNM) should benefit. "
                "This also supports commodity prices broadly — bullish for your energy and materials positions."
            )
            dxy_c = "#00e676"
        else:
            dxy_text = (
                f"➖ **Dollar neutral ({dxy_1m:+.1f}% 1M)** — No strong dollar headwind or tailwind. "
                "FX is not a major factor in your returns right now — focus on fundamentals and technicals."
            )
            dxy_c = "#888"
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {dxy_c};border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-top:10px;font-size:13px;color:#aaa">{dxy_text}</div>',
            unsafe_allow_html=True)

    # USD/CAD specific for Fabien
    if usdcad:
        cad_val = usdcad["price"]
        cad_1m  = usdcad["ret_1m"]
        # Note: CADUSD=X shows CAD per USD (inverse), so higher = stronger USD vs CAD
        cad_text = (
            f"🍁 **USD/CAD note** — The CAD is at {cad_val:.4f} USD (1M: {cad_1m:+.2f}%). "
            + ("Your TSX holdings (ENB.TO, WPM.TO, etc.) earn in CAD — a stronger CAD vs USD means your CAD assets are worth more in USD terms, but your US holdings are worth slightly less in CAD. "
               "Oil prices also matter for CAD — Canada is a commodity currency, so oil strength typically strengthens CAD."
               if abs(cad_1m) > 1 else
               "CAD is relatively stable vs USD this month — minimal FX impact on your cross-border holdings.")
        )
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid #ff0000;border-radius:0 10px 10px 0;'
            f'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">{cad_text}</div>',
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Commodities ───────────────────────────────────────────────────────────
    st.markdown("### 🥇 Commodities & Risk Appetite")
    st.caption("Commodities reflect real-world supply/demand and act as inflation and growth barometers. Bitcoin is the speculative risk appetite gauge.")

    comm_names = ["Gold", "Oil (WTI)", "Copper", "Silver", "Bitcoin"]
    comm_cols  = st.columns(len(comm_names))
    for i, name in enumerate(comm_names):
        data = macro.get(name, {})
        if not data:
            continue
        c = "#00e676" if data["ret_1m"] > 0 else "#ff5252"
        comm_cols[i].markdown(
            f'<div style="background:#1c1f26;border-radius:12px;padding:14px;text-align:center;border-top:3px solid {c}">'
            f'<div style="font-size:10px;color:#555">{name}</div>'
            f'<div style="font-size:18px;font-weight:700;color:#ddd">${data["price"]:,.2f}</div>'
            f'<div style="font-size:11px;color:{"#00e676" if data["ret_1d"]>=0 else "#ff5252"}">1D: {data["ret_1d"]:+.2f}%</div>'
            f'<div style="font-size:11px;color:{c}">1M: {data["ret_1m"]:+.2f}%</div>'
            f'</div>', unsafe_allow_html=True)

    # Commodities plain language
    gold = macro.get("Gold", {})
    oil  = macro.get("Oil (WTI)", {})
    copper = macro.get("Copper", {})
    btc  = macro.get("Bitcoin", {})

    comm_interpretations = []

    if gold:
        g1m = gold["ret_1m"]
        if g1m > 5:
            comm_interpretations.append(("#ffd740", f"🥇 **Gold surging (+{g1m:.1f}% 1M)** — Strong gold is a defensive signal. Investors are seeking safety. This often accompanies dollar weakness, geopolitical stress, or inflation concerns. Your WPM.TO (gold streaming) is directly benefiting. Watch if this is driven by inflation fears (bullish for WPM long-term) or pure fear (temporary safe-haven bid)."))
        elif g1m < -5:
            comm_interpretations.append(("#ff5252", f"🥇 **Gold declining ({g1m:.1f}% 1M)** — Weak gold suggests risk-on rotation (investors prefer equities over safe havens) or dollar strength. Headwind for your WPM.TO position. Not alarming unless it accelerates."))

    if copper:
        cu1m = copper["ret_1m"]
        if cu1m > 5:
            comm_interpretations.append(("#00e676", f"🔴 **Copper strong (+{cu1m:.1f}% 1M)** — Copper is called 'Dr. Copper' because it has a PhD in economics. Strong copper means global industrial demand is healthy — factories are running, construction is active. Bullish macro signal. Your COPP.TO benefits directly."))
        elif cu1m < -5:
            comm_interpretations.append(("#ff5252", f"🔴 **Copper weak ({cu1m:.1f}% 1M)** — Falling copper often signals slowing global growth, particularly in China (world's largest copper consumer). This is a macro warning worth taking seriously. Headwind for COPP.TO."))

    if btc:
        b1m = btc["ret_1m"]
        if b1m > 20:
            comm_interpretations.append(("#F7931A", f"₿ **Bitcoin surging (+{b1m:.1f}% 1M)** — Strong BTC signals broad risk appetite in speculative assets. When crypto runs, it often pulls your smaller speculative positions (SOUN, LUNR, RDW, quantum plays) along with it. Risk-on environment."))
        elif b1m < -20:
            comm_interpretations.append(("#ff5252", f"₿ **Bitcoin weak ({b1m:.1f}% 1M)** — BTC selling off is often a leading indicator of risk-off sentiment spreading to equities. Your speculative positions are most vulnerable. Consider trimming exposure."))

    if gold and oil and oil["price"] > 0:
        go_ratio = gold["price"] / oil["price"]
        go_c = "#ffd740" if go_ratio > 25 else "#00e676"
        go_label = "Defensive" if go_ratio > 25 else "Growth"
        st.markdown(
            f'<div style="background:#1c1f26;border-radius:8px;padding:10px 16px;border-left:4px solid {go_c};font-size:13px;margin-top:8px">'
            f'<b style="color:{go_c}">Gold/Oil Ratio: {go_ratio:.1f}x</b> — '
            f'<span style="color:#aaa">{go_label} signal. '
            + (f"High ratio means gold is expensive relative to oil — investors prefer safety over growth. Defensive positioning recommended."
               if go_ratio > 25 else
               f"Low ratio means oil is strong relative to gold — industrial demand is driving markets, not fear. Risk-on environment, cyclicals favoured.")
            + '</span></div>', unsafe_allow_html=True)

    for color, text in comm_interpretations:
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {color};border-radius:0 10px 10px 0;'
            f'padding:10px 14px;margin-top:6px;font-size:12px;color:#aaa">{text}</div>',
            unsafe_allow_html=True)

    st.markdown("---")

    # ── Macro Regime Summary ──────────────────────────────────────────────────
    st.markdown("### 🧭 Macro Regime Summary")
    st.caption("Synthesising all signals into actionable context for your portfolio.")

    signals = []
    if vix_data:
        vix_v = vix_data["price"]
        if vix_v < 18:
            signals.append(("✅", "Low VIX", f"{vix_v:.1f} — Market calm, risk-on environment. Momentum strategies work. Options cheap for protection.", "#00e676"))
        elif vix_v > 25:
            signals.append(("🚨", "High VIX", f"{vix_v:.1f} — Elevated fear. Size down, wait for stabilisation before adding positions.", "#ff5252"))
        else:
            signals.append(("⚠️", "Moderate VIX", f"{vix_v:.1f} — Cautious positioning. Normal volatility but watch for spikes.", "#ffd740"))

    if y10 and y2:
        spread = y10["price"] - y2["price"]
        if spread < 0:
            signals.append(("🚨", "Inverted Yield Curve", f"Spread {spread:+.2f}% — Recession signal. Historically reliable. Shift toward defensives and cash.", "#ff5252"))
        elif spread < 0.3:
            signals.append(("⚠️", "Flat Yield Curve", f"Spread {spread:+.2f}% — Growth slowing. Reduce cyclical exposure, avoid deep value traps.", "#ffd740"))
        else:
            signals.append(("✅", "Normal Yield Curve", f"Spread {spread:+.2f}% — Healthy credit environment. Banks lending. Economic expansion supported.", "#00e676"))

    if fg["available"]:
        if fg["score"] > 75:
            signals.append(("⚠️", "Extreme Greed", f"F&G {fg['score']:.0f} — Crowded trade. Trim winners, raise cash. Not a sell signal — a caution signal.", "#ff6b35"))
        elif fg["score"] < 25:
            signals.append(("✅", "Extreme Fear", f"F&G {fg['score']:.0f} — Historically a buying zone. Deploy cash into quality names systematically.", "#00e676"))

    if btc:
        if btc["ret_1m"] > 15:
            signals.append(("✅", "BTC Risk Appetite", f"+{btc['ret_1m']:.1f}% 1M — Speculative appetite strong. Tailwind for your growth and speculative positions.", "#F7931A"))
        elif btc["ret_1m"] < -15:
            signals.append(("🚨", "BTC Weakness", f"{btc['ret_1m']:.1f}% 1M — Risk appetite fading. Review speculative positions.", "#ff5252"))

    if hyg and iei:
        credit_ratio = hyg["ret_1m"] - iei["ret_1m"]
        if credit_ratio < -1:
            signals.append(("⚠️", "Credit Stress", f"Junk bonds lagging by {abs(credit_ratio):.1f}% — bond market seeing stress before equity market. Watch closely.", "#ffd740"))

    for icon, title, desc, color in signals:
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {color};border-radius:0 10px 10px 0;'
            f'padding:10px 14px;margin-bottom:6px">'
            f'<span style="font-size:14px">{icon}</span> '
            f'<b style="color:{color}">{title}</b> '
            f'<span style="color:#888;font-size:12px">— {desc}</span>'
            f'</div>', unsafe_allow_html=True)

    # Overall portfolio posture recommendation
    bullish_signals = sum(1 for _, _, _, c in signals if c in ("#00e676", "#F7931A", "#69f0ae"))
    bearish_signals = sum(1 for _, _, _, c in signals if c in ("#ff5252", "#ff1744"))
    caution_signals = sum(1 for _, _, _, c in signals if c in ("#ffd740", "#ff6b35"))

    if bullish_signals >= 3 and bearish_signals == 0:
        posture_c, posture = "#00e676", "🟢 RISK-ON — Macro backdrop supports aggressive positioning. Run your winners, add to high-conviction ideas."
    elif bearish_signals >= 2:
        posture_c, posture = "#ff5252", "🔴 RISK-OFF — Multiple macro warning signs. Reduce position sizes, raise cash, prioritise capital preservation."
    elif caution_signals >= 2:
        posture_c, posture = "#ffd740", "🟡 CAUTIOUS — Mixed signals. Hold existing positions but be selective about new entries. Size smaller than normal."
    else:
        posture_c, posture = "#888", "⬜ NEUTRAL — No dominant macro signal. Let technicals and fundamentals drive individual stock decisions."

    st.markdown(
        f'<div style="background:#1c1f26;border-radius:12px;padding:16px;margin-top:12px;'
        f'border:2px solid {posture_c};text-align:center">'
        f'<div style="font-size:11px;color:#555;text-transform:uppercase;margin-bottom:6px">Suggested Portfolio Posture</div>'
        f'<div style="font-size:14px;font-weight:700;color:{posture_c}">{posture}</div>'
        f'</div>', unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SECTOR ROTATION RRG
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔄 Sector Rotation (RRG)":
    st.markdown("# 🔄 Sector Rotation — Relative Rotation Graph")
    st.caption("Each sector plotted by Relative Strength vs S&P 500 (x-axis) and RS Momentum (y-axis)")

    with st.expander("ℹ️ How to read this chart"):
        st.markdown("""
**Quadrants — clockwise rotation is the typical cycle:**

| Quadrant | RS Value | RS Momentum | Meaning |
|----------|----------|-------------|---------|
| 🟢 **Leading** (top-right) | Above 100 | Positive | Strong and accelerating — be here |
| 🔵 **Weakening** (bottom-right) | Above 100 | Negative | Was strong, now fading — start reducing |
| 🔴 **Lagging** (bottom-left) | Below 100 | Negative | Weak and worsening — avoid |
| 🟡 **Recovering** (top-left) | Below 100 | Positive | Was weak, now improving — early entry |

**The tail** shows the last 4 weeks of movement — direction of travel matters as much as position.
        """)

    with st.spinner("Computing relative strength for all 11 sectors…"):
        rs_data = fetch_sector_rs_data()

    if not rs_data:
        st.error("Could not compute relative strength data.")
        st.stop()

    # Build RRG dataframe
    rrg_rows = []
    for sector, data in rs_data.items():
        rrg_rows.append({
            "Sector":      sector,
            "ETF":         data["etf"],
            "RS_Value":    data["rs_value"],
            "RS_Momentum": data["rs_momentum"],
            "Improving":   data["improving"],
            "Color":       SECTOR_COLORS.get(sector, "#888"),
        })
    rrg_df = pd.DataFrame(rrg_rows)

    # Determine quadrant
    def get_quadrant(rs_val, rs_mom):
        if rs_val >= 100 and rs_mom >= 0:  return "🟢 Leading"
        if rs_val >= 100 and rs_mom < 0:   return "🔵 Weakening"
        if rs_val < 100  and rs_mom < 0:   return "🔴 Lagging"
        return "🟡 Recovering"

    rrg_df["Quadrant"] = rrg_df.apply(lambda r: get_quadrant(r["RS_Value"], r["RS_Momentum"]), axis=1)

    quad_colors = {
        "🟢 Leading":    "#00e676",
        "🔵 Weakening":  "#5c7cfa",
        "🔴 Lagging":    "#ff5252",
        "🟡 Recovering": "#ffd740",
    }

    # ── RRG Plot ──────────────────────────────────────────────────────────────
    fig = go.Figure()

    # Quadrant background shading — smart scaling to prevent clustering
    x_mid = 100
    y_mid = 0

    # X-axis: centre on 100, symmetric padding based on spread
    x_vals   = rrg_df["RS_Value"].values
    x_spread = max(float(x_vals.max() - x_vals.min()), 4.0)
    x_pad    = max(x_spread * 0.35, 3.0)
    x_centre = float(x_vals.mean())
    # Always keep 100 (neutral line) visible and roughly centred
    x_lo = min(x_centre - x_pad, 100 - x_pad * 0.5)
    x_hi = max(x_centre + x_pad, 100 + x_pad * 0.5)
    x_range = [round(x_lo, 1), round(x_hi, 1)]

    # Y-axis: symmetric around 0
    y_vals   = rrg_df["RS_Momentum"].values
    y_max    = max(abs(float(y_vals.max())), abs(float(y_vals.min())), 1.5)
    y_pad    = y_max * 0.4
    y_range  = [-(y_max + y_pad), (y_max + y_pad)]

    # Shaded quadrant regions
    for x0, x1, y0, y1, color, label in [
        (x_range[0], x_mid, y_mid, y_range[1], "rgba(255,215,64,0.06)",  "RECOVERING"),
        (x_mid, x_range[1], y_mid, y_range[1], "rgba(0,230,118,0.06)",   "LEADING"),
        (x_range[0], x_mid, y_range[0], y_mid, "rgba(255,82,82,0.06)",   "LAGGING"),
        (x_mid, x_range[1], y_range[0], y_mid, "rgba(92,124,250,0.06)",  "WEAKENING"),
    ]:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=color, line=dict(width=0), layer="below")

    # Quadrant labels
    for x, y, label, color in [
        (x_mid + (x_range[1]-x_mid)*0.75, y_range[1]*0.85, "LEADING",    "#00e676"),
        (x_mid + (x_range[1]-x_mid)*0.75, y_range[0]*0.85, "WEAKENING",  "#5c7cfa"),
        (x_range[0] + (x_mid-x_range[0])*0.25, y_range[0]*0.85, "LAGGING", "#ff5252"),
        (x_range[0] + (x_mid-x_range[0])*0.25, y_range[1]*0.85, "RECOVERING", "#ffd740"),
    ]:
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>",
            showarrow=False, font=dict(color=color, size=11), opacity=0.5)

    # Dividing lines
    fig.add_hline(y=0,   line_dash="dash", line_color="#444", line_width=1)
    fig.add_vline(x=100, line_dash="dash", line_color="#444", line_width=1)

    # Tail lines — show 4-week RS trajectory as arrow
    for _, row in rrg_df.iterrows():
        sd     = rs_data.get(row["Sector"], {})
        rs4w   = sd.get("rs_4w",  row["RS_Value"])
        rs8w   = sd.get("rs_8w",  rs4w)
        # Estimate momentum 4 weeks ago using rs_4w as reference point
        mom4w  = (rs4w / sd.get("rs_12w", rs4w) - 1) * 100 if sd.get("rs_12w", 0) > 0 else 0
        # Draw multi-point tail: 8w ago → 4w ago → now
        fig.add_trace(go.Scatter(
            x=[rs8w, rs4w, row["RS_Value"]],
            y=[mom4w * 0.3, mom4w * 0.7, row["RS_Momentum"]],
            mode="lines",
            line=dict(color=row["Color"], width=2, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
            opacity=0.6,
        ))

    # Sector bubbles
    fig.add_trace(go.Scatter(
        x=rrg_df["RS_Value"],
        y=rrg_df["RS_Momentum"],
        mode="markers+text",
        text=rrg_df["ETF"],
        textposition="top center",
        marker=dict(
            size=18,
            color=rrg_df["Color"].tolist(),
            line=dict(width=2, color="#0e1117"),
        ),
        customdata=rrg_df[["Sector", "RS_Value", "RS_Momentum", "Quadrant"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "RS Value: %{customdata[1]:.1f}<br>"
            "RS Momentum: %{customdata[2]:.2f}%<br>"
            "Quadrant: %{customdata[3]}<extra></extra>"
        ),
        name="Sectors",
    ))

    fig.update_layout(
        height=600,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#ccc",
        xaxis=dict(
            title="Relative Strength vs S&P 500 (100 = neutral)",
            gridcolor="#1a1d24", zeroline=False,
            range=x_range,
        ),
        yaxis=dict(
            title="RS Momentum (% change, 4-week)",
            gridcolor="#1a1d24", zeroline=False,
            range=y_range,
        ),
        showlegend=False,
        margin=dict(t=20, b=40, l=60, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Quadrant Summary Cards ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Sector Quadrant Summary")

    q_cols = st.columns(4)
    for i, (quad, qcolor) in enumerate([
        ("🟢 Leading", "#00e676"), ("🔵 Weakening", "#5c7cfa"),
        ("🟡 Recovering", "#ffd740"), ("🔴 Lagging", "#ff5252"),
    ]):
        sectors_in_quad = rrg_df[rrg_df["Quadrant"] == quad]
        with q_cols[i]:
            st.markdown(
                f'<div style="background:#1c1f26;border-radius:12px;padding:14px;'
                f'border-top:4px solid {qcolor};min-height:120px">'
                f'<div style="font-size:13px;font-weight:700;color:{qcolor};margin-bottom:8px">{quad} ({len(sectors_in_quad)})</div>'
                + "".join(
                    f'<div style="font-size:12px;color:#aaa;margin-bottom:3px">'
                    f'<b style="color:#ddd">{row["ETF"]}</b> {row["Sector"][:20]}'
                    f'</div>'
                    for _, row in sectors_in_quad.iterrows()
                ) +
                f'</div>', unsafe_allow_html=True)

    # ── RS Table ──────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Full Relative Strength Table")
    display_df = rrg_df[["Sector", "ETF", "RS_Value", "RS_Momentum", "Quadrant"]].copy()
    display_df["RS_Value"]    = display_df["RS_Value"].map("{:.1f}".format)
    display_df["RS_Momentum"] = display_df["RS_Momentum"].map("{:+.2f}%".format)
    display_df = display_df.sort_values("Quadrant")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.caption("RS Value > 100 = outperforming S&P 500 · RS Momentum positive = improving relative strength · Dotted tails show 4-week trajectory")

    st.markdown("---")
    st.markdown("### 🧭 What the RRG Is Telling You")

    # Build action insights per quadrant
    leading    = rrg_df[rrg_df["Quadrant"] == "🟢 Leading"]
    weakening  = rrg_df[rrg_df["Quadrant"] == "🔵 Weakening"]
    recovering = rrg_df[rrg_df["Quadrant"] == "🟡 Recovering"]
    lagging    = rrg_df[rrg_df["Quadrant"] == "🔴 Lagging"]

    if not leading.empty:
        names = ", ".join(f"{r['ETF']} ({r['Sector'][:12]})" for _, r in leading.iterrows())
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid #00e676;border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-bottom:8px">'
            f'<b style="color:#00e676">🟢 LEADING — {names}</b><br>'
            f'<span style="color:#aaa;font-size:12px">These sectors are beating the S&P 500 AND their relative strength is still improving. '
            f'This is where you want to be overweight. If you have holdings in these sectors, this confirms your positioning. '
            f'Stocks within leading sectors tend to outperform even if the broader market stumbles.</span>'
            f'</div>', unsafe_allow_html=True)

    if not weakening.empty:
        names = ", ".join(f"{r['ETF']} ({r['Sector'][:12]})" for _, r in weakening.iterrows())
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid #5c7cfa;border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-bottom:8px">'
            f'<b style="color:#5c7cfa">🔵 WEAKENING — {names}</b><br>'
            f'<span style="color:#aaa;font-size:12px">These sectors were strong but are losing momentum. Still outperforming the S&P 500 overall, '
            f'but the tide is turning. Review your positions here — not a panic sell, but worth trimming winners and tightening stops. '
            f'They often rotate into Lagging next unless a catalyst reverses the trend.</span>'
            f'</div>', unsafe_allow_html=True)

    if not recovering.empty:
        names = ", ".join(f"{r['ETF']} ({r['Sector'][:12]})" for _, r in recovering.iterrows())
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid #ffd740;border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-bottom:8px">'
            f'<b style="color:#ffd740">🟡 RECOVERING — {names}</b><br>'
            f'<span style="color:#aaa;font-size:12px">These sectors have been underperforming but their relative strength is now improving. '
            f'This is the early entry signal — the contrarian opportunity. They are still below neutral but the direction has changed. '
            f'Best used in combination with a macro tailwind (e.g. energy recovering + oil rising = conviction).</span>'
            f'</div>', unsafe_allow_html=True)

    if not lagging.empty:
        names = ", ".join(f"{r['ETF']} ({r['Sector'][:12]})" for _, r in lagging.iterrows())
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid #ff5252;border-radius:0 10px 10px 0;'
            f'padding:12px 16px;margin-bottom:8px">'
            f'<b style="color:#ff5252">🔴 LAGGING — {names}</b><br>'
            f'<span style="color:#aaa;font-size:12px">These sectors are underperforming and still deteriorating. Avoid adding new positions here. '
            f'If you hold stocks in these sectors, review whether your thesis is still intact or whether the sector headwind is too strong. '
            f'Lagging sectors can stay lagging for months.</span>'
            f'</div>', unsafe_allow_html=True)

    # Rotation cycle note
    st.markdown(
        '<div style="background:#1c1f26;border-radius:8px;padding:12px 16px;margin-top:8px;'
        'border:1px solid #2d3139;font-size:12px;color:#888">'
        '💡 <b style="color:#ddd">Typical rotation cycle:</b> Sectors generally rotate clockwise — '
        'Recovering → Leading → Weakening → Lagging → Recovering. '
        'The fastest money is made catching a sector moving from Recovering into Leading. '
        'The tail direction tells you which way it is heading -- look for tails pointing toward the Leading quadrant.'
        '</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: MARKET BREADTH
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Market Breadth":
    st.markdown("# 📊 Market Breadth")
    st.caption("Full market breadth — 8,000+ US stocks via Finviz + TSX · Separates real rallies from narrow melt-ups")

    with st.expander("ℹ️ Why breadth matters + data sources"):
        st.markdown("""
**Primary source: Finviz** (8,000+ US stocks — NYSE, NASDAQ, AMEX) — pre-computed technical data, updates every few minutes during market hours.

**Fallback: yfinance batch** (~400 stocks across all sectors + TSX top 24) — used if Finviz is unavailable.

**Key signals:**
- **% above SMA50/200** — above 70% = healthy broad market · below 40% = warning
- **Advance/Decline ratio** — above 1.5 = broad buying · below 0.7 = distribution
- **New Highs vs New Lows** — trend health indicator
- **Cap tier divergence** — if Mega caps healthy but Small caps weak = narrowing rally, elevated risk
- **Sector breadth** — which sectors have the most participation

**The warning sign to watch:** Index near highs + Mega caps strong + Small/Mid caps weak = narrow leadership. This precedes most corrections by 2-6 weeks.
        """)

    with st.spinner("Loading full market breadth data… (Finviz: 8,000+ stocks · first load ~15s)"):
        breadth = fetch_breadth_data()

    if not breadth:
        st.error("Could not load breadth data.")
        st.stop()

    total  = breadth["total"]
    source = breadth.get("source", "yfinance")

    # Source badge
    src_c = "#00e676" if "Finviz" in source else "#ffd740"
    st.markdown(
        f'<div style="background:#1c1f26;border-radius:6px;padding:6px 12px;'
        f'border-left:3px solid {src_c};font-size:11px;color:#aaa;margin-bottom:12px;display:inline-block">'
        f'📡 Data source: <b style="color:{src_c}">{source}</b> · '
        f'<b style="color:#ddd">{total:,}</b> stocks analysed'
        f'</div>', unsafe_allow_html=True)

    # ── Key Breadth Metrics ───────────────────────────────────────────────────
    st.markdown("### 📐 Market-Wide Breadth")
    b1, b2, b3, b4, b5, b6 = st.columns(6)

    a50  = breadth["above_50_pct"]
    a200 = breadth["above_200_pct"]
    ad   = breadth["ad_ratio"]
    nh   = breadth["new_highs"]
    nl   = breadth["new_lows"]
    hl   = breadth["hl_ratio"]

    a50_c  = "#00e676" if a50  > 65 else ("#ffd740" if a50  > 45 else "#ff5252")
    a200_c = "#00e676" if a200 > 60 else ("#ffd740" if a200 > 40 else "#ff5252")
    ad_c   = "#00e676" if ad   > 1.5 else ("#ffd740" if ad   > 0.8 else "#ff5252")
    nh_c   = "#00e676" if nh   > 50  else ("#ffd740" if nh   > 20  else "#ff5252")
    nl_c   = "#00e676" if nl   < 20  else ("#ffd740" if nl   < 50  else "#ff5252")
    hl_c   = "#00e676" if hl   > 3   else ("#ffd740" if hl   > 1   else "#ff5252")

    for col, label, val, color, sub in [
        (b1, "% ABOVE SMA50",   f"{a50:.0f}%",  a50_c,  "Healthy" if a50>65 else ("Neutral" if a50>45 else "Weak")),
        (b2, "% ABOVE SMA200",  f"{a200:.0f}%", a200_c, "Bullish" if a200>60 else ("Mixed" if a200>40 else "Bearish")),
        (b3, "ADV/DEC RATIO",   f"{ad:.2f}",    ad_c,   f"{breadth['advancing']:,} adv · {breadth['declining']:,} dec"),
        (b4, "NEW 52W HIGHS",   f"{nh:,}",      nh_c,   f"of {total:,} tracked"),
        (b5, "NEW 52W LOWS",    f"{nl:,}",      nl_c,   f"of {total:,} tracked"),
        (b6, "HIGH/LOW RATIO",  f"{hl:.1f}x",   hl_c,   "Bullish" if hl>3 else ("Mixed" if hl>1 else "Bearish")),
    ]:
        col.markdown(
            f'<div style="background:#1c1f26;border-radius:10px;padding:12px;text-align:center;border-top:3px solid {color}">'
            f'<div style="font-size:9px;color:#555;text-transform:uppercase">{label}</div>'
            f'<div style="font-size:24px;font-weight:900;color:{color}">{val}</div>'
            f'<div style="font-size:9px;color:#555">{sub}</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Breadth Score + A/D Chart ─────────────────────────────────────────────
    breadth_score = round((
        (a50 / 100 * 30) + (a200 / 100 * 25) +
        (min(ad / 2, 1) * 25) + (min(hl / 5, 1) * 20)
    ) * 100, 1)

    if breadth_score >= 70:   bs_label, bs_c = "BROAD BULL MARKET",  "#00e676"
    elif breadth_score >= 55: bs_label, bs_c = "HEALTHY MARKET",     "#69f0ae"
    elif breadth_score >= 45: bs_label, bs_c = "MIXED SIGNALS",      "#ffd740"
    elif breadth_score >= 30: bs_label, bs_c = "NARROW / WEAK",      "#ff5252"
    else:                     bs_label, bs_c = "BREADTH BREAKDOWN",  "#ff1744"

    col_gauge, col_chart = st.columns([1, 2])
    with col_gauge:
        st.markdown(
            f'<div style="background:#1c1f26;border-radius:16px;padding:24px;text-align:center;border:3px solid {bs_c}">'
            f'<div style="font-size:11px;color:#555;text-transform:uppercase">Breadth Health Score</div>'
            f'<div style="font-size:56px;font-weight:900;color:{bs_c}">{breadth_score:.0f}</div>'
            f'<div style="font-size:13px;font-weight:700;color:{bs_c}">{bs_label}</div>'
            f'<div style="background:#2a2d35;border-radius:8px;height:10px;margin-top:14px">'
            f'<div style="width:{breadth_score}%;background:{bs_c};height:100%;border-radius:8px"></div></div>'
            f'<div style="font-size:9px;color:#555;margin-top:6px">{total:,} stocks · {source}</div>'
            f'</div>', unsafe_allow_html=True)

    with col_chart:
        fig_ad = go.Figure()
        flat = max(total - breadth["advancing"] - breadth["declining"], 0)
        fig_ad.add_trace(go.Bar(
            x=["Advancing", "Declining", "Unchanged"],
            y=[breadth["advancing"], breadth["declining"], flat],
            marker_color=["#00e676", "#ff5252", "#888"],
            text=[f'{breadth["advancing"]:,}', f'{breadth["declining"]:,}', f'{flat:,}'],
            textposition="outside",
        ))
        fig_ad.update_layout(
            height=260, title=f"Today's Market — {total:,} Stocks",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc", showlegend=False,
            yaxis=dict(gridcolor="#2d3139"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            margin=dict(t=40, b=10, l=20, r=20),
        )
        st.plotly_chart(fig_ad, use_container_width=True)

    st.markdown("---")

    # ── Market Cap Tier Breakdown ─────────────────────────────────────────────
    tier_summary = breadth.get("tier_summary", {})
    if tier_summary:
        st.markdown("### 🏗️ Breadth by Market Cap Tier")
        st.caption("The most important divergence signal — when Mega caps are fine but Small/Mid caps are breaking down")

        tier_order = [
            "Mega Cap (>$200B)", "Large Cap ($10-200B)",
            "Mid Cap ($2-10B)", "Small Cap ($300M-2B)", "Micro Cap (<$300M)"
        ]
        tier_colors_map = {
            "Mega Cap (>$200B)":    "#378ADD",
            "Large Cap ($10-200B)": "#5DCAA5",
            "Mid Cap ($2-10B)":     "#ffd740",
            "Small Cap ($300M-2B)": "#EF9F27",
            "Micro Cap (<$300M)":   "#ff5252",
        }

        tier_cols = st.columns(len([t for t in tier_order if t in tier_summary]))
        col_idx = 0
        for tier in tier_order:
            td = tier_summary.get(tier)
            if not td:
                continue
            tc   = tier_colors_map.get(tier, "#888")
            a50t = td["above_50_pct"]
            a200t= td["above_200_pct"]
            adt  = td["ad_ratio"]
            a50t_c = "#00e676" if a50t > 65 else ("#ffd740" if a50t > 45 else "#ff5252")

            with tier_cols[col_idx]:
                st.markdown(
                    f'<div style="background:#1c1f26;border-radius:12px;padding:14px;border-top:4px solid {tc}">'
                    f'<div style="font-size:11px;font-weight:700;color:{tc};margin-bottom:8px">{tier}</div>'
                    f'<div style="font-size:10px;color:#555">{td["total"]:,} stocks</div>'
                    f'<div style="margin-top:8px">'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#aaa">'
                    f'<span>Above SMA50</span><b style="color:{a50t_c}">{a50t:.0f}%</b></div>'
                    f'{momentum_bar(int(a50t), a50t_c)}'
                    f'</div>'
                    f'<div style="margin-top:6px">'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;color:#aaa">'
                    f'<span>Above SMA200</span><b style="color:{"#00e676" if a200t>60 else "#ff5252"}">{a200t:.0f}%</b></div>'
                    f'{momentum_bar(int(a200t), "#00e676" if a200t>60 else "#ff5252")}'
                    f'</div>'
                    f'<div style="margin-top:8px;font-size:11px;color:#aaa">'
                    f'A/D: <b style="color:{"#00e676" if adt>1.2 else "#ff5252"}">{adt:.2f}</b> · '
                    f'Highs: <b style="color:#ddd">{td["new_highs"]}</b> / Lows: <b style="color:#ddd">{td["new_lows"]}</b>'
                    f'</div>'
                    f'</div>', unsafe_allow_html=True)
            col_idx += 1

        # Cap tier heatmap chart
        st.markdown("---")
        tier_chart_data = [(t, tier_summary[t]) for t in tier_order if t in tier_summary]
        fig_tier = go.Figure()
        fig_tier.add_trace(go.Bar(
            name="% Above SMA50",
            x=[t[0].split(" (")[0] for t in tier_chart_data],
            y=[t[1]["above_50_pct"] for t in tier_chart_data],
            marker_color=[tier_colors_map.get(t[0], "#888") for t in tier_chart_data],
            opacity=0.9,
        ))
        fig_tier.add_trace(go.Bar(
            name="% Above SMA200",
            x=[t[0].split(" (")[0] for t in tier_chart_data],
            y=[t[1]["above_200_pct"] for t in tier_chart_data],
            marker_color=[tier_colors_map.get(t[0], "#888") for t in tier_chart_data],
            opacity=0.4,
        ))
        fig_tier.add_hline(y=50, line_dash="dash", line_color="#555", opacity=0.5,
            annotation_text="50% line", annotation_font_color="#555")
        fig_tier.update_layout(
            barmode="group", height=320,
            title="SMA50 vs SMA200 Participation by Cap Tier",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc",
            yaxis=dict(gridcolor="#2d3139", title="% of Stocks", range=[0, 105]),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            legend=dict(orientation="h", y=1.1),
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig_tier, use_container_width=True)
        st.caption("⚠️ Watch for Mega/Large cap bars staying high while Small/Micro bars drop — classic narrow rally warning")

    st.markdown("---")

    # ── Sector Breadth Breakdown ──────────────────────────────────────────────
    sector_summary = breadth.get("sector_summary", {})
    if sector_summary:
        st.markdown("### 🏭 Breadth by Sector")
        sorted_sectors = sorted(sector_summary.items(), key=lambda x: x[1]["above_50_pct"], reverse=True)

        sec_df_rows = []
        for sec, sd in sorted_sectors:
            sec_df_rows.append({
                "Sector": sec,
                "Stocks": sd["total"],
                "% Above SMA50":  sd["above_50_pct"],
                "% Above SMA200": sd["above_200_pct"],
                "A/D Ratio":      sd["ad_ratio"],
                "Health": "🟢 Strong" if sd["above_50_pct"] > 65 else (
                           "🟡 Mixed"  if sd["above_50_pct"] > 45 else "🔴 Weak"),
            })
        sec_df = pd.DataFrame(sec_df_rows)

        fig_sec = go.Figure()
        fig_sec.add_trace(go.Bar(
            x=sec_df["Sector"],
            y=sec_df["% Above SMA50"],
            name="% Above SMA50",
            marker_color=["#00e676" if v > 65 else ("#ffd740" if v > 45 else "#ff5252")
                          for v in sec_df["% Above SMA50"]],
            text=sec_df["% Above SMA50"].map("{:.0f}%".format),
            textposition="outside",
        ))
        fig_sec.add_hline(y=50, line_dash="dash", line_color="#555", opacity=0.5)
        fig_sec.update_layout(
            height=360, title="% of Stocks Above SMA50 by Sector",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc", showlegend=False,
            xaxis=dict(gridcolor="rgba(0,0,0,0)", tickangle=-30),
            yaxis=dict(gridcolor="#2d3139", title="% Above SMA50", range=[0, 115]),
            margin=dict(t=40, b=80),
        )
        st.plotly_chart(fig_sec, use_container_width=True)
        st.dataframe(sec_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Breadth Interpretation ────────────────────────────────────────────────
    st.markdown("### 🧭 What the Breadth Is Telling You")

    interpretations = []
    if a50 > 70 and a200 > 60:
        interpretations.append(("✅", "Broad participation", f"{a50:.0f}% above SMA50, {a200:.0f}% above SMA200 across {total:,} stocks — healthy wide rally", "#00e676"))
    elif a50 < 40:
        interpretations.append(("🚨", "Weak breadth", f"Only {a50:.0f}% of {total:,} stocks above SMA50 — indices masking underlying weakness", "#ff5252"))

    if ad > 1.5:
        interpretations.append(("✅", "Strong advance/decline", f"{breadth['advancing']:,} advancing vs {breadth['declining']:,} declining — broad buying pressure", "#00e676"))
    elif ad < 0.8:
        interpretations.append(("🚨", "Distribution signal", f"More stocks declining than advancing — smart money rotating out", "#ff5252"))

    if nh > nl * 3:
        interpretations.append(("✅", "New highs dominating", f"{nh:,} new 52W highs vs {nl:,} lows — trend firmly intact", "#00e676"))
    elif nl > nh * 2:
        interpretations.append(("🚨", "New lows expanding", f"{nl:,} new 52W lows vs {nh:,} highs — trend deteriorating across the market", "#ff5252"))

    # Cap tier divergence check
    if tier_summary:
        mega   = tier_summary.get("Mega Cap (>$200B)",    {}).get("above_50_pct", 50)
        large  = tier_summary.get("Large Cap ($10-200B)", {}).get("above_50_pct", 50)
        small  = tier_summary.get("Small Cap ($300M-2B)", {}).get("above_50_pct", 50)
        micro  = tier_summary.get("Micro Cap (<$300M)",   {}).get("above_50_pct", 50)
        if mega > 65 and small < 45:
            interpretations.append(("⚠️", "Cap tier divergence", f"Mega caps {mega:.0f}% healthy vs Small caps {small:.0f}% — narrow rally, elevated correction risk", "#ff6b35"))
        elif small > mega:
            interpretations.append(("✅", "Small caps leading", f"Small caps {small:.0f}% vs Mega caps {mega:.0f}% — broad risk-on, best breadth signal", "#00e676"))

    if a50 < 45:
        interpretations.append(("⚠️", "Potential index divergence", f"Only {a50:.0f}% of stocks above SMA50 — if indices near highs, that's a major warning", "#ffd740"))

    if not interpretations:
        interpretations.append(("➖", "Mixed signals", "No strong directional breadth signal — market in consolidation", "#888"))

    for icon, title, desc, color in interpretations:
        st.markdown(
            f'<div style="background:#1c1f26;border-left:4px solid {color};border-radius:0 10px 10px 0;'
            f'padding:10px 14px;margin-bottom:6px">'
            f'{icon} <b style="color:{color}">{title}</b> '
            f'<span style="color:#888;font-size:12px">— {desc}</span>'
            f'</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: AI NEWS SENTIMENT
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📰 AI News Sentiment":
    st.markdown("# 📰 AI News Sentiment")
    st.caption("Claude reads the latest headlines for each sector and scores the tone — updated every 30 minutes")

    col1, col2 = st.columns([3, 1])
    with col1:
        sectors_to_scan = st.multiselect(
            "Sectors to analyse",
            list(SECTOR_ETFS.keys()),
            default=list(SECTOR_ETFS.keys()),
        )
    with col2:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        run_news = st.button("🤖 Analyse News", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

    if run_news and sectors_to_scan:
        with st.spinner(f"Claude is reading headlines for {len(sectors_to_scan)} sectors…"):
            news_data = fetch_sector_news_and_sentiment(sectors_to_scan)

        if not news_data:
            st.error("No news data returned.")
            st.stop()

        # ── Sentiment Overview Bar Chart ──────────────────────────────────────
        st.markdown("### 📊 Sector Sentiment Scores")
        sorted_news = sorted(news_data.items(), key=lambda x: x[1]["score"], reverse=True)

        fig_news = go.Figure()
        fig_news.add_trace(go.Bar(
            x=[n[0] for n in sorted_news],
            y=[n[1]["score"] for n in sorted_news],
            marker_color=[grade_color(n[1]["grade"]) for n in sorted_news],
            text=[n[1]["grade"] for n in sorted_news],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Score: %{y}<br><extra></extra>",
        ))
        fig_news.add_hline(y=50, line_dash="dash", line_color="#555", opacity=0.5)
        fig_news.update_layout(
            height=360,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#ccc", showlegend=False,
            xaxis=dict(gridcolor="#2d3139", tickangle=-30),
            yaxis=dict(gridcolor="#2d3139", range=[0, 115], title="Sentiment Score"),
            margin=dict(t=30, b=80),
        )
        st.plotly_chart(fig_news, use_container_width=True)

        st.markdown("---")

        # ── Individual Sector Cards ───────────────────────────────────────────
        st.markdown("### 📋 Sector-by-Sector Breakdown")
        for row_start in range(0, len(sorted_news), 2):
            row_items = sorted_news[row_start:row_start + 2]
            cols = st.columns(2)
            for i, (sector, data) in enumerate(row_items):
                gc    = grade_color(data["grade"])
                score = data["score"]
                color = SECTOR_COLORS.get(sector, "#5c7cfa")

                with cols[i]:
                    headlines_html = "".join(
                        f'<div style="font-size:11px;color:#888;border-left:2px solid #2d3139;'
                        f'padding-left:8px;margin-bottom:4px">{h}</div>'
                        for h in data.get("headlines", [])[:4]
                    )
                    st.markdown(
                        f'<div style="background:#1c1f26;border-radius:12px;padding:16px;'
                        f'border-left:5px solid {color};margin-bottom:12px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div>'
                        f'<div style="font-size:15px;font-weight:700;color:#ddd">{sector}</div>'
                        f'<div style="font-size:10px;color:#555">{SECTOR_ETFS.get(sector,"")}</div>'
                        f'</div>'
                        f'<div style="text-align:right">'
                        f'<div style="font-size:22px;font-weight:900;color:{gc}">{score:.0f}</div>'
                        f'<div style="font-size:10px;color:{gc}">{data["grade"]}</div>'
                        f'</div></div>'
                        f'{momentum_bar(int(score), gc)}'
                        f'<div style="margin-top:10px;font-size:12px;color:#aaa;font-style:italic">'
                        f'"{data.get("summary","")}"</div>'
                        f'<div style="margin-top:8px">{headlines_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # ── Combined Technical + News Signal ─────────────────────────────────
        st.markdown("---")
        st.markdown("### 🎯 Combined Signal: Technical Momentum + News Sentiment")
        st.caption("Confluence of both signals = higher conviction")

        with st.spinner("Fetching technical momentum…"):
            tech_data = fetch_etf_momentum(SECTOR_ETFS)

        combo_rows = []
        for sector in sectors_to_scan:
            tech = tech_data.get(sector, {})
            news = news_data.get(sector, {})
            tech_score = tech.get("score", 50)
            news_score = news.get("score", 50)
            combined   = round(tech_score * 0.6 + news_score * 0.4, 1)

            if combined >= 68:   combo_grade, cc = "🟢 Strong Buy",  "#00e676"
            elif combined >= 55: combo_grade, cc = "🟡 Bullish",     "#ffd740"
            elif combined >= 45: combo_grade, cc = "⬜ Neutral",     "#888"
            elif combined >= 32: combo_grade, cc = "🔴 Bearish",     "#ff5252"
            else:                combo_grade, cc = "🔴 Strong Sell", "#ff1744"

            combo_rows.append({
                "Sector":        sector,
                "ETF":           SECTOR_ETFS.get(sector, ""),
                "Tech Score":    tech_score,
                "News Score":    news_score,
                "Combined":      combined,
                "Signal":        combo_grade,
                "Tech Grade":    tech.get("grade", ""),
                "News Grade":    news.get("grade", ""),
                "Color":         cc,
            })

        combo_df = pd.DataFrame(combo_rows).sort_values("Combined", ascending=False)

        for _, row in combo_df.iterrows():
            cc = row["Color"]
            st.markdown(
                f'<div style="background:#1c1f26;border-radius:10px;padding:12px 16px;'
                f'margin-bottom:6px;border-left:4px solid {cc}">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<span style="font-size:15px;font-weight:700;color:#ddd">{row["Sector"]}</span>'
                f' <span style="font-size:10px;color:#555">{row["ETF"]}</span><br>'
                f'<span style="font-size:11px;color:#888">'
                f'Technical: <b style="color:{grade_color(row["Tech Grade"])}">{row["Tech Score"]}</b>'
                f' · News: <b style="color:{grade_color(row["News Grade"])}">{row["News Score"]:.0f}</b>'
                f'</span>'
                f'</div>'
                f'<div style="text-align:right">'
                f'<span style="font-size:20px;font-weight:900;color:{cc}">{row["Combined"]:.0f}</span>'
                f'<br><span style="font-size:11px;color:{cc}">{row["Signal"]}</span>'
                f'</div></div>'
                f'{momentum_bar(int(row["Combined"]), cc)}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.caption("Combined = 60% technical momentum + 40% news sentiment · Higher weight on technicals as they are more objective")

    else:
        st.info("Select sectors above and click **Analyse News** to run the AI sentiment scan.")
        st.markdown("### 💡 What this module does")
        st.markdown("""
- Fetches the **latest financial headlines** for each sector ETF via Yahoo Finance
- Sends them to **Claude** which reads and scores the overall tone
- Combines with **technical momentum** for a unified signal
- Identifies **sector-level catalysts** you might have missed
- Updates every **30 minutes** (cached)
        """)


# ══════════════════════════════════════════════════════════════════════════════
# OPTION D: ACCURACY UPGRADES — Relative Strength per stock + Volume confirm
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=900)
def fetch_stock_momentum_enhanced(tickers: list, sector_etf: str = "SPY") -> dict:
    """
    Enhanced momentum with:
    - Relative Strength vs sector ETF (not just absolute)
    - Volume confirmation flag
    - Insider buy/sell proxy via short interest change
    """
    results = {}

    # Fetch benchmark
    try:
        bench_hist = yf.Ticker(sector_etf).history(period="6mo", interval="1d")
        bench_close = bench_hist["Close"].squeeze() if not bench_hist.empty else None
    except Exception:
        bench_close = None

    for ticker in tickers:
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="6mo", interval="1d")
            if hist.empty or len(hist) < 20:
                continue

            close = hist["Close"].squeeze()
            vol   = hist["Volume"].squeeze() if "Volume" in hist.columns else None

            # Base momentum score
            mom = compute_momentum_score(hist)
            score = mom["score"]
            details = mom["details"].copy()

            # Relative Strength vs benchmark
            if bench_close is not None:
                try:
                    combined = pd.concat([close, bench_close], axis=1).dropna()
                    combined.columns = ["stock", "bench"]
                    if len(combined) >= 20:
                        rs_ratio = combined["stock"] / combined["bench"]
                        rs_1m = (float(rs_ratio.iloc[-1]) / float(rs_ratio.iloc[-22]) - 1) * 100 if len(rs_ratio) >= 22 else 0
                        rs_3m = (float(rs_ratio.iloc[-1]) / float(rs_ratio.iloc[-63]) - 1) * 100 if len(rs_ratio) >= 63 else 0
                        details["rs_vs_bench_1m"] = round(rs_1m, 1)
                        details["rs_vs_bench_3m"] = round(rs_3m, 1)
                        # Bonus points for relative outperformance
                        if rs_1m > 5:   score = min(score + 10, 100)
                        elif rs_1m > 0: score = min(score + 5, 100)
                        elif rs_1m < -5: score = max(score - 10, 0)
                except Exception:
                    pass

            # Volume confirmation
            if vol is not None and len(vol) >= 20:
                avg_vol   = float(vol.rolling(20).mean().iloc[-1])
                last_vol  = float(vol.iloc[-1])
                vol_ratio = last_vol / avg_vol if avg_vol > 0 else 1.0
                details["vol_ratio"] = round(vol_ratio, 2)
                # Price + high volume = confirmed move
                ret_1d = details.get("ret_1d", 0)
                if ret_1d > 1 and vol_ratio > 1.5:
                    details["vol_confirmed"] = True
                    score = min(score + 8, 100)
                elif ret_1d < -1 and vol_ratio > 1.5:
                    details["vol_confirmed_down"] = True
                    score = max(score - 8, 0)
                else:
                    details["vol_confirmed"] = False

            # Try insider/short interest proxy
            try:
                info = t.info or {}
                short_pct = info.get("shortPercentOfFloat", 0) or 0
                details["short_pct"] = round(float(short_pct) * 100, 1)
                # High short interest can mean squeeze potential OR warning
                if short_pct > 0.20:
                    details["short_squeeze_risk"] = True
            except Exception:
                pass

            results[ticker] = {
                "score":   min(score, 100),
                "grade":   mom["grade"],
                "details": details,
                "name":    ticker,
                "you_own": any(ticker.startswith(p) for p in YOUR_PORTFOLIO),
            }
        except Exception:
            continue
    return results


# ══════════════════════════════════════════════════════════════════════════════
# OPTION C: STOCK SCREENER DATA
# ══════════════════════════════════════════════════════════════════════════════

SCREENER_UNIVERSE = list(set(
    SECTOR_STOCKS["Technology"] + SECTOR_STOCKS["Healthcare"] +
    SECTOR_STOCKS["Financials"] + SECTOR_STOCKS["Consumer Discretionary"] +
    SECTOR_STOCKS["Industrials"] + SECTOR_STOCKS["Communication Services"] +
    SECTOR_STOCKS["Energy"] + SECTOR_STOCKS["Consumer Staples"] +
    SECTOR_STOCKS["Materials"] + SECTOR_STOCKS["Utilities"] +
    SECTOR_STOCKS["Real Estate"] +
    # Add your portfolio tickers
    ["NVDA","MSFT","AMZN","META","TSLA","AAPL","CRWV","APLD","SOUN","LUNR",
     "BBAI","NNE","OKLO","QBTS","RGTI","WPM","ENB","BEP-UN","RDDT","NU"]
))


@st.cache_data(ttl=1800)
def run_stock_screener(
    min_momentum: int = 60,
    sectors: list = None,
    volume_confirmed: bool = False,
    rs_positive: bool = False,
) -> pd.DataFrame:
    """Screen stocks by momentum, RS, volume confirmation."""
    raw = fetch_stock_momentum(SCREENER_UNIVERSE)
    rows = []
    for ticker, data in raw.items():
        d = data.get("details", {})
        sec = data.get("sector", "")

        if sectors and sec and sec not in sectors:
            continue
        if data["score"] < min_momentum:
            continue
        if volume_confirmed and not d.get("vol_confirmed", False):
            continue
        if rs_positive and d.get("rs_vs_bench_1m", 0) <= 0:
            continue

        rows.append({
            "Ticker":    ticker,
            "Score":     data["score"],
            "Grade":     data["grade"],
            "1D%":       d.get("ret_1d", 0),
            "1W%":       d.get("ret_1w", 0),
            "1M%":       d.get("ret_1m", 0),
            "RSI":       d.get("rsi", 50),
            "vs SMA50":  d.get("vs_sma50", 0),
            "Vol Ratio": d.get("vol_ratio", 1.0),
            "RS 1M":     d.get("rs_vs_bench_1m", 0),
            "Own":       "✓" if data.get("you_own") else "",
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Score", ascending=False)


# ══════════════════════════════════════════════════════════════════════════════
# OPTION C: ECONOMIC CALENDAR DATA
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_economic_calendar() -> list:
    """
    Fetch upcoming economic events via investing.com public calendar
    or fall back to a hardcoded list of known recurring events.
    """
    # Try fetching from a public economic calendar API
    events = []
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data = resp.json()
            for e in data:
                impact = e.get("impact", "").lower()
                if impact in ("high", "medium"):
                    events.append({
                        "date":     e.get("date", ""),
                        "time":     e.get("time", ""),
                        "country":  e.get("country", ""),
                        "event":    e.get("title", ""),
                        "impact":   impact,
                        "forecast": e.get("forecast", ""),
                        "previous": e.get("previous", ""),
                    })
    except Exception:
        pass

    # Fallback: key recurring events with approximate dates
    if not events:
        now = datetime.now()
        # FOMC meetings — roughly every 6 weeks
        fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
        for month in fomc_months:
            if month >= now.month:
                events.append({
                    "date": f"2026-{month:02d}-15",
                    "time": "14:00 ET",
                    "country": "US",
                    "event": "FOMC Interest Rate Decision",
                    "impact": "high",
                    "forecast": "—",
                    "previous": "4.25-4.50%",
                })

        events.append({
            "date": f"2026-{now.month:02d}-{min(now.day+7,28):02d}",
            "time": "08:30 ET",
            "country": "US",
            "event": "CPI Inflation Report",
            "impact": "high",
            "forecast": "—",
            "previous": "—",
        })

    return sorted(events, key=lambda x: x.get("date", ""))[:30]


@st.cache_data(ttl=3600)
def fetch_earnings_calendar(tickers: list) -> list:
    """Fetch upcoming earnings dates for a list of tickers via yfinance."""
    results = []
    for ticker in tickers[:30]:  # cap for speed
        try:
            t    = yf.Ticker(ticker)
            info = t.info or {}
            ed   = info.get("earningsTimestamp") or info.get("earningsDate")
            if ed:
                if isinstance(ed, (int, float)):
                    dt = datetime.fromtimestamp(ed)
                elif hasattr(ed, "__iter__") and not isinstance(ed, str):
                    dt = datetime.fromtimestamp(list(ed)[0])
                else:
                    continue
                if dt >= datetime.now():
                    results.append({
                        "ticker": ticker,
                        "date":   dt.strftime("%Y-%m-%d"),
                        "time":   dt.strftime("%H:%M") if dt.hour > 0 else "TBD",
                        "you_own": any(ticker.startswith(p) for p in YOUR_PORTFOLIO),
                    })
        except Exception:
            continue
    return sorted(results, key=lambda x: x["date"])


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: STOCK SCREENER
# ══════════════════════════════════════════════════════════════════════════════

if page == "📈 Stock Screener":
    st.markdown("# 📈 Stock Screener")
    st.caption(f"Scan {len(SCREENER_UNIVERSE)} stocks across all sectors · Momentum + RS + Volume confirmation")

    with st.expander("ℹ️ How the screener works"):
        st.markdown("""
**Momentum Score (0-100):** Combines price vs SMA50, RSI, 1M/3M return, MACD direction, 1W return. Above 65 = strong setup.

**Relative Strength vs S&P 500:** Does the stock outperform the market? Positive RS + high momentum = highest conviction.

**Volume Confirmation:** A price breakout on above-average volume (>1.5x) is far more reliable than a low-volume move.

**Short Interest:** High short % (>20%) can mean either a squeeze setup or a reason smart money is bearish. Context matters.

**Best signals = Momentum score >65 + RS positive + Volume confirmed.** These three together significantly outperform any single indicator.
        """)

    # Filters
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        min_score = st.slider("Min Momentum Score", 0, 90, 60, 5)
    with fc2:
        vol_confirm = st.checkbox("Volume Confirmed Only", value=False)
    with fc3:
        rs_positive = st.checkbox("RS Positive vs S&P Only", value=False)
    with fc4:
        owned_only = st.checkbox("Show My Portfolio Only", value=False)

    sector_filter = st.multiselect(
        "Filter by Sector (leave empty = all)",
        list(SECTOR_STOCKS.keys()),
        default=[],
    )

    run_screen = st.button("🔍 Run Screener", type="primary")

    if run_screen:
        universe = list(YOUR_PORTFOLIO) if owned_only else SCREENER_UNIVERSE
        with st.spinner(f"Scanning {len(universe)} stocks…"):
            screen_df = run_stock_screener(
                min_momentum=min_score,
                sectors=sector_filter if sector_filter else None,
                volume_confirmed=vol_confirm,
                rs_positive=rs_positive,
            )
            if owned_only:
                screen_df = screen_df[screen_df["Own"] == "✓"]

        if screen_df.empty:
            st.warning("No stocks match your criteria. Try lowering the momentum score threshold.")
        else:
            st.success(f"Found **{len(screen_df)}** stocks matching your criteria")

            # Summary metrics
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Stocks Found", len(screen_df))
            sm2.metric("Avg Score", f"{screen_df['Score'].mean():.0f}")
            sm3.metric("Avg 1M Return", f"{screen_df['1M%'].mean():+.1f}%")
            sm4.metric("In Your Portfolio", f"{(screen_df['Own'] == '✓').sum()}")

            st.markdown("---")

            # Results cards — top 12
            st.markdown("### 🏆 Top Results")
            top = screen_df.head(12)
            for row_start in range(0, len(top), 4):
                row_items = top.iloc[row_start:row_start+4]
                cols = st.columns(4)
                for i, (_, row) in enumerate(row_items.iterrows()):
                    gc = grade_color(row["Grade"])
                    ret_c = "#00e676" if row["1M%"] >= 0 else "#ff5252"
                    rs_c  = "#00e676" if row.get("RS 1M", 0) >= 0 else "#ff5252"
                    vol_badge = (
                        '<span style="background:#00e67622;color:#00e676;border:1px solid #00e67644;'
                        'border-radius:3px;padding:1px 4px;font-size:8px">VOL ✓</span>'
                        if row.get("Vol Ratio", 1) > 1.5 else ""
                    )
                    own_badge = (
                        '<span style="background:#1D9E7522;color:#1D9E75;border:1px solid #1D9E7544;'
                        'border-radius:3px;padding:1px 4px;font-size:8px">OWN</span>'
                        if row["Own"] == "✓" else ""
                    )
                    with cols[i]:
                        st.markdown(
                            f'<div style="background:#1c1f26;border-radius:10px;padding:12px;'
                            f'border-left:3px solid {gc};margin-bottom:8px">'
                            f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                            f'<div>'
                            f'<span style="font-size:15px;font-weight:700;color:#ddd">{row["Ticker"]}</span> '
                            f'{vol_badge} {own_badge}'
                            f'</div>'
                            f'<span style="font-size:20px;font-weight:900;color:{gc}">{row["Score"]:.0f}</span>'
                            f'</div>'
                            f'{momentum_bar(int(row["Score"]), gc)}'
                            f'<div style="display:flex;justify-content:space-between;margin-top:6px;font-size:10px">'
                            f'<span style="color:#888">1M <b style="color:{ret_c}">{row["1M%"]:+.1f}%</b></span>'
                            f'<span style="color:#888">RSI <b style="color:#ddd">{row["RSI"]:.0f}</b></span>'
                            f'<span style="color:#888">RS <b style="color:{rs_c}">{row.get("RS 1M", 0):+.1f}%</b></span>'
                            f'</div></div>',
                            unsafe_allow_html=True
                        )

            st.markdown("---")
            st.markdown("### 📋 Full Results Table")
            display = screen_df.copy()
            for col in ["1D%", "1W%", "1M%"]:
                display[col] = display[col].map("{:+.2f}%".format)
            display["Score"]     = display["Score"].map("{:.0f}".format)
            display["RSI"]       = display["RSI"].map("{:.0f}".format)
            display["vs SMA50"]  = display["vs SMA50"].map("{:+.1f}%".format)
            display["Vol Ratio"] = display["Vol Ratio"].map("{:.2f}x".format)
            display["RS 1M"]     = display["RS 1M"].map("{:+.1f}%".format)
            st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("Set your filters above and click **Run Screener**.")
        st.markdown("""
**Quick presets:**
- 🔥 **Strongest momentum:** Score >75, no other filters
- 📈 **Breakout setups:** Score >60 + Volume Confirmed
- 💎 **High conviction:** Score >65 + RS Positive + Volume Confirmed
- 🏦 **Your portfolio health:** My Portfolio Only, Score >0
        """)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: PORTFOLIO RISK MONITOR
# ══════════════════════════════════════════════════════════════════════════════

elif page == "⚠️ Portfolio Risk Monitor":
    st.markdown("# ⚠️ Portfolio Risk Monitor")
    st.caption("Cross-references your TFSA positions against current macro regime and technical signals")

    with st.expander("ℹ️ How this works"):
        st.markdown("""
This module reads your TFSA portfolio and runs it through three filters:

1. **Macro alignment** — Is the current macro environment (VIX, yield curve, dollar) a headwind or tailwind for this position?
2. **Technical signal** — What is the momentum score and signal for each position right now?
3. **Concentration risk** — Are you over-exposed to sectors or themes with macro headwinds?

The goal is not to tell you to sell everything — it's to flag the positions most at risk given current conditions, so you can make informed decisions about sizing and stops.
        """)

    with st.spinner("Loading macro + portfolio data…"):
        macro_data = fetch_macro_data()
        vix_val  = macro_data.get("VIX", {}).get("price", 18)
        y10_val  = macro_data.get("10Y Yield", {}).get("price", 4.0)
        y2_val   = macro_data.get("2Y Yield", {}).get("price", 4.5)
        dxy_1m   = macro_data.get("DXY (USD)", {}).get("ret_1m", 0)
        spread   = y10_val - y2_val

    # Determine macro regime
    if vix_val > 25:        macro_regime, regime_c = "RISK-OFF",    "#ff5252"
    elif vix_val > 20:      macro_regime, regime_c = "CAUTIOUS",    "#ffd740"
    elif spread < 0:        macro_regime, regime_c = "RECESSIONARY","#ff1744"
    else:                   macro_regime, regime_c = "RISK-ON",     "#00e676"

    st.markdown(
        f'<div style="background:#1c1f26;border-radius:12px;padding:16px;margin-bottom:16px;'
        f'border:2px solid {regime_c};text-align:center">'
        f'<div style="font-size:11px;color:#555">CURRENT MACRO REGIME</div>'
        f'<div style="font-size:28px;font-weight:900;color:{regime_c}">{macro_regime}</div>'
        f'<div style="font-size:12px;color:#888">VIX {vix_val:.1f} · Yield spread {spread:+.2f}% · DXY 1M {dxy_1m:+.1f}%</div>'
        f'</div>', unsafe_allow_html=True)

    # Macro headwinds by theme
    THEME_MACRO_SENSITIVITY = {
        "AI Infrastructure":              {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "LOW"},
        "AI Applications":                {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "LOW"},
        "Semiconductors":                 {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "MEDIUM"},
        "Nuclear & Uranium":              {"risk_off": "MEDIUM", "rising_rates": "MEDIUM", "strong_usd": "LOW"},
        "Space, Aerospace & Defence":     {"risk_off": "MEDIUM", "rising_rates": "MEDIUM", "strong_usd": "LOW"},
        "Quantum Computing":              {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "LOW"},
        "Biotech & Health Tech":          {"risk_off": "HIGH",   "rising_rates": "MEDIUM", "strong_usd": "LOW"},
        "Fintech, Platforms & Compounders":{"risk_off":"MEDIUM", "rising_rates": "MEDIUM", "strong_usd": "LOW"},
        "Precious Metals & Mining":       {"risk_off": "LOW",    "rising_rates": "LOW",    "strong_usd": "HIGH"},
        "Energy & Utilities":             {"risk_off": "LOW",    "rising_rates": "LOW",    "strong_usd": "MEDIUM"},
        "Core ETFs":                      {"risk_off": "MEDIUM", "rising_rates": "MEDIUM", "strong_usd": "MEDIUM"},
        "Speculative / Micro-Cap":        {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "LOW"},
        "Tech / Software":                {"risk_off": "HIGH",   "rising_rates": "HIGH",   "strong_usd": "LOW"},
    }

    # Active headwinds
    active_headwinds = []
    if vix_val > 20:        active_headwinds.append("risk_off")
    if y10_val > 4.5:       active_headwinds.append("rising_rates")
    if dxy_1m > 2:          active_headwinds.append("strong_usd")

    # Fetch portfolio signals
    YOUR_TFSA = {
    "MSFT.TO":"AI Infrastructure","AMZN.TO":"AI Infrastructure","META.TO":"AI Infrastructure",
    "APLD":"AI Infrastructure","CRWV":"AI Infrastructure","BBAI":"AI Applications",
    "SOUN":"AI Applications","TEM":"AI Applications","VFV.TO":"Core ETFs","ZCN.TO":"Core ETFs",
    "XEF.TO":"Core ETFs","VEE.TO":"Core ETFs","XID.TO":"Core ETFs","XSU.TO":"Core ETFs",
    "ZJPN.TO":"Core ETFs","VNM":"Core ETFs","NNE":"Nuclear & Uranium","OKLO":"Nuclear & Uranium",
    "CEGS.TO":"Nuclear & Uranium","LUNR":"Space, Aerospace & Defence","RDW":"Space, Aerospace & Defence",
    "MDA.TO":"Space, Aerospace & Defence","LMT.TO":"Space, Aerospace & Defence",
    "JOBY":"Space, Aerospace & Defence","PNG.V":"Space, Aerospace & Defence",
    "QBTS":"Quantum Computing","RGTI":"Quantum Computing","WPM.TO":"Precious Metals & Mining",
    "COPP.TO":"Precious Metals & Mining","ABCL":"Biotech & Health Tech","RXRX":"Biotech & Health Tech",
    "CMPS":"Biotech & Health Tech","RARE":"Biotech & Health Tech","IMVT":"Biotech & Health Tech",
    "DRUG.CN":"Biotech & Health Tech","HELP":"Biotech & Health Tech","WELL.TO":"Biotech & Health Tech",
    "ISRG.NE":"Biotech & Health Tech","NU":"Fintech, Platforms & Compounders",
    "RDDT":"Fintech, Platforms & Compounders","BAM.TO":"Fintech, Platforms & Compounders",
    "BRK.TO":"Fintech, Platforms & Compounders","TOI.V":"Fintech, Platforms & Compounders",
    "CRCL":"Fintech, Platforms & Compounders","ENB.TO":"Energy & Utilities","CU.TO":"Energy & Utilities",
    "BEP-UN.TO":"Energy & Utilities","EOSE":"Energy & Utilities","NXT":"Energy & Utilities",
    "ONE.V":"Speculative / Micro-Cap","PHOS.CN":"Speculative / Micro-Cap","SCD.V":"Speculative / Micro-Cap",
    "TMC":"Speculative / Micro-Cap","CLBT":"Speculative / Micro-Cap","AAPL.TO":"Tech / Software",
    "TSLA.TO":"Tech / Software","APPS.TO":"Tech / Software","NVDA.TO":"Semiconductors",
    "ASML.TO":"Semiconductors","NVTS":"Semiconductors","AEHR":"Semiconductors",
    }

    with st.spinner("Fetching signals for your portfolio positions…"):
        port_signals = fetch_stock_momentum(list(YOUR_TFSA.keys())[:20])

    # Build risk table
    risk_rows = []
    for ticker, theme in YOUR_TFSA.items():
        sig_data = port_signals.get(ticker, {})
        score    = sig_data.get("score", 50)
        grade    = sig_data.get("grade", "➖ Neutral")
        details  = sig_data.get("details", {})

        # Calculate macro risk level for this position
        sensitivity = THEME_MACRO_SENSITIVITY.get(theme, {})
        risk_level  = 0
        risk_reasons = []
        for hw in active_headwinds:
            hw_level = sensitivity.get(hw, "LOW")
            if hw_level == "HIGH":
                risk_level += 2
                risk_reasons.append(f"{hw.replace('_',' ').title()} headwind")
            elif hw_level == "MEDIUM":
                risk_level += 1

        # Technical risk
        if score < 40:
            risk_level += 2
            risk_reasons.append("Weak technicals")
        elif score < 55:
            risk_level += 1

        if risk_level >= 4:   risk_label, risk_color = "🔴 HIGH RISK",    "#ff1744"
        elif risk_level >= 2: risk_label, risk_color = "🟡 MODERATE",     "#ffd740"
        else:                 risk_label, risk_color = "🟢 LOW RISK",     "#00e676"

        risk_rows.append({
            "Ticker":    ticker,
            "Theme":     theme[:22],
            "Mom Score": score,
            "Signal":    grade,
            "Risk Level": risk_label,
            "Risk Color": risk_color,
            "Reasons":   " · ".join(risk_reasons) if risk_reasons else "No active headwinds",
            "1M%":       details.get("ret_1m", 0),
        })

    risk_rows.sort(key=lambda x: (
        0 if "HIGH" in x["Risk Level"] else (1 if "MODERATE" in x["Risk Level"] else 2),
        -x["Mom Score"]
    ))

    st.markdown("---")
    st.markdown("### 🚨 Position Risk Assessment")
    st.caption(f"Active macro headwinds: {', '.join(active_headwinds) if active_headwinds else 'None'}")

    for row in risk_rows:
        rc  = row["Risk Color"]
        gc  = grade_color(row["Signal"])
        ret_c = "#00e676" if row["1M%"] >= 0 else "#ff5252"
        st.markdown(
            f'<div style="background:#1c1f26;border-radius:10px;padding:12px 16px;'
            f'margin-bottom:6px;border-left:4px solid {rc}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
            f'<div>'
            f'<span style="font-size:16px;font-weight:700;color:#ddd">{row["Ticker"]}</span>'
            f' <span style="font-size:10px;color:#555">{row["Theme"]}</span><br>'
            f'<span style="font-size:11px;color:#888">{row["Reasons"]}</span>'
            f'</div>'
            f'<div style="text-align:right;display:flex;gap:12px;align-items:center">'
            f'<div><span style="font-size:10px;color:#555">1M</span><br>'
            f'<span style="font-size:13px;font-weight:700;color:{ret_c}">{row["1M%"]:+.1f}%</span></div>'
            f'<div><span style="font-size:10px;color:#555">Score</span><br>'
            f'<span style="font-size:13px;font-weight:700;color:{gc}">{row["Mom Score"]}</span></div>'
            f'<div><span style="font-size:11px;font-weight:700;color:{rc}">{row["Risk Level"]}</span></div>'
            f'</div></div></div>',
            unsafe_allow_html=True)

    # Summary
    high_risk  = [r for r in risk_rows if "HIGH" in r["Risk Level"]]
    mod_risk   = [r for r in risk_rows if "MODERATE" in r["Risk Level"]]
    low_risk   = [r for r in risk_rows if "LOW" in r["Risk Level"]]

    st.markdown("---")
    sr1, sr2, sr3 = st.columns(3)
    sr1.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid #ff1744"><div style="font-size:10px;color:#555">HIGH RISK POSITIONS</div><div style="font-size:28px;font-weight:900;color:#ff1744">{len(high_risk)}</div><div style="font-size:10px;color:#888">{", ".join(r["Ticker"] for r in high_risk[:5])}</div></div>', unsafe_allow_html=True)
    sr2.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid #ffd740"><div style="font-size:10px;color:#555">MODERATE RISK</div><div style="font-size:28px;font-weight:900;color:#ffd740">{len(mod_risk)}</div></div>', unsafe_allow_html=True)
    sr3.markdown(f'<div style="background:#1c1f26;border-radius:10px;padding:14px;text-align:center;border-top:3px solid #00e676"><div style="font-size:10px;color:#555">LOW RISK</div><div style="font-size:28px;font-weight:900;color:#00e676">{len(low_risk)}</div></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ALERT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

elif page == "🔔 Alert System":
    st.markdown("# 🔔 Alert System")
    st.caption("Define conditions — get a daily digest of what triggered")

    with st.expander("ℹ️ How alerts work"):
        st.markdown("""
The alert system scans real-time data against your defined thresholds every time you open this page (cached for 15 minutes).

**Available alert types:**
- **VIX threshold** — alert when VIX crosses a level
- **Sector RS flip** — when a sector changes quadrant on the RRG
- **Stock SMA cross** — when price crosses above/below SMA50 or SMA200
- **Momentum score change** — when a stock's score drops below or rises above a threshold
- **New 52W high/low** — breakout or breakdown alerts
        """)

    # Alert definitions in session state
    if "alerts" not in st.session_state:
        st.session_state["alerts"] = [
            {"type": "VIX",        "condition": "above", "value": 25,  "label": "VIX spike warning"},
            {"type": "VIX",        "condition": "below", "value": 15,  "label": "VIX low — complacency"},
            {"type": "Breadth",    "condition": "below", "value": 45,  "label": "Breadth deteriorating"},
            {"type": "Momentum",   "ticker": "NVDA",  "condition": "below", "value": 50, "label": "NVDA momentum falling"},
            {"type": "Momentum",   "ticker": "VFV",   "condition": "below", "value": 45, "label": "S&P proxy weakening"},
        ]

    # Add new alert
    st.markdown("### ➕ Add Alert")
    ac1, ac2, ac3, ac4, ac5 = st.columns([2, 2, 1.5, 2, 1])
    with ac1:
        alert_type = st.selectbox("Type", ["VIX", "Momentum", "Breadth", "Yield Spread", "DXY"])
    with ac2:
        if alert_type == "Momentum":
            alert_ticker = st.text_input("Ticker", value="NVDA").upper()
        else:
            alert_ticker = None
    with ac3:
        alert_cond = st.selectbox("Condition", ["above", "below"])
    with ac4:
        alert_val = st.number_input("Threshold", value=25.0, step=0.5)
    with ac5:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        if st.button("Add"):
            label = f"{alert_type}{' ' + alert_ticker if alert_ticker else ''} {alert_cond} {alert_val}"
            new_alert = {"type": alert_type, "condition": alert_cond, "value": float(alert_val), "label": label}
            if alert_ticker:
                new_alert["ticker"] = alert_ticker
            st.session_state["alerts"].append(new_alert)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Scan alerts
    st.markdown("### 📡 Live Alert Scan")

    with st.spinner("Scanning all alert conditions…"):
        macro_live = fetch_macro_data()
        vix_live   = macro_live.get("VIX", {}).get("price", 18)
        y10_live   = macro_live.get("10Y Yield", {}).get("price", 4.0)
        y2_live    = macro_live.get("2Y Yield", {}).get("price", 4.5)
        dxy_live   = macro_live.get("DXY (USD)", {}).get("ret_1m", 0)

        # Fetch breadth for breadth alerts
        try:
            breadth_live = fetch_breadth_data()
            breadth_a50  = breadth_live.get("above_50_pct", 55)
        except Exception:
            breadth_a50 = 55

    triggered = []
    not_triggered = []

    for alert in st.session_state["alerts"]:
        atype = alert["type"]
        cond  = alert["condition"]
        val   = alert["value"]

        current_val = None
        unit = ""

        if atype == "VIX":
            current_val = vix_live
        elif atype == "Yield Spread":
            current_val = y10_live - y2_live
            unit = "%"
        elif atype == "DXY":
            current_val = dxy_live
            unit = "% 1M"
        elif atype == "Breadth":
            current_val = breadth_a50
            unit = "%"
        elif atype == "Momentum":
            ticker = alert.get("ticker", "")
            if ticker:
                try:
                    sig = fetch_stock_momentum([ticker])
                    current_val = sig.get(ticker, {}).get("score", 50)
                except Exception:
                    current_val = 50

        if current_val is None:
            continue

        fired = (cond == "above" and current_val > val) or (cond == "below" and current_val < val)

        entry = {**alert, "current": current_val, "unit": unit, "fired": fired}
        if fired:
            triggered.append(entry)
        else:
            not_triggered.append(entry)

    # Show triggered alerts first
    if triggered:
        st.markdown(f"#### 🚨 {len(triggered)} Alert(s) Triggered")
        for a in triggered:
            st.markdown(
                f'<div style="background:#1c1f26;border-radius:10px;padding:14px;'
                f'margin-bottom:8px;border:2px solid #ff5252;animation:pulse 1s infinite">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<div>'
                f'<span style="font-size:16px;font-weight:700;color:#ff5252">🚨 {a["label"]}</span><br>'
                f'<span style="font-size:12px;color:#aaa">{a["type"]}'
                f'{" — " + a["ticker"] if a.get("ticker") else ""} '
                f'is {a["condition"]} {a["value"]}{a["unit"]}</span>'
                f'</div>'
                f'<div style="text-align:right">'
                f'<span style="font-size:22px;font-weight:900;color:#ff5252">'
                f'{a["current"]:.1f}{a["unit"]}</span><br>'
                f'<span style="font-size:10px;color:#888">threshold: {a["value"]}{a["unit"]}</span>'
                f'</div></div></div>',
                unsafe_allow_html=True)
    else:
        st.success("✅ No alerts triggered — all conditions within normal range")

    if not_triggered:
        st.markdown("---")
        st.markdown("#### ⬜ Watching — Not Yet Triggered")
        for a in not_triggered:
            dist = abs(a["current"] - a["value"])
            pct_to_trigger = dist / max(abs(a["value"]), 1) * 100
            bar_fill = max(0, 100 - int(pct_to_trigger * 2))
            st.markdown(
                f'<div style="background:#1c1f26;border-radius:8px;padding:10px 14px;'
                f'margin-bottom:5px;border-left:3px solid #2d3139">'
                f'<div style="display:flex;justify-content:space-between;align-items:center">'
                f'<span style="font-size:13px;color:#aaa">{a["label"]}</span>'
                f'<span style="font-size:13px;color:#ddd">{a["current"]:.1f}{a["unit"]} '
                f'<span style="color:#555">/ threshold {a["value"]}{a["unit"]}</span></span>'
                f'</div>'
                f'{momentum_bar(bar_fill, "#5c7cfa")}'
                f'</div>',
                unsafe_allow_html=True)

    # Manage alerts
    st.markdown("---")
    st.markdown("#### ⚙️ Manage Alerts")
    for i, a in enumerate(st.session_state["alerts"]):
        col_l, col_r = st.columns([5, 1])
        col_l.markdown(f"**{a['label']}** — {a['type']} {a['condition']} {a['value']}")
        if col_r.button("🗑️", key=f"del_alert_{i}"):
            st.session_state["alerts"].pop(i)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ECONOMIC CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

elif page == "📅 Economic Calendar":
    st.markdown("# 📅 Economic Calendar")
    st.caption("Upcoming macro events + earnings dates for key tickers")

    with st.expander("ℹ️ Why the calendar matters"):
        st.markdown("""
**Never get caught by surprise on a macro event.** The biggest single-day moves in markets are almost always caused by scheduled events — FOMC decisions, CPI prints, NFP reports, earnings releases.

**Key events to watch:**
- 🔴 **FOMC** — Interest rate decisions. If they raise/cut unexpectedly, expect 1-3% moves in S&P 500 same day
- 🔴 **CPI** — Inflation data. Hot CPI = rate hike fears = tech selloff. Cool CPI = rally
- 🔴 **NFP** — Jobs data. Paradox: strong jobs = Fed stays high = bad for growth stocks short-term
- 🟡 **Earnings** — Your individual positions can move 10-20% on earnings day

**Strategy:** Avoid adding new positions 1-2 days before a major event you're uncertain about.
        """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🌍 Macro Events This Week")
        with st.spinner("Fetching economic calendar…"):
            econ_events = fetch_economic_calendar()

        if not econ_events:
            st.info("Economic calendar data unavailable. Check back during market hours.")
        else:
            now_str = datetime.now().strftime("%Y-%m-%d")
            for event in econ_events[:15]:
                impact = event.get("impact", "medium")
                ec = "#ff5252" if impact == "high" else "#ffd740"
                is_past = event.get("date", "") < now_str
                opacity = "opacity:0.5;" if is_past else ""
                forecast_str = f" · Forecast: {event['forecast']}" if event.get("forecast") and event["forecast"] not in ("—", "") else ""
                prev_str = f" · Prev: {event['previous']}" if event.get("previous") and event["previous"] not in ("—", "") else ""
                st.markdown(
                    f'<div style="background:#1c1f26;border-left:4px solid {ec};border-radius:0 8px 8px 0;'
                    f'padding:8px 12px;margin-bottom:5px;{opacity}">'
                    f'<div style="display:flex;justify-content:space-between">'
                    f'<b style="color:#ddd;font-size:12px">{event.get("event","")}</b>'
                    f'<span style="font-size:10px;color:#555">{event.get("country","")} · {event.get("time","")}</span>'
                    f'</div>'
                    f'<div style="font-size:10px;color:#888">{event.get("date","")}{forecast_str}{prev_str}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

    with col2:
        st.markdown("### 📊 Upcoming Earnings")
        st.caption("Key tickers across sectors + your portfolio holdings")

        earnings_tickers = [
            "NVDA", "MSFT", "AAPL", "META", "AMZN", "GOOGL", "TSLA",
            "SOUN", "BBAI", "LUNR", "CRWV", "APLD", "NNE", "OKLO",
            "QBTS", "RDDT", "NU", "WPM", "ENB",
        ]
        with st.spinner("Fetching earnings dates…"):
            earnings = fetch_earnings_calendar(earnings_tickers)

        if not earnings:
            st.info("Could not fetch earnings dates. yfinance data may be delayed.")
        else:
            for e in earnings[:15]:
                days_away = (datetime.strptime(e["date"], "%Y-%m-%d") - datetime.now()).days
                urgency_c = "#ff5252" if days_away <= 3 else ("#ffd740" if days_away <= 7 else "#5c7cfa")
                own_badge = ('  <span style="background:#1D9E7522;color:#1D9E75;border:1px solid #1D9E7544;'
                             'border-radius:3px;padding:1px 5px;font-size:9px">YOU OWN</span>'
                             if e["you_own"] else "")
                st.markdown(
                    f'<div style="background:#1c1f26;border-left:4px solid {urgency_c};border-radius:0 8px 8px 0;'
                    f'padding:8px 12px;margin-bottom:5px">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><b style="color:#ddd">{e["ticker"]}</b>{own_badge}</div>'
                    f'<div style="text-align:right">'
                    f'<span style="font-size:12px;color:{urgency_c}">{e["date"]}</span><br>'
                    f'<span style="font-size:10px;color:#555">in {days_away}d</span>'
                    f'</div></div></div>',
                    unsafe_allow_html=True)

    # Market hours reference
    st.markdown("---")
    st.markdown("### 🕐 Market Hours Reference")
    now_et = datetime.now()  # simplified
    mh_cols = st.columns(4)
    for i, (market, hours, tz) in enumerate([
        ("NYSE / NASDAQ", "9:30 AM – 4:00 PM", "Eastern"),
        ("TSX Toronto",   "9:30 AM – 4:00 PM", "Eastern"),
        ("Euronext Paris","9:00 AM – 5:30 PM", "CET"),
        ("Pre/Post Market","4:00 AM – 8:00 PM", "Eastern"),
    ]):
        mh_cols[i].markdown(
            f'<div style="background:#1c1f26;border-radius:8px;padding:10px;text-align:center">'
            f'<div style="font-size:11px;font-weight:700;color:#ddd">{market}</div>'
            f'<div style="font-size:10px;color:#5c7cfa">{hours}</div>'
            f'<div style="font-size:9px;color:#555">{tz}</div>'
            f'</div>', unsafe_allow_html=True)

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
    """Fetch StockTwits sentiment — free, no auth needed for basic data."""
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return {"bullish": 0, "bearish": 0, "total": 0, "bull_pct": 50, "available": False}
        data = resp.json()
        messages = data.get("messages", [])
        bullish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}) and m["entities"]["sentiment"].get("basic") == "Bullish")
        bearish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}) and m["entities"]["sentiment"].get("basic") == "Bearish")
        total = bullish + bearish
        bull_pct = round(bullish / total * 100, 1) if total > 0 else 50
        return {
            "bullish": bullish, "bearish": bearish,
            "total": len(messages), "bull_pct": bull_pct,
            "available": True,
        }
    except Exception:
        return {"bullish": 0, "bearish": 0, "total": 0, "bull_pct": 50, "available": False}


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
        "📡 Momentum Scanner",
        "💬 Social Sentiment",
        "🏢 Sector Drill-Down",
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
                            f'<div style="font-size:12px;color:#aaa">'
                            f'{st_d["total"]} messages · '
                            f'<b style="color:{"#00e676" if st_d["bull_pct"]>=50 else "#ff5252"}">{st_d["bull_pct"]:.0f}% bullish</b>'
                            f'</div>'
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

    if search_filings and ticker_input:
        with st.spinner(f"Looking up {ticker_input} on SEC EDGAR…"):
            cik = get_cik_from_ticker(ticker_input)

        if not cik:
            st.error(f"Could not find {ticker_input} on SEC EDGAR. Verify the ticker is a US-listed company.")
        else:
            st.success(f"Found: **{ticker_input}** → CIK `{cik}`")
            st.session_state["cik"] = cik
            st.session_state["filing_ticker"] = ticker_input
            st.session_state["form_type"] = form_type

            with st.spinner(f"Fetching recent {form_type} filings…"):
                filings = get_recent_filings(cik, form_type=form_type, count=8)
            st.session_state["filings"] = filings

    # Show filings if available
    if "filings" in st.session_state and st.session_state.get("filing_ticker") == ticker_input:
        filings = st.session_state["filings"]
        if not filings:
            st.warning(f"No {form_type} filings found for {ticker_input}.")
        else:
            st.markdown(f"### 📁 Recent {form_type} Filings — {ticker_input}")
            filing_labels = [f"{f['date']} — {f['form']} ({f['accession'][:12]}…)" for f in filings]
            selected_label = st.selectbox("Select filing to analyse", filing_labels)
            selected_idx   = filing_labels.index(selected_label)
            selected_filing = filings[selected_idx]

            col_a, col_b = st.columns([1, 4])
            with col_a:
                run_analysis = st.button("🤖 Analyse with AI", type="primary")
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

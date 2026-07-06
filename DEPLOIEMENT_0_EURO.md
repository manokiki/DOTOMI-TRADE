# DOTOMI-TRADE — Guide Déploiement 0 Euro

## Stack gratuite

| Composant | Service | Plan | Limite |
|---|---|---|---|
| Backend | Railway | Trial ($5 offert) | ~2 mois gratuit |
| Frontend | Vercel | Hobby | Illimité |
| Base de données | Supabase | Free | 500MB PostgreSQL |
| Cache Redis | Upstash | Free | 10 000 req/jour |
| Scheduler | GitHub Actions | Free | 2 000 min/mois |

---

## 1. Backend sur Railway

```bash
# Dans le dossier backend/
railway login
railway init
railway add postgresql   # base de données gratuite

# Variables d'environnement à configurer dans Railway
DATABASE_URL=postgresql://...  # auto-configuré par Railway
CORS_ALLOWED_ORIGINS=https://dotomi-trade.vercel.app
SYMBOLS_TO_SCAN=BTCUSDT,ETHUSDT,SOLUSDT
RISK_PCT_PER_TRADE=1.0
MAX_DAILY_LOSS_PCT=3.0
MAX_WEEKLY_LOSS_PCT=6.0

railway up
```

Le backend sera disponible sur `https://dotomi-trade.up.railway.app`

---

## 2. Frontend sur Vercel

```bash
# Dans le dossier frontend/
vercel login
vercel

# Variable d'environnement Vercel
VITE_API_URL=https://dotomi-trade.up.railway.app
```

---

## 3. Scheduler via GitHub Actions (GRATUIT — solution au sleep Railway)

Railway Free endort le backend après 15 min d'inactivité.
Solution : GitHub Actions ping le scanner toutes les 5 minutes.

Créer `.github/workflows/scanner.yml` :

```yaml
name: DOTOMI Scanner
on:
  schedule:
    - cron: '*/5 7-15 * * 1-5'  # Toutes les 5min pendant kill zones (UTC)
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Scan BTC
        run: |
          curl -s "${{ secrets.API_URL }}/scanner?symbol=BTCUSDT&timeframe=1h" > /dev/null
      - name: Scan ETH
        run: |
          curl -s "${{ secrets.API_URL }}/scanner?symbol=ETHUSDT&timeframe=1h" > /dev/null
      - name: Scan SOL
        run: |
          curl -s "${{ secrets.API_URL }}/scanner?symbol=SOLUSDT&timeframe=1h" > /dev/null
      - name: Macro update
        run: |
          curl -s "${{ secrets.API_URL }}/macro" > /dev/null
```

Ajouter dans GitHub Secrets : `API_URL=https://dotomi-trade.up.railway.app`

Le cron `*/5 7-15 * * 1-5` = toutes les 5 minutes, de 07h à 15h UTC, du lundi au vendredi.
Couvre exactement les kill zones London + New York.
Consomme ~300 minutes GitHub Actions par mois (budget : 2000 min).

---

## 4. APIs gratuites à configurer

### FRED API (données macro Fed, CPI, M2)
1. Aller sur https://fred.stlouisfed.org/docs/api/api_key.html
2. Créer un compte gratuit
3. Copier la clé API
4. Ajouter dans Railway : `FRED_API_KEY=votre_clé`

### Twelve Data (DXY, VIX, S&P500)
1. https://twelvedata.com/pricing — plan Free : 800 appels/jour
2. Créer un compte
3. Ajouter : `TWELVEDATA_API_KEY=votre_clé`

### CryptoPanic (news sentiment)
1. https://cryptopanic.com/developers/api/ — plan Free disponible
2. Ajouter : `CRYPTOPANIC_API_KEY=votre_clé`

### CoinGlass (funding rate, OI)
- Sans clé : le système utilise Binance Futures API directement (gratuit, sans limite)
- Avec clé CoinGlass Free : données plus riches

---

## 5. Variables .env backend (dev local)

```env
DATABASE_URL=sqlite+aiosqlite:///./dotomi_trade.db
SYMBOLS_TO_SCAN=BTCUSDT,ETHUSDT,SOLUSDT
DEFAULT_CAPITAL=100.0
RISK_PCT_PER_TRADE=1.0
MAX_DAILY_LOSS_PCT=3.0
MAX_WEEKLY_LOSS_PCT=6.0
MAX_DRAWDOWN_ABSOLUTE_PCT=15.0
MAX_LEVER_STANDARD=10
MIN_RRR=2.5
THRESHOLD_AUTHORIZED=85.0
FRED_API_KEY=
TWELVEDATA_API_KEY=
CRYPTOPANIC_API_KEY=
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## 6. Lancement local

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000

# Frontend (autre terminal)
cd frontend
npm install
npm run dev
```

---

## Coût réel mois par mois

| Mois | Coût | Notes |
|---|---|---|
| 1–2 | 0 EUR | Crédit Railway $5 |
| 3+ | ~5 USD/mois | Railway Hobby plan si crédit épuisé |

Alternative 0 coût permanent : **Render.com Free** + GitHub Actions pour le scheduler.
Render Free : pas de sleep sur les web services depuis 2024.

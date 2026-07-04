# DOTOMI-TRADE — v2.0
## Système de décision trading · 100 USD → 4 000 USD en 12 mois

---

## Lancement rapide (dev local)

```bash
# Backend
cd backend
cp .env.example .env          # configurer les clés API
pip install -r requirements.txt
uvicorn app.api.main:app --reload --port 8000

# Frontend (autre terminal)
cd frontend
cp .env.example .env
npm install
npm run dev
```

Ouvrir http://localhost:5173

---

## Corrections V2 appliquées

### Backend — 8 bugs corrigés

| # | Fichier | Correction |
|---|---|---|
| 1 | config.py | min_rrr 1.5→2.5, max_daily 5→3%, max_weekly 10→6% |
| 2 | binance_provider.py | Fichier vide → provider complet avec funding rate |
| 3 | scoring/engine.py | Kill zones exactes UTC, hors zone = 0 (trade bloqué) |
| 4 | scoring/engine.py | RRR < 2.5 = score 0 = rejet immédiat |
| 5 | scoring/engine.py | 9 critères (ajout macro + onchain) |
| 6 | risk/risk_center.py | Formule sizing exacte CDC, limites corrigées |
| 7 | risk/validation.py | 22 conditions avec état humain + macro |
| 8 | core/scanner.py | Pipeline complet : macro + human → validate → persist |
| 9 | db/models.py | TradingRuleSet valeurs corrigées + nouveaux modèles |
| 10 | api/main.py | Import session corrigé + tous les nouveaux endpoints |

### Frontend — cause page blanche résolue

L'App.jsx original importait `HumanCheckInPage` et `SystemSignalsPage`
qui n'existaient pas → crash silencieux → page blanche.
Ces 2 fichiers sont maintenant présents.

### Nouveaux fichiers créés

- `backend/app/macro/macro_scanner.py` — Fear & Greed, DXY, VIX, funding
- `frontend/src/pages/HumanCheckInPage.jsx` — check-in état humain
- `frontend/src/pages/SystemSignalsPage.jsx` — historique système

---

## Architecture

```
Backend (FastAPI) → PostgreSQL/SQLite
    ├── MacroScanner  : Fear&Greed, DXY, VIX, S&P500, funding, news
    ├── BinanceProvider : OHLCV WebSocket/REST
    ├── ScoringEngine : 9 critères, 100 points
    ├── ValidationEngine : 22 conditions
    └── RiskCenter    : sizing, limites, courbe capital

Frontend (React + Vite)
    ├── Dashboard, Scanner, Recommendation
    ├── Validation, RiskCenter, TradeRoom
    ├── HumanCheckIn (NOUVEAU), SystemSignals (NOUVEAU)
    ├── Journal, Analytics, Playbook
    └── Alerts, Settings
```

---

## Déploiement 0 euro

| Service | Usage | Coût |
|---|---|---|
| Railway | Backend + PostgreSQL | $5 crédit offert (~2 mois) |
| Vercel | Frontend | Gratuit illimité |
| GitHub Actions | Cron scanner kill zones | Gratuit (2000 min/mois) |

Cron GitHub Actions (`.github/workflows/scanner.yml`) :
```yaml
on:
  schedule:
    - cron: '*/5 7-15 * * 1-5'  # Kill zones UTC, lun-ven
```

---

## Objectif mathématique

- Capital : 100 → 4 000 USD en 12 mois (x40)
- Gain mensuel requis : +37.6%
- Fréquence : 5-7 trades AUTORISÉS/semaine
- Win rate hypothèse : 55%, R:R moyen : 2.8
- Expectancy : 1.09R par trade









# DOTOMI-TRADE — Corrections V2

## Fichiers modifiés et ajoutés

### BACKEND

#### `app/config.py` — REMPLACER ENTIÈREMENT
- `min_rrr` : 1.5 → **2.5** (CDC section 9)
- `max_daily_loss_pct` : 5.0 → **3.0** (CDC section 9)
- `max_weekly_loss_pct` : 10.0 → **6.0**
- `hard_safety_cap` : 10.0 → **3.0**
- Ajout poids `weight_macro = 5.0` et `weight_onchain = 5.0`
- Ajout seuils kill zones exacts (London 07h-10h, NY 12h-15h)
- Ajout seuils macro : DXY, VIX, Fear & Greed, funding rate

#### `app/data/binance_provider.py` — REMPLACER ENTIÈREMENT
- Le fichier était vide — maintenant complet
- REST API Binance Futures + fallback Spot
- `get_funding_rate()` et `get_open_interest()` ajoutés
- Gestion erreurs + timeout

#### `app/scoring/engine.py` — REMPLACER ENTIÈREMENT
- Kill zones corrigées : London 07h-10h UTC, NY 12h-15h UTC
- Hors kill zone = score timing 0 = trade bloqué (était score 55 avant)
- Score timing peut maintenant atteindre 100 (était plafonné à 80)
- 9 critères au lieu de 7 (ajout macro + onchain)
- `compute_levels()` avec logique OB/Fib/swing réelle
- `_has_fvg()`, `_has_order_block()` : détection ICT
- `min_rrr` respecte maintenant 2.5

#### `app/scoring/indicators.py` — REMPLACER ENTIÈREMENT
- Swing highs/lows vectorisés (numpy) — plus de boucle O(n²)
- Ajout `vol_ma20` pour le score de confirmation

#### `app/risk/risk_center.py` — REMPLACER ENTIÈREMENT
- Toutes les limites corrigées (3%/6%/15%)
- `compute_position_size()` : formule exacte du CDC + ajustement macro
- `record_trade_result()` : 3 stops consécutifs = session bloquée
- `CAPITAL_CURVE` : courbe cible x40 en 12 mois

#### `app/risk/validation.py` — REMPLACER ENTIÈREMENT
- 22 conditions (était 9)
- Intégration `HumanState` (6 variables)
- Vérification contexte macro (CRISIS bloque tout)
- VIX > 35 bloquant
- Levier 20x conditionnel (score >= 92 + humain <= 3 + VIX < 20)

#### `app/macro/macro_scanner.py` — NOUVEAU FICHIER
- Collecte Fear & Greed (alternative.me)
- Funding rate Binance Futures (public, sans clé)
- DXY / VIX / S&P500 (Twelve Data — clé gratuite)
- News sentiment CryptoPanic
- Calendrier Forex Factory (structure en place)
- Calcul contexte : FAVORABLE / NEUTRAL / HOSTILE / CRISIS
- Score macro 0-5 pts pour le Scoring Engine

#### `app/db/models.py` — REMPLACER ENTIÈREMENT
- `HumanCheckIn` : nouveau modèle check-in humain
- `SystemTradeSignal` : historique de TOUS les signaux (pas seulement exécutés)
- `Trade` : ajout champs contexte macro + état humain + note post-trade + error_tag
- `TradeSetup` : ajout score_macro, score_onchain, contexte macro archivé
- `RiskEvent` et `MacroSnapshot` : nouveaux modèles pour analytics long terme

#### `app/api/main.py` — REMPLACER ENTIÈREMENT
- `POST /human/checkin` : saisie état humain
- `GET /human/checkin/today` : récupère check-in du jour
- `GET /system/signals` : historique signaux système
- `GET /macro` : données macro temps réel
- `POST /risk/sizing` : calcul sizing exact
- `GET /risk/summary` : résumé risk state
- `GET /capital/curve` : courbe capital cible vs réel
- `GET /scanner/all` : scan tous les actifs en un appel
- Archivage automatique de chaque signal dans `system_trade_signals`

---

### FRONTEND

#### `src/App.jsx` — REMPLACER ENTIÈREMENT
- Nouvelles routes : `/human` (Check-in) et `/signals` (Historique Système)
- Icônes SVG inline (conformes au design system — pas d'emoji)
- Badge "REQUIS" sur Check-in, "NOUVEAU" sur Historique Système

#### `src/lib/api.js` — REMPLACER ENTIÈREMENT
- Tous les nouveaux endpoints ajoutés
- `api.systemSignals()`, `api.getMacro()`, `api.createCheckIn()`, `api.getTodayCheckIn()`
- `api.computeSizing()`, `api.getRiskSummary()`, `api.getCapitalCurve()`, `api.scanAll()`

#### `src/pages/HumanCheckInPage.jsx` — NOUVEAU FICHIER
- Sliders pour fatigue, stress, confiance, sommeil
- Toggles pour FOMO et revenge mode
- Statut live avec blocages calculés en temps réel
- Ajustements affichés (levier réduit, risque réduit, session limitée)
- Pré-remplissage si check-in déjà effectué aujourd'hui

#### `src/pages/SystemSignalsPage.jsx` — NOUVEAU FICHIER
- Tableau de tous les signaux générés (exécutés ou non)
- Filtres par statut et par actif
- Ligne expandable : détail complet (9 sous-scores, niveaux, contexte macro, raisons)
- Barre de score visuelle par critère
- Badge "exécuté" avec ID du trade lié

---

### DÉPLOIEMENT

#### `DEPLOIEMENT_0_EURO.md` — NOUVEAU FICHIER
- Architecture complète Railway + Vercel + GitHub Actions
- Solution au sleep Railway : GitHub Actions cron 0-coût
- Cron configuré exactement sur les kill zones (07h-15h UTC, lun-ven)
- Guide complet des APIs gratuites (FRED, Twelve Data, CryptoPanic)
- Variables `.env` complètes

---

## Ordre d'intégration recommandé

1. Remplacer `config.py` en premier (corrige les paramètres critiques)
2. Remplacer `binance_provider.py` (active les vraies données)
3. Ajouter `app/macro/macro_scanner.py` (nouveau dossier à créer)
4. Remplacer `app/db/models.py` + relancer `init_db()`
5. Remplacer `app/scoring/engine.py` et `indicators.py`
6. Remplacer `app/risk/risk_center.py` et `validation.py`
7. Remplacer `app/api/main.py`
8. Frontend : remplacer `api.js` et `App.jsx`
9. Ajouter `HumanCheckInPage.jsx` et `SystemSignalsPage.jsx`
10. Configurer GitHub Actions pour le scheduler

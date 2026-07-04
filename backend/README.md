# DOTOMI-TRADE — Backend V1 étendu (scheduler 24h/24 + multi-marchés + Docker)

Système de décision pour le trading discrétionnaire assisté. Ce dépôt
contient le **backend complet du Niveau 1**, étendu avec un scan en continu
24h/24, le support multi-marchés (crypto + forex/actions), et la
conteneurisation Docker prête pour un déploiement robuste.

**Ce que ce système fait** : il scanne plusieurs marchés en continu, sans
intervention humaine, calcule un score déterministe sur 7 critères, applique
des règles de validation et de risque, persiste chaque décision, surveille
sa propre santé, et alerte par email quand un trade respecte toutes les
conditions — ou quand le système lui-même tombe en panne.

**Ce que ce système ne fait PAS** : il ne place aucun ordre. Il ne contient
aucune IA générative. Il ne garantit et n'affiche jamais un rendement
projeté — toute statistique vient uniquement de trades réellement
journalisés ou d'un backtest réellement exécuté (voir section "Garde-fou"
plus bas).

---

## 1. Ce qui est inclus dans cette version

### Niveau 1 (fondations, déjà présentes depuis la première livraison)

- Connecteur de données Binance (REST public) avec retry, backoff
  exponentiel et circuit breaker.
- Score Engine avec les 7 sous-scores pondérés et leurs formules complètes.
- Validation Engine appliquant les règles obligatoires et les blocages.
- Risk Center avec sizing par % de risque + ATR, et plafonds journaliers.
- Module de Backtest "walk-forward" pour mesurer l'edge réel sur historique.
- Journal et Analytics calculés uniquement à partir de trades réels.
- Alerting email avec template HTML complet et file de retry.
- Modèle de données complet (SQLAlchemy).

### Nouveau dans cette itération

- **Scheduler 24h/24** (`app/core/scheduler.py`) : boucle de fond qui scanne
  chaque symbole à intervalle régulier, indéfiniment, sans appel manuel à
  l'API. Un symbole en panne ne bloque jamais les autres (tâches asyncio
  isolées). Détecte les pannes répétées et envoie une alerte email
  *distincte* de l'alerting trading.
- **Multi-marchés** (`app/data/registry.py`, `app/data/twelvedata_provider.py`) :
  un `MarketRegistry` route chaque actif vers le bon fournisseur de données
  selon son marché (`crypto` → Binance, `forex`/`stocks` → Twelve Data). Un
  marché sans provider configuré est ignoré proprement plutôt que de faire
  planter le système.
- **Intégration scheduler + API** : le scheduler démarre automatiquement en
  tâche de fond au lancement de l'API si `SCHEDULER_ENABLED=true`, et
  s'arrête proprement à l'extinction.
- **Endpoints de monitoring étendus** : `/health/markets` (santé par
  marché) et `/health/system` (historique agrégé de `SystemHealthLog`,
  utilisable comme dashboard de santé minimal sans Grafana).
- **Conteneurisation Docker complète** : `Dockerfile` (API),
  `docker/Dockerfile.scheduler` (process de scan séparé, pour qu'un
  redémarrage de l'API n'interrompe jamais le scan), `docker-compose.yml`
  orchestrant API + scheduler + PostgreSQL/TimescaleDB, et
  `docker/timescale_setup.sql` pour convertir `market_snapshots` en
  hypertable.
- **9 tests supplémentaires** couvrant le scheduler (persistance continue,
  isolation des pannes, déclenchement unique de l'alerte système, tolérance
  aux marchés non configurés) — 27 tests au total, tous vérifiés.

### PAS encore inclus (prochaine itération)

- **Interface utilisateur (frontend React)** — seule l'API existe.
- **Authentification multi-utilisateurs** — V1 reste mono-utilisateur
  (`DEFAULT_USER_ID = 1`).
- **Niveaux 2 à 4 de sophistication** (sentiment, news, recalibrage
  automatique) — volontairement absents, conformément à la méthodologie
  validée : on ne sophistique pas avant d'avoir mesuré l'edge du Niveau 1
  sur un vrai backtest long.

---

## 2. Garde-fou non négociable

Ce système ne doit **jamais** être modifié pour afficher un chiffre de
performance (taux de réussite, rendement projeté, probabilité d'atteindre
un objectif) qui ne provient pas d'un calcul réel sur des trades
effectivement journalisés (`/analytics`) ou d'un backtest réellement
exécuté (`scripts/run_backtest.py`). Si vous étendez ce système, conservez
ce principe : un chiffre affiché à l'utilisateur doit toujours pouvoir être
retracé jusqu'à la donnée réelle qui l'a produit.

---

## 3. Structure du projet

```
dotomi-trade/
├── app/
│   ├── config.py                   # Configuration centralisée
│   ├── core/
│   │   ├── scanner.py               # données -> score -> validation -> alerte
│   │   ├── scheduler.py             # NOUVEAU : boucle de scan 24h/24, multi-symboles
│   │   └── backtest.py              # Backtest walk-forward
│   ├── data/
│   │   ├── base.py                  # Interface MarketDataProvider
│   │   ├── binance_provider.py      # Crypto (retry + circuit breaker)
│   │   ├── twelvedata_provider.py   # NOUVEAU : forex + actions
│   │   ├── registry.py              # NOUVEAU : routage multi-marchés
│   │   └── mock_provider.py         # Données simulées (tests sans réseau)
│   ├── scoring/
│   │   ├── indicators.py
│   │   └── engine.py
│   ├── risk/
│   │   ├── risk_center.py
│   │   └── validation.py
│   ├── alerting/
│   │   └── email_alerts.py
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── api/
│       └── main.py                  # Endpoints REST + intégration scheduler
├── docker/
│   ├── Dockerfile.scheduler         # NOUVEAU
│   └── timescale_setup.sql          # NOUVEAU
├── scripts/
│   └── run_backtest.py
├── tests/
│   ├── test_scoring_engine.py
│   ├── test_risk_center.py
│   ├── test_validation_engine.py
│   └── test_scheduler.py            # NOUVEAU
├── Dockerfile                       # NOUVEAU (API)
├── docker-compose.yml               # NOUVEAU
├── requirements.txt
├── pytest.ini                       # NOUVEAU (mode asyncio)
├── .env.example
└── README.md
```

---

## 4. Installation et lancement (sans Docker — développement local)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

pytest tests/ -v          # 27 tests, tous doivent passer

# Lancer l'API seule (scan à la demande via /scanner) :
uvicorn app.api.main:app --reload --port 8000

# OU lancer le scan en continu en process séparé :
python -m app.core.scheduler
```

Pour activer le scan automatique *intégré à l'API* plutôt qu'en process
séparé, mettre `SCHEDULER_ENABLED=true` dans `.env` avant de lancer
`uvicorn`.

---

## 5. Lancement avec Docker (recommandé pour un fonctionnement 24h/24 réel)

```bash
cp .env.example .env
# Éditer .env : configurer au minimum POSTGRES_PASSWORD, et les identifiants
# SMTP si vous voulez des alertes email réelles.

docker compose up -d --build

# Convertir market_snapshots en hypertable TimescaleDB (une seule fois) :
docker compose exec db psql -U dotomi -d dotomi_trade -f /dev/stdin < docker/timescale_setup.sql

# Suivre les logs du scan en continu :
docker compose logs -f scheduler

# Suivre les logs de l'API :
docker compose logs -f api
```

Trois services démarrent : `db` (PostgreSQL+TimescaleDB), `api` (REST, scan
à la demande), `scheduler` (scan en continu, process indépendant). Isoler
le scheduler de l'API garantit qu'un déploiement ou un crash de l'un ne
coupe jamais l'autre.

**Note de transparence** : ce `docker-compose.yml` et les deux Dockerfiles
ont été écrits et leur syntaxe (YAML) validée, mais n'ont pas pu être
réellement construits et lancés dans l'environnement où ce code a été
préparé (pas de Docker disponible). Testez `docker compose up --build`
vous-même avant de considérer le déploiement comme acquis — c'est une
limite honnête à vérifier, pas une garantie déjà faite.

---

## 6. Comprendre le Scheduler (scan 24h/24)

`app/core/scheduler.py` lance une tâche asyncio indépendante par symbole
configuré. Chaque tâche :

1. attend son `interval_seconds`,
2. récupère les données via le provider du bon marché (`MarketRegistry`),
3. calcule le score, valide, persiste, alerte si autorisé (exactement le
   même `scan_symbol` que l'endpoint `/scanner` utilise à la demande),
4. journalise sa propre santé (`SystemHealthLog`),
5. en cas d'échec répété (3 par défaut), envoie une alerte de panne
   système — une seule fois, pas à chaque cycle, pour ne pas spammer.

Un symbole dont le marché n'a pas de provider enregistré (ex: `forex` sans
clé Twelve Data configurée) est ignoré avec un simple avertissement dans
les logs, sans jamais faire échouer les autres symboles.

Pour changer la liste des actifs scannés en continu, modifier
`default_multi_market_targets()` dans `app/data/registry.py`.

---

## 7. Comprendre le multi-marchés

`MarketRegistry` (`app/data/registry.py`) associe un nom de marché
(`"crypto"`, `"forex"`, `"stocks"`) à un `MarketDataProvider`. Le Scanner et
le Score Engine ne savent jamais quel marché ils traitent — ils reçoivent
juste un DataFrame OHLCV normalisé, quel que soit le fournisseur d'origine.

Pour activer forex et actions, obtenir une clé API gratuite sur
twelvedata.com et la renseigner dans `.env` :

```
TWELVEDATA_API_KEY=votre_clé
```

Sans cette clé, `forex` et `stocks` restent simplement absents du registre
— le système continue de fonctionner normalement sur `crypto` seul.

Pour ajouter un nouveau marché ou fournisseur, il suffit d'implémenter
l'interface `MarketDataProvider` (`get_ohlcv`, `health_check`) et de
l'enregistrer dans `build_default_registry()`.

---

## 8. Comprendre le Score Engine sans lire le code

Le Score Engine calcule, pour chaque actif, 7 sous-scores entre 0 et 100,
qu'il combine en un score total selon les poids suivants :

| Sous-score | Poids | Ce qu'il mesure |
|---|---|---|
| Régime | 20 | Le marché est-il en tendance claire (ADX) ou en range ? |
| Structure | 20 | Y a-t-il une cassure récente de swing high/low dans le sens du biais ? |
| Liquidité | 15 | Y a-t-il eu un "sweep" récent (chasse aux stops) avant le mouvement ? |
| Pullback | 15 | Le retracement actuel est-il dans la zone optimale (38%-61%) ? |
| Timing | 10 | Sommes-nous dans une fenêtre horaire de volume favorable ? |
| Confirmation | 10 | La dernière bougie clôture-t-elle dans le sens du biais avec un RSI cohérent ? |
| Risque | 10 | Le ratio risque/rendement calculé est-il suffisant ? |

| Score total | Statut |
|---|---|
| 85-100 | Candidat à AUTORISÉ (sous réserve de validation, voir section 9) |
| 70-84 | Surveiller |
| 50-69 | Faible |
| 0-49 | Rejeté |

**Important** : un score élevé seul ne suffit jamais à autoriser un trade.
C'est le Validation Engine qui a le dernier mot.

---

## 9. Comprendre le Validation Engine et le Risk Center

Même avec un score total ≥ 85, un trade n'est **AUTORISÉ** que si TOUTES
ces conditions sont vraies en même temps :

- Un biais directionnel clair existe
- Le sous-score de pullback dépasse le seuil minimum configuré
- Le sous-score de timing dépasse le seuil minimum configuré
- Le sous-score de risque dépasse le seuil minimum configuré
- Le ratio risque/rendement dépasse le minimum configuré (1.5 par défaut)
- La perte journalière n'a pas atteint le plafond (5% par défaut)
- La perte hebdomadaire n'a pas atteint le plafond (10% par défaut)
- Le nombre de trades pris aujourd'hui n'a pas atteint le maximum (5 par défaut)

Le **Risk Center** calcule ensuite la taille de position avec la méthode la
plus conservatrice entre sizing par distance au stop et sizing par ATR. Un
plafond de sécurité absolu (10% par défaut) limite le risque par trade même
si la configuration utilisateur demande plus.

---

## 10. Activer les alertes email

1. Pour Gmail : activer la validation en deux étapes, créer un "mot de
   passe d'application" dédié.
2. Dans `.env` :
   ```
   SMTP_USER=votre-adresse@gmail.com
   SMTP_PASSWORD=le-mot-de-passe-application-généré
   ALERT_EMAIL_TO=adresse-qui-recevra-les-alertes@example.com
   ALERTS_ENABLED=true
   ```
3. Chaque setup `AUTHORIZED` déclenche un email avec tous les détails. Une
   panne système répétée déclenche un email *séparé* et distinct.

---

## 11. Lancer un backtest réel

```bash
python scripts/run_backtest.py --symbol BTCUSDT --timeframe 15m --candles 5000
```

Mesure le taux de réussite réel, le R moyen, le profit factor et le
drawdown maximum **sur l'échantillon testé** — jamais une garantie de
performance future. Voir le code pour la méthodologie complète
(walk-forward, aucune fuite d'information du futur vers le passé).

---

## 12. Lancer les tests

```bash
pytest tests/ -v
```

27 tests couvrent le Score Engine, le Risk Center, le Validation Engine, et
le Scheduler (persistance continue, isolation des pannes entre symboles,
déclenchement unique de l'alerte de panne système, tolérance aux marchés
non configurés).

---

## 13. Limites connues et honnêtes de cette livraison

- Le connecteur Binance et Twelve Data n'ont pas pu être testés contre les
  vraies APIs depuis l'environnement où ce code a été écrit (accès réseau
  restreint). Testez `python scripts/run_backtest.py` vous-même en premier.
- Le `docker-compose.yml` n'a pas pu être réellement construit/lancé
  (Docker absent de cet environnement) — la syntaxe YAML est validée, pas
  le comportement réel du build.
- Le scheduler tourne en tâche de fond `asyncio` dans le même process que
  l'API si `SCHEDULER_ENABLED=true`, ou en process Docker séparé via
  `docker compose`. Une vraie supervision de process (`systemd`,
  Kubernetes liveness probe) reste à mettre en place pour un redémarrage
  automatique en cas de crash du process lui-même (pas juste des erreurs
  internes au scan, déjà gérées).
- Pas encore d'authentification : `DEFAULT_USER_ID = 1` partout. À ajouter
  avant tout usage multi-utilisateurs.

---

## 14. Prochaines étapes recommandées

1. **Backtester réellement** sur plusieurs années de données Binance pour
   mesurer l'edge actuel du Score Engine.
2. **Tester réellement le déploiement Docker** dans un environnement avec
   Docker disponible, et corriger ce qui ne fonctionnerait pas du premier
   coup.
3. **Construire l'interface React** en consommant l'API existante
   (`/scanner`, `/recommendations/top`, `/health/system`...).
4. **Ajouter une vraie supervision de process** (systemd ou Kubernetes)
   pour le service scheduler en production.
5. **Ajouter l'authentification** pour un usage multi-utilisateurs.
6. **Ajouter les Niveaux 2 à 4** de sophistication, chacun validé par
   backtest avant activation.


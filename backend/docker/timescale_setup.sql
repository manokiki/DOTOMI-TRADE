-- DOTOMI-TRADE — Conversion de market_snapshots en hypertable TimescaleDB.
--
-- À exécuter UNE SEULE FOIS après le premier démarrage de l'application
-- contre une base PostgreSQL+TimescaleDB (les tables sont d'abord créées
-- par SQLAlchemy via init_db(), normalement, puis on convertit market_snapshots
-- en hypertable pour profiter du partitionnement temporel — section 2 et 6
-- du prompt maître : MarketSnapshot est une vraie série temporelle à fort
-- volume, c'est elle qui bénéficie le plus de TimescaleDB).
--
-- Usage :
--   docker compose exec db psql -U dotomi -d dotomi_trade -f /docker-entrypoint-initdb.d/timescale_setup.sql
-- ou simplement copier-coller dans un client psql connecté à la base.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- create_hypertable est idempotent avec if_not_exists => TRUE : sans danger
-- de le relancer par erreur.
SELECT create_hypertable(
    'market_snapshots',
    'timestamp',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- Politique de rétention optionnelle : décommenter pour purger automatiquement
-- les données de marché de plus de 2 ans une fois l'historique de backtest
-- jugé suffisant (à ajuster selon l'espace disque et le besoin réel de
-- ré-exécuter des backtests sur du très long terme).
-- SELECT add_retention_policy('market_snapshots', INTERVAL '2 years');

-- Index utile pour les requêtes fréquentes du Scanner (dernier snapshot par symbole).
CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_timestamp
    ON market_snapshots (symbol, timestamp DESC);

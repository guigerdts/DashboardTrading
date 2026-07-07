CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 484cf4edb40f

CREATE TABLE brokers (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_brokers PRIMARY KEY (id)
);

CREATE TABLE market_sessions (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_market_sessions PRIMARY KEY (id), 
    CONSTRAINT uq_market_sessions_name UNIQUE (name)
);

CREATE TABLE markets (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_markets PRIMARY KEY (id), 
    CONSTRAINT uq_markets_name UNIQUE (name)
);

CREATE TABLE timeframes (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_timeframes PRIMARY KEY (id), 
    CONSTRAINT uq_timeframes_name UNIQUE (name)
);

INSERT INTO alembic_version (version_num) VALUES ('484cf4edb40f') RETURNING version_num;

-- Running upgrade 484cf4edb40f -> 2e3b2ebec6d5

CREATE TABLE accounts (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    broker TEXT, 
    account_type TEXT, 
    base_currency TEXT NOT NULL, 
    status TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_accounts PRIMARY KEY (id), 
    CONSTRAINT ck_accounts_status CHECK (status IN ('active', 'inactive')), 
    CONSTRAINT uq_accounts_name UNIQUE (name)
);

CREATE TABLE assets (
    id INTEGER NOT NULL, 
    market_id INTEGER NOT NULL, 
    symbol TEXT NOT NULL, 
    name TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_assets PRIMARY KEY (id), 
    CONSTRAINT fk_assets_market_id_markets FOREIGN KEY(market_id) REFERENCES markets (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_assets_symbol_market UNIQUE (symbol, market_id)
);

CREATE TABLE trades (
    id INTEGER NOT NULL, 
    account_id INTEGER NOT NULL, 
    asset_id INTEGER NOT NULL, 
    direction TEXT NOT NULL, 
    status TEXT NOT NULL, 
    entry_price REAL NOT NULL, 
    quantity REAL NOT NULL, 
    entry_datetime TEXT NOT NULL, 
    broker_id INTEGER, 
    market_session_id INTEGER, 
    timeframe_id INTEGER, 
    strategy_id INTEGER, 
    setup_id INTEGER, 
    risk_profile_id INTEGER, 
    trading_session_id INTEGER, 
    exit_price REAL, 
    exit_datetime TEXT, 
    stop_loss REAL, 
    take_profit REAL, 
    position_size REAL, 
    commission REAL NOT NULL, 
    swap_fees REAL NOT NULL, 
    risk_amount REAL, 
    editable_until TEXT, 
    notes_override TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_trades PRIMARY KEY (id), 
    CONSTRAINT ck_trades_direction CHECK (direction IN ('long', 'short')), 
    CONSTRAINT ck_trades_status CHECK (status IN ('open', 'closed')), 
    CONSTRAINT ck_trades_commission CHECK (commission >= 0), 
    CONSTRAINT ck_trades_entry_price CHECK (entry_price > 0), 
    CONSTRAINT ck_trades_position_size CHECK (position_size >= 0), 
    CONSTRAINT ck_trades_quantity CHECK (quantity > 0), 
    CONSTRAINT ck_trades_swap_fees CHECK (swap_fees >= 0), 
    CONSTRAINT fk_trades_account_id_accounts FOREIGN KEY(account_id) REFERENCES accounts (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_trades_asset_id_assets FOREIGN KEY(asset_id) REFERENCES assets (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_trades_broker_id_brokers FOREIGN KEY(broker_id) REFERENCES brokers (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_market_session_id_market_sessions FOREIGN KEY(market_session_id) REFERENCES market_sessions (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_timeframe_id_timeframes FOREIGN KEY(timeframe_id) REFERENCES timeframes (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_strategy_id_strategies FOREIGN KEY(strategy_id) REFERENCES strategies (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_setup_id_setups FOREIGN KEY(setup_id) REFERENCES setups (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_risk_profile_id_risk_profiles FOREIGN KEY(risk_profile_id) REFERENCES risk_profiles (id) ON DELETE SET NULL, 
    CONSTRAINT fk_trades_trading_session_id_trading_sessions FOREIGN KEY(trading_session_id) REFERENCES trading_sessions (id) ON DELETE SET NULL
);

CREATE INDEX ix_trades_account_id ON trades (account_id);

CREATE INDEX ix_trades_asset_entry_datetime ON trades (asset_id, entry_datetime);

CREATE INDEX ix_trades_asset_id ON trades (asset_id);

CREATE INDEX ix_trades_broker_id ON trades (broker_id);

CREATE INDEX ix_trades_direction ON trades (direction);

CREATE INDEX ix_trades_entry_datetime ON trades (entry_datetime);

CREATE INDEX ix_trades_exit_datetime ON trades (exit_datetime);

CREATE INDEX ix_trades_market_session_id ON trades (market_session_id);

CREATE INDEX ix_trades_risk_profile_id ON trades (risk_profile_id);

CREATE INDEX ix_trades_setup_id ON trades (setup_id);

CREATE INDEX ix_trades_status_entry_datetime ON trades (status, entry_datetime);

CREATE INDEX ix_trades_strategy_entry_datetime ON trades (strategy_id, entry_datetime);

CREATE INDEX ix_trades_strategy_id ON trades (strategy_id);

CREATE INDEX ix_trades_timeframe_id ON trades (timeframe_id);

CREATE INDEX ix_trades_trading_session_id ON trades (trading_session_id);

UPDATE alembic_version SET version_num='2e3b2ebec6d5' WHERE alembic_version.version_num = '484cf4edb40f';

-- Running upgrade 2e3b2ebec6d5 -> 970bf55b0d74

CREATE TABLE setups (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    description TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_setups PRIMARY KEY (id), 
    CONSTRAINT uq_setups_name UNIQUE (name)
);

CREATE TABLE strategies (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    description TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_strategies PRIMARY KEY (id), 
    CONSTRAINT uq_strategies_name UNIQUE (name)
);

CREATE TABLE risk_profiles (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    strategy_id INTEGER, 
    max_risk_per_trade REAL, 
    position_sizing_method TEXT, 
    max_daily_loss REAL, 
    max_concurrent_trades INTEGER, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_risk_profiles PRIMARY KEY (id), 
    CONSTRAINT fk_risk_profiles_strategy_id_strategies FOREIGN KEY(strategy_id) REFERENCES strategies (id) ON DELETE SET NULL
);

CREATE INDEX ix_risk_profiles_strategy_id ON risk_profiles (strategy_id);

CREATE TABLE strategy_setups (
    strategy_id INTEGER NOT NULL, 
    setup_id INTEGER NOT NULL, 
    CONSTRAINT pk_strategy_setups PRIMARY KEY (strategy_id, setup_id), 
    CONSTRAINT fk_strategy_setups_setup_id_setups FOREIGN KEY(setup_id) REFERENCES setups (id) ON DELETE CASCADE, 
    CONSTRAINT fk_strategy_setups_strategy_id_strategies FOREIGN KEY(strategy_id) REFERENCES strategies (id) ON DELETE CASCADE
);

CREATE INDEX ix_strategy_setups_setup_id ON strategy_setups (setup_id);

UPDATE alembic_version SET version_num='970bf55b0d74' WHERE alembic_version.version_num = '2e3b2ebec6d5';

-- Running upgrade 970bf55b0d74 -> 93fa025b4e22

CREATE TABLE emotions (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_emotions PRIMARY KEY (id), 
    CONSTRAINT uq_emotions_name UNIQUE (name)
);

CREATE TABLE mistakes (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_mistakes PRIMARY KEY (id), 
    CONSTRAINT uq_mistakes_name UNIQUE (name)
);

CREATE TABLE tags (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_tags PRIMARY KEY (id), 
    CONSTRAINT uq_tags_name UNIQUE (name)
);

CREATE TABLE trading_sessions (
    id INTEGER NOT NULL, 
    name TEXT NOT NULL, 
    start_datetime TEXT NOT NULL, 
    end_datetime TEXT, 
    notes TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_trading_sessions PRIMARY KEY (id)
);

CREATE TABLE attachments (
    id INTEGER NOT NULL, 
    trade_id INTEGER NOT NULL, 
    file_path TEXT NOT NULL, 
    type TEXT NOT NULL, 
    original_name TEXT, 
    caption TEXT, 
    file_size_bytes INTEGER, 
    mime_type TEXT, 
    sort_order INTEGER NOT NULL, 
    created_at TEXT NOT NULL, 
    is_active INTEGER NOT NULL, 
    CONSTRAINT pk_attachments PRIMARY KEY (id), 
    CONSTRAINT ck_attachments_type CHECK (type IN ('image')), 
    CONSTRAINT fk_attachments_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE TABLE emotion_entries (
    id INTEGER NOT NULL, 
    trade_id INTEGER NOT NULL, 
    emotion_id INTEGER NOT NULL, 
    intensity INTEGER NOT NULL, 
    context TEXT NOT NULL, 
    notes TEXT, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_emotion_entries PRIMARY KEY (id), 
    CONSTRAINT ck_emotion_entries_context CHECK (context IN ('before_entry', 'during_trade', 'after_exit')), 
    CONSTRAINT ck_emotion_entries_intensity CHECK (intensity BETWEEN 1 AND 10), 
    CONSTRAINT fk_emotion_entries_emotion_id_emotions FOREIGN KEY(emotion_id) REFERENCES emotions (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_emotion_entries_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE INDEX ix_emotion_entries_emotion_id ON emotion_entries (emotion_id);

CREATE TABLE mistake_entries (
    id INTEGER NOT NULL, 
    trade_id INTEGER NOT NULL, 
    mistake_id INTEGER NOT NULL, 
    notes TEXT, 
    created_at TEXT NOT NULL, 
    CONSTRAINT pk_mistake_entries PRIMARY KEY (id), 
    CONSTRAINT fk_mistake_entries_mistake_id_mistakes FOREIGN KEY(mistake_id) REFERENCES mistakes (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_mistake_entries_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE INDEX ix_mistake_entries_mistake_id ON mistake_entries (mistake_id);

CREATE TABLE notes (
    id INTEGER NOT NULL, 
    trade_id INTEGER NOT NULL, 
    content TEXT NOT NULL, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    CONSTRAINT pk_notes PRIMARY KEY (id), 
    CONSTRAINT fk_notes_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE TABLE trade_reviews (
    id INTEGER NOT NULL, 
    trade_id INTEGER NOT NULL, 
    content TEXT, 
    lesson_learned TEXT, 
    created_at TEXT NOT NULL, 
    updated_at TEXT, 
    CONSTRAINT pk_trade_reviews PRIMARY KEY (id), 
    CONSTRAINT fk_trade_reviews_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE TABLE trade_tags (
    trade_id INTEGER NOT NULL, 
    tag_id INTEGER NOT NULL, 
    CONSTRAINT pk_trade_tags PRIMARY KEY (trade_id, tag_id), 
    CONSTRAINT fk_trade_tags_tag_id_tags FOREIGN KEY(tag_id) REFERENCES tags (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_trade_tags_trade_id_trades FOREIGN KEY(trade_id) REFERENCES trades (id) ON DELETE CASCADE
);

CREATE INDEX ix_trade_tags_tag_id ON trade_tags (tag_id);

UPDATE alembic_version SET version_num='93fa025b4e22' WHERE alembic_version.version_num = '970bf55b0d74';

-- Running upgrade 93fa025b4e22 -> 95da0ec91fc5

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('forex', '2026-07-07T13:54:46.456Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('indices', '2026-07-07T13:54:46.458Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('commodities', '2026-07-07T13:54:46.458Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('crypto', '2026-07-07T13:54:46.459Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('equities', '2026-07-07T13:54:46.459Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('bonds', '2026-07-07T13:54:46.459Z');

INSERT OR IGNORE INTO markets (name, created_at) VALUES ('etfs', '2026-07-07T13:54:46.460Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('asian', '2026-07-07T13:54:46.461Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('european', '2026-07-07T13:54:46.461Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('american', '2026-07-07T13:54:46.462Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('asian_european_overlap', '2026-07-07T13:54:46.462Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('european_american_overlap', '2026-07-07T13:54:46.462Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('weekend', '2026-07-07T13:54:46.463Z');

INSERT OR IGNORE INTO market_sessions (name, created_at) VALUES ('opening_auction', '2026-07-07T13:54:46.463Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('M1', '2026-07-07T13:54:46.464Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('M5', '2026-07-07T13:54:46.464Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('M15', '2026-07-07T13:54:46.465Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('M30', '2026-07-07T13:54:46.465Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('H1', '2026-07-07T13:54:46.465Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('H2', '2026-07-07T13:54:46.466Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('H4', '2026-07-07T13:54:46.466Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('D1', '2026-07-07T13:54:46.466Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('W1', '2026-07-07T13:54:46.467Z');

INSERT OR IGNORE INTO timeframes (name, created_at) VALUES ('MN', '2026-07-07T13:54:46.467Z');

UPDATE alembic_version SET version_num='95da0ec91fc5' WHERE alembic_version.version_num = '93fa025b4e22';

-- Running upgrade 95da0ec91fc5 -> e0843debd49b

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('calm', '2026-07-07T13:54:46.468Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('anxious', '2026-07-07T13:54:46.469Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('confident', '2026-07-07T13:54:46.470Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('fearful', '2026-07-07T13:54:46.470Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('greedy', '2026-07-07T13:54:46.470Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('neutral', '2026-07-07T13:54:46.471Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('excited', '2026-07-07T13:54:46.471Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('frustrated', '2026-07-07T13:54:46.471Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('disappointed', '2026-07-07T13:54:46.472Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('apathetic', '2026-07-07T13:54:46.472Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('hopeful', '2026-07-07T13:54:46.473Z');

INSERT OR IGNORE INTO emotions (name, created_at) VALUES ('regretful', '2026-07-07T13:54:46.473Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('fomo', '2026-07-07T13:54:46.473Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('revenge_trading', '2026-07-07T13:54:46.474Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('overtrading', '2026-07-07T13:54:46.474Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('no_stop_loss', '2026-07-07T13:54:46.475Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('moving_stop_loss', '2026-07-07T13:54:46.475Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('holding_losers', '2026-07-07T13:54:46.475Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('cutting_winners', '2026-07-07T13:54:46.476Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('ignoring_risk', '2026-07-07T13:54:46.476Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('bad_entry', '2026-07-07T13:54:46.476Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('no_plan', '2026-07-07T13:54:46.477Z');

INSERT OR IGNORE INTO mistakes (name, created_at) VALUES ('emotional_trading', '2026-07-07T13:54:46.477Z');

UPDATE alembic_version SET version_num='e0843debd49b' WHERE alembic_version.version_num = '95da0ec91fc5';


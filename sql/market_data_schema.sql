CREATE TABLE IF NOT EXISTS historical_market_data (
    id BIGSERIAL PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    adj_close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_historical_market_data_ticker_date UNIQUE (ticker, date),
    CONSTRAINT chk_historical_market_data_prices CHECK (
        open > 0 AND high > 0 AND low > 0 AND close > 0 AND adj_close > 0 AND volume >= 0
    )
);

CREATE INDEX IF NOT EXISTS ix_historical_market_data_ticker_date
    ON historical_market_data (ticker, date);

CREATE TABLE IF NOT EXISTS backtest_runs (
    backtest_run_id BIGSERIAL PRIMARY KEY,
    strategy_name VARCHAR(128) NOT NULL,
    ticker VARCHAR(32) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital NUMERIC(18, 2) NOT NULL,
    fee_rate NUMERIC(10, 6) NOT NULL DEFAULT 0.001,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

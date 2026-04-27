# populate_candle_db

Backfills historical OHLCV candlestick data from Binance.US (free, no API key) into your Postgres database.

## Setup

```bash
cd tools/populate_candle_db
pip install -r requirements.txt
```

Make sure `DATABASE_URL` is set in your `.env` file at the project root:
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Also make sure you've run `price_candles.sql` against your database first to create the tables.

## Usage

```bash
# Backfill 1h + 1d candles for all coins (1 year back) — recommended first run
python main.py

# Only specific coins
python main.py --coins bitcoin ethereum solana litecoin

# Only 1d candles (fastest, lowest row count)
python main.py --resolutions 1d

# All resolutions (1m is very slow — 1 year × 50 coins = 26M requests)
python main.py --resolutions 1h 1d

# Last 90 days only
python main.py --days 90

# Dry run — see what would be fetched without writing to DB
python main.py --dry-run
```

## Notes

- **1m candles are intentionally excluded from the default run.** Fetching 1 year of 1m candles for 50 coins would take hours and generate ~75M rows. Let your live candle builder populate 1m going forward instead.
- The tool uses `ON CONFLICT DO UPDATE` so it's safe to re-run — duplicates are overwritten, not doubled.
- Binance.US doesn't list every coin. Coins without a Binance listing are skipped and reported at the end.
- Rate limit: 150ms delay between requests — well within Binance.US free tier limits.

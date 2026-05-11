#!/usr/bin/env python3
"""
Score Orchestrator — Main
==========================
Coordinates all collectors, calculates scores, and writes to SQL + Redis.

Architecture:
  Collectors (rating/collectors/)   — fetch raw data from external APIs only
  Writers    (rating/writers/)      — own all SQL and Redis persistence
  Orchestrator (this file)          — coordinates, scores, writes

Flow per run:
  1. Cold-start: seed Redis from existing SQL rows
  2. Load coin lists for each collector
  3. Run all collectors (GitHub, holder diversity, tokenomics, public discourse)
  4. For each coin:
       a. Read manual_validation from SQL (default 25 if no row yet)
       b. Read previous community_dev_activity from SQL (for delta_commits)
       c. Score using scorer.py
       d. Compute overall_score = automated_score + manual_validation
       e. Upsert to rating_scores SQL
       f. Write crypto:rating:{coin_id} to Redis with REDIS_TTL

Usage:
    DATABASE_URL=... REDIS_URL=... GITHUB_TOKEN=... python main.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


# ── Env loading ────────────────────────────────────────────────────────────────
def _load_env():
    root_env  = Path(__file__).resolve().parents[2] / ".env"
    local_env = Path(__file__).resolve().parent / ".env"
    for env_file in [root_env, local_env]:
        if not env_file.exists():
            continue
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value

_load_env()

import config
import scorer
from writers import sql as sql_writer
from writers import redis_writer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors import github as github_collector
from collectors import holder_diversity as hd_collector
from collectors import tokenomics as tok_collector
from collectors import public_discourse as pd_collector

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("score-orchestrator")


# ── Coin loading ───────────────────────────────────────────────────────────────

def _load_json(path: str) -> list:
    p = Path(path)
    if not p.exists():
        logger.warning(f"Coins file not found: {path}")
        return []
    with open(p) as f:
        return json.load(f)


# ── Cold-start seed ────────────────────────────────────────────────────────────

def _seed_redis_from_sql():
    """Read all existing rating_scores rows and push them to Redis."""
    try:
        conn = sql_writer._get_conn()
        import psycopg2.extras
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT coin_id, coin_symbol, overall_score, automated_score,
                       manual_validation, risk_level,
                       security_transparency, tokenomics_utility,
                       community_dev_activity, public_discourse,
                       last_computed_at::text
                FROM rating_scores
            """)
            rows = [dict(r) for r in cur.fetchall()]
        redis_writer.seed_from_sql(rows, config.REDIS_TTL)
        logger.info(f"Cold-start seeded {len(rows)} coins from SQL into Redis")
    except Exception as exc:
        logger.warning(f"Cold-start seed failed (maybe first run): {exc}")


# ── Per-coin scoring ───────────────────────────────────────────────────────────

def score_coin(
    coin_id:         str,
    coin_symbol:     str,
    holder_data:     dict | None,
    tokenomics_data: dict | None,
    github_data:     dict | None,
    discourse_data:  dict | None,
) -> bool:
    """Score a single coin and write results to SQL + Redis."""
    # Read analyst score and previous GitHub data from SQL
    manual_validation = sql_writer.get_manual_validation(coin_id)
    prev_community    = sql_writer.get_previous_github_snapshot(coin_id)

    score_row = scorer.calculate(
        coin_id           = coin_id,
        coin_symbol       = coin_symbol,
        holder_data       = holder_data,
        tokenomics_data   = tokenomics_data,
        github_data       = github_data,
        discourse_data    = discourse_data,
        prev_community    = prev_community,
        manual_validation = manual_validation,
    )

    logger.info(
        f"[{coin_id}] overall={score_row['overall_score']} "
        f"(auto={score_row['automated_score']} + manual={manual_validation})"
    )

    sql_ok   = sql_writer.upsert_rating_score(score_row)
    redis_ok = redis_writer.write_score(score_row, config.REDIS_TTL)

    if not sql_ok:
        logger.error(f"[{coin_id}] SQL write failed")
    if not redis_ok:
        logger.warning(f"[{coin_id}] Redis write failed — data still in SQL")

    return sql_ok


# ── Main run ───────────────────────────────────────────────────────────────────

def run_once():
    logger.info("═" * 60)
    logger.info("Starting scoring cycle")

    # ── Load coin lists ──────────────────────────────────────────────────────
    github_coins    = _load_json(config.GITHUB_COINS_FILE)
    hd_coins        = _load_json(config.HOLDER_DIVERSITY_COINS_FILE)
    tok_raw         = _load_json(config.TOKENOMICS_COINS_FILE)
    pd_coins        = _load_json(config.PUBLIC_DISCOURSE_COINS_FILE)

    # ── Run tokenomics batch (single API call for all coins) ─────────────────
    tok_ids        = [c["coin_id"] for c in tok_raw if c.get("coin_id")]
    logger.info(f"Fetching tokenomics for {len(tok_ids)} coins …")
    tok_snapshots  = tok_collector.fetch_batch(tok_ids)
    tok_by_id      = {s["coin_id"]: s for s in tok_snapshots}

    # ── Run GitHub concurrently ───────────────────────────────────────────────
    logger.info(f"Fetching GitHub data for {len(github_coins)} coins …")
    github_by_id: dict[str, dict | None] = {}

    def _fetch_github(coin):
        return coin["coin_id"], github_collector.fetch(
            coin, token=config.GITHUB_TOKEN
        )

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch_github, c): c for c in github_coins}
        for fut in as_completed(futures):
            cid, result = fut.result()
            github_by_id[cid] = result

    # ── Run holder diversity (sequential — Covalent can be rate-sensitive) ───
    logger.info(f"Fetching holder diversity for {len(hd_coins)} coins …")
    hd_by_id: dict[str, dict | None] = {}
    for coin in hd_coins:
        hd_by_id[coin["coin_id"]] = hd_collector.fetch(coin, config.COVALENT_API_KEY)

    # ── Run public discourse (sequential — Trends has strict rate limits) ────
    logger.info(f"Fetching public discourse for {len(pd_coins)} coins …")
    pd_by_id: dict[str, dict | None] = {}
    for coin in pd_coins:
        pd_by_id[coin["coin_id"]] = pd_collector.fetch(coin, config.NEWSAPI_KEY)

    # ── Build master coin list (union of all coin IDs seen) ──────────────────
    all_ids = sorted({
        *[c["coin_id"] for c in github_coins],
        *[c["coin_id"] for c in hd_coins],
        *tok_ids,
        *[c["coin_id"] for c in pd_coins],
    })

    # Build symbol lookup from any available source
    symbol_lookup: dict[str, str] = {}
    for coins_list in [github_coins, hd_coins, tok_raw, pd_coins]:
        for c in coins_list:
            if c.get("coin_id") and c.get("symbol"):
                symbol_lookup[c["coin_id"]] = c["symbol"]

    # ── Score each coin ───────────────────────────────────────────────────────
    logger.info(f"Scoring {len(all_ids)} coins …")
    ok_count = fail_count = 0

    for coin_id in all_ids:
        symbol = symbol_lookup.get(coin_id, coin_id.upper()[:6])
        ok = score_coin(
            coin_id        = coin_id,
            coin_symbol    = symbol,
            holder_data    = hd_by_id.get(coin_id),
            tokenomics_data= tok_by_id.get(coin_id),
            github_data    = github_by_id.get(coin_id),
            discourse_data = pd_by_id.get(coin_id),
        )
        if ok:
            ok_count += 1
        else:
            fail_count += 1

    logger.info(
        f"Scoring cycle complete — "
        f"success: {ok_count}, failed: {fail_count}, total: {len(all_ids)}"
    )
    logger.info("═" * 60)


def main():
    if not config.DATABASE_URL:
        logger.error("DATABASE_URL is not set. Exiting.")
        sys.exit(1)
    if not config.REDIS_URL:
        logger.error("REDIS_URL is not set. Exiting.")
        sys.exit(1)

    # Initialise writers
    sql_writer.init(config.DATABASE_URL)
    redis_writer.init(config.REDIS_URL)

    # Cold-start seed
    _seed_redis_from_sql()

    interval = config.SCHEDULE_INTERVAL_SECONDS
    logger.info(f"Schedule: every {interval // 3600}h")

    while True:
        run_once()
        logger.info(f"Sleeping {interval}s until next run …")
        time.sleep(interval)


if __name__ == "__main__":
    main()

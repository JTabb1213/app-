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
from collectors.coin_registry import CoinRegistry
from collectors import github as github_collector
from collectors import tokenomics as tok_collector
from collectors import public_discourse as pd_collector
from collectors.decentralization_risk import base as decentral_collector

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
    coin_id:               str,
    coin_symbol:           str,
    decentralization_data: dict | None,
    tokenomics_data:       dict | None,
    github_data:           dict | None,
    discourse_data:        dict | None,
    # Legacy alias
    holder_data:           dict | None = None,
) -> bool:
    """
    Score a single coin and write results to SQL + Redis.

    If any collector returned None, the previous score for that category is
    preserved from SQL.  A WARNING is logged but nothing crashes and the
    frontend never sees a zero or an error — it just shows the last known data.
    """
    # Read analyst score and previous snapshots from SQL
    manual_validation = sql_writer.get_manual_validation(coin_id)
    prev_community    = sql_writer.get_previous_github_snapshot(coin_id)
    prev_row          = sql_writer.get_previous_score_row(coin_id)

    # ── Score each category, falling back to previous when collector returned None ──

    def _prev(key: str) -> dict | None:
        return prev_row.get(key) if prev_row else None

    # Security / decentralization
    _dec = decentralization_data or holder_data
    if _dec is not None:
        sec = scorer._score_security(_dec)
    elif _prev("security_transparency"):
        logger.warning(
            f"⚠  [{coin_id}] decentralization collector returned None — "
            f"reusing previous security score ({_prev('security_transparency').get('score')})"
        )
        sec = _prev("security_transparency")
    else:
        sec = {"score": 0, "max": 35, "metrics": {}, "note": "no data (first run)"}

    # Tokenomics
    if tokenomics_data is not None:
        tok = scorer._score_tokenomics(tokenomics_data)
    elif _prev("tokenomics_utility"):
        logger.warning(
            f"⚠  [{coin_id}] tokenomics collector returned None — "
            f"reusing previous tokenomics score ({_prev('tokenomics_utility').get('score')})"
        )
        tok = _prev("tokenomics_utility")
    else:
        tok = {"score": 0, "max": 20, "metrics": {}, "note": "no data (first run)"}

    # Community / GitHub
    if github_data is not None:
        com = scorer._score_community(github_data, prev_community)
    elif _prev("community_dev_activity"):
        logger.warning(
            f"⚠  [{coin_id}] GitHub collector returned None — "
            f"reusing previous community score ({_prev('community_dev_activity').get('score')})"
        )
        com = _prev("community_dev_activity")
    else:
        com = {"score": 0, "max": 15, "metrics": {}, "note": "no data (first run)"}

    # Public discourse
    if discourse_data is not None:
        disc = scorer._score_discourse(discourse_data)
    elif _prev("public_discourse"):
        logger.warning(
            f"⚠  [{coin_id}] discourse collector returned None — "
            f"reusing previous discourse score ({_prev('public_discourse').get('score')})"
        )
        disc = _prev("public_discourse")
    else:
        # scorer gives 2.5 neutral default when there is no data at all
        disc = scorer._score_discourse(None)

    automated = round(sec["score"] + tok["score"] + com["score"] + disc["score"], 2)
    overall   = round(min(automated + manual_validation, 100.0), 2)

    score_row = {
        "coin_id":                coin_id.lower(),
        "coin_symbol":            coin_symbol.upper(),
        "overall_score":          overall,
        "automated_score":        automated,
        "manual_validation":      round(manual_validation, 2),
        "risk_level":             scorer._risk_level(overall),
        "security_transparency":  sec,
        "tokenomics_utility":     tok,
        "community_dev_activity": com,
        "public_discourse":       disc,
    }

    logger.info(
        f"[{coin_id}] overall={overall} "
        f"(auto={automated} + manual={manual_validation})"
    )

    # SQL-first: write to Postgres, then populate Redis from the returned row
    # (guarantees Redis has exactly what the DB stored: score_history, review_status, etc.)
    returned_row = sql_writer.upsert_rating_score(score_row)
    if returned_row is None:
        logger.error(f"✗  [{coin_id}] SQL write failed — score NOT persisted")
        return False

    redis_ok = redis_writer.write_score(returned_row, config.REDIS_TTL)
    if not redis_ok:
        logger.warning(f"⚠  [{coin_id}] Redis write failed — data still in SQL")

    return True


# ── Main run ───────────────────────────────────────────────────────────────────

def run_once():
    logger.info("═" * 60)
    logger.info("Starting scoring cycle")

    # ── Load coin lists ──────────────────────────────────────────────────────
    registry        = CoinRegistry()
    github_coins    = registry.get_github_coins()
    decentral_coins = registry.get_decentralization_coins()
    tok_raw         = registry.get_tokenomics_coins()
    pd_coins        = registry.get_discourse_coins()

    # ── Run tokenomics batch (single API call for all coins) ─────────────────
    tok_ids       = [c["coin_id"] for c in tok_raw if c.get("coin_id")]
    logger.info(f"Fetching tokenomics for {len(tok_ids)} coins …")
    tok_by_id: dict[str, dict | None] = {}
    try:
        tok_snapshots = tok_collector.fetch_batch(tok_ids)
        tok_by_id     = {s["coin_id"]: s for s in tok_snapshots}
    except Exception as exc:
        logger.error(
            f"✗  tokenomics batch CRASHED — previous scores will be reused. Error: {exc}",
            exc_info=True,
        )

    # ── Run GitHub concurrently ───────────────────────────────────────────────
    logger.info(f"Fetching GitHub data for {len(github_coins)} coins …")
    github_by_id: dict[str, dict | None] = {}

    def _fetch_github(coin):
        try:
            return coin["coin_id"], github_collector.fetch(
                coin, token=config.GITHUB_TOKEN
            )
        except Exception as exc:
            logger.error(
                f"✗  [{coin['coin_id']}] GitHub collector CRASHED: {exc}",
                exc_info=True,
            )
            return coin["coin_id"], None

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_fetch_github, c): c for c in github_coins}
        for fut in as_completed(futures):
            try:
                cid, result = fut.result()
                if result is None:
                    logger.warning(f"⚠  [{cid}] GitHub collector returned None")
                github_by_id[cid] = result
            except Exception as exc:
                cid = futures[fut].get("coin_id", "?")
                logger.error(f"✗  [{cid}] GitHub future raised: {exc}", exc_info=True)
                github_by_id[cid] = None

    # ── Run decentralization risk (sequential — external APIs can be rate-sensitive) ─
    logger.info(f"Fetching decentralization risk for {len(decentral_coins)} coins …")
    decentral_by_id: dict[str, dict | None] = {}
    _decentral_config = {
        "COVALENT_API_KEY":  config.COVALENT_API_KEY,
        "RATED_API_KEY":     getattr(config, "RATED_API_KEY", ""),
        "COINGECKO_API_KEY": config.COINGECKO_API_KEY,
    }
    for coin in decentral_coins:
        if "diversity_method" not in coin:
            coin["diversity_method"] = decentral_collector.get_method_for_coin(coin["coin_id"])
        try:
            result = decentral_collector.fetch(coin, _decentral_config)
            if result is None:
                logger.warning(
                    f"⚠  [{coin['coin_id']}] decentralization collector returned None "
                    f"— previous score will be reused"
                )
            decentral_by_id[coin["coin_id"]] = result
        except Exception as exc:
            logger.error(
                f"✗  [{coin['coin_id']}] decentralization collector CRASHED: {exc} "
                f"— previous score will be reused",
                exc_info=True,
            )
            decentral_by_id[coin["coin_id"]] = None

    # ── Run public discourse (sequential — Trends has strict rate limits) ────
    logger.info(f"Fetching public discourse for {len(pd_coins)} coins …")
    pd_by_id: dict[str, dict | None] = {}
    # Pre-fetch all Trends data in batches of 5 (one pass, cache results to disk)
    pd_collector.prefetch_trends_batch(pd_coins, config.SERPAPI_KEY)
    for coin in pd_coins:
        try:
            result = pd_collector.fetch(coin, config.NEWSAPI_KEY, serpapi_key=config.SERPAPI_KEY)
            if result is None:
                logger.warning(
                    f"⚠  [{coin['coin_id']}] discourse collector returned None "
                    f"— previous score will be reused"
                )
            pd_by_id[coin["coin_id"]] = result
        except Exception as exc:
            logger.error(
                f"✗  [{coin['coin_id']}] discourse collector CRASHED: {exc} "
                f"— previous score will be reused",
                exc_info=True,
            )
            pd_by_id[coin["coin_id"]] = None

    # ── Build master coin list (union of all coin IDs seen) ──────────────────
    all_ids = sorted({
        *[c["coin_id"] for c in github_coins],
        *[c["coin_id"] for c in decentral_coins],
        *tok_ids,
        *[c["coin_id"] for c in pd_coins],
    })

    # Build symbol lookup from registry
    symbol_lookup: dict[str, str] = {
        cid: registry.get_symbol(cid) for cid in registry.get_all_coin_ids()
    }

    # ── Score each coin ───────────────────────────────────────────────────────
    logger.info(f"Scoring {len(all_ids)} coins …")
    ok_count = fail_count = skip_count = 0

    for coin_id in all_ids:
        symbol = symbol_lookup.get(coin_id, coin_id.upper()[:6])
        try:
            ok = score_coin(
                coin_id               = coin_id,
                coin_symbol           = symbol,
                decentralization_data = decentral_by_id.get(coin_id),
                tokenomics_data       = tok_by_id.get(coin_id),
                github_data           = github_by_id.get(coin_id),
                discourse_data        = pd_by_id.get(coin_id),
            )
            if ok:
                ok_count += 1
            else:
                fail_count += 1
                logger.error(f"✗  [{coin_id}] score_coin returned False (SQL write failed)")
        except Exception as exc:
            skip_count += 1
            logger.error(
                f"✗  [{coin_id}] score_coin CRASHED — coin skipped, no DB update. "
                f"Error: {exc}",
                exc_info=True,
            )

    logger.info(
        f"Scoring cycle complete — "
        f"✓ {ok_count} scored  ✗ {fail_count} write-failed  ⚡ {skip_count} crashed  "
        f"total: {len(all_ids)}"
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
        try:
            run_once()
        except Exception as exc:
            logger.critical(
                f"✗✗ run_once() CRASHED with unhandled exception — "
                f"will retry after {interval}s. Error: {exc}",
                exc_info=True,
            )
        logger.info(f"Sleeping {interval}s until next run …")
        time.sleep(interval)


if __name__ == "__main__":
    main()

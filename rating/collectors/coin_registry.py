"""
Coin Registry
=============
Single source of truth for which coins the rating system processes.

Reads coin IDs from ``data/coin_aliases.json`` (the project-wide master list)
and merges with supplemental per-collector config (GitHub repos, EVM contracts,
vesting insider percentages, discourse subreddits, etc.).

Usage::

    from collectors.coin_registry import CoinRegistry

    registry = CoinRegistry()
    github_coins     = registry.get_github_coins()
    decentral_coins  = registry.get_decentralization_coins()
    tokenomics_coins = registry.get_tokenomics_coins()
    discourse_coins  = registry.get_discourse_coins()

Adding a new coin
-----------------
1. Add it to ``data/coin_aliases.json`` (the only required step).
2. Optionally add supplemental config to the dicts below:
   - ``GITHUB_CONFIG``        — owner/repo if it has a public GitHub repo
   - ``DIVERSITY_METHOD_MAP`` — decentralization scoring method
   - ``VESTING_DATA``         — insider_pct + circulating_ratio (vesting method)
   - ``EVM_CONTRACTS``        — chain_id + contract address (token_holders method)
   - ``_DISCOURSE_OVERRIDES`` — subreddits + search queries
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to the project-wide master coin list.
# Override with COIN_ALIASES_FILE env var (set in Docker to /rating/data/coin_aliases.json).
# Falls back to walking up the tree for local dev.
_ALIASES_FILE = Path(
    os.getenv(
        "COIN_ALIASES_FILE",
        str(Path(__file__).resolve().parents[2] / "data" / "coin_aliases.json"),
    )
)

# ── Supplemental GitHub config ─────────────────────────────────────────────────
# Only coins listed here are included in the GitHub collector.
GITHUB_CONFIG: dict[str, dict] = {
    "bitcoin":             {"owner": "bitcoin",             "repo": "bitcoin"},
    "ethereum":            {"owner": "ethereum",            "repo": "go-ethereum"},
    "solana":              {"owner": "solana-labs",         "repo": "solana"},
    "chainlink":           {"owner": "smartcontractkit",    "repo": "chainlink"},
    "cardano":             {"owner": "IntersectMBO",        "repo": "cardano-node"},
    "polkadot":            {"owner": "paritytech",          "repo": "polkadot-sdk"},
    "cosmos":              {"owner": "cosmos",              "repo": "cosmos-sdk"},
    "avalanche-2":         {"owner": "ava-labs",            "repo": "avalanchego"},
    "near":                {"owner": "near",                "repo": "nearcore"},
    "aptos":               {"owner": "aptos-labs",          "repo": "aptos-core"},
    "sui":                 {"owner": "MystenLabs",          "repo": "sui"},
    "algorand":            {"owner": "algorand",            "repo": "go-algorand"},
    "tron":                {"owner": "tronprotocol",        "repo": "java-tron"},
    "uniswap":             {"owner": "Uniswap",             "repo": "v3-core"},
    "aave":                {"owner": "aave",                "repo": "aave-v3-core"},
    "the-graph":           {"owner": "graphprotocol",       "repo": "graph-node"},
    "filecoin":            {"owner": "filecoin-project",    "repo": "lotus"},
    "litecoin":            {"owner": "litecoin-project",    "repo": "litecoin"},
    "dogecoin":            {"owner": "dogecoin",            "repo": "dogecoin"},
    "zcash":               {"owner": "zcash",               "repo": "zcash"},
    "thorchain":           {"owner": "thorchain",           "repo": "thornode"},
    "optimism":            {"owner": "ethereum-optimism",   "repo": "optimism"},
    "arbitrum":            {"owner": "OffchainLabs",        "repo": "nitro"},
    "ripple":              {"owner": "XRPLF",               "repo": "rippled"},
    "stellar":             {"owner": "stellar",             "repo": "stellar-core"},
    "hedera-hashgraph":    {"owner": "hashgraph",           "repo": "hedera-services"},
    "injective-protocol":  {"owner": "InjectiveLabs",       "repo": "injective-core"},
    "kusama":              {"owner": "paritytech",          "repo": "polkadot-sdk"},
    "fantom":              {"owner": "Fantom-foundation",   "repo": "go-opera"},
    "the-open-network":    {"owner": "ton-blockchain",      "repo": "ton"},
    "lido-dao":            {"owner": "lidofinance",         "repo": "lido-dao"},
    "curve-dao-token":     {"owner": "curvefi",             "repo": "curve-contract"},
    "ethereum-name-service": {"owner": "ensdomains",        "repo": "ens-contracts"},
}

# ── Decentralization method mapping ───────────────────────────────────────────
# Maps coin_id → diversity_method.
# "not_implemented" coins receive a mid-level placeholder score (17/35)
# instead of 0, so they still get a fair automated score until proper data
# is available.
DIVERSITY_METHOD_MAP: dict[str, str] = {
    # ── PoW — hashrate / Nakamoto coefficient ──────────────────────────────
    "bitcoin":             "hashrate",
    "bitcoin-cash":        "hashrate",
    "dogecoin":            "hashrate",
    "litecoin":            "hashrate",
    "zcash":               "hashrate",
    "ethereum-classic":    "hashrate",

    # ── PoS — validator set (ETH-style, 33% finality threshold) ───────────
    "ethereum":            "validator",

    # ── PoS L1s — insider / vesting concentration is the primary risk ─────
    "solana":              "vesting",
    "cardano":             "vesting",
    "avalanche-2":         "vesting",
    "near":                "vesting",
    "aptos":               "vesting",
    "sui":                 "vesting",
    "cosmos":              "vesting",
    "polkadot":            "vesting",
    "the-open-network":    "vesting",
    "tron":                "vesting",
    "hedera-hashgraph":    "vesting",
    "algorand":            "vesting",
    "kusama":              "vesting",
    "fantom":              "vesting",
    "stellar":             "vesting",
    "ripple":              "vesting",
    "thorchain":           "vesting",
    "filecoin":            "vesting",
    "binancecoin":         "vesting",
    "hyperliquid":         "vesting",

    # ── ERC-20 / EVM tokens — richlist holder concentration ───────────────
    "chainlink":                    "token_holders",
    "uniswap":                      "token_holders",
    "aave":                         "token_holders",
    "shiba-inu":                    "token_holders",
    "pepe":                         "token_holders",
    "lido-dao":                     "token_holders",
    "the-graph":                    "token_holders",
    "curve-dao-token":              "token_holders",
    "loopring":                     "token_holders",
    "basic-attention-token":        "token_holders",
    "sushi":                        "token_holders",
    "yearn-finance":                "token_holders",
    "decentraland":                 "token_holders",
    "the-sandbox":                  "token_holders",
    "ocean-protocol":               "token_holders",
    "immutable-x":                  "token_holders",
    "havven":                       "token_holders",
    "compound-governance-token":    "token_holders",
    "injective-protocol":           "token_holders",
    "axie-infinity":                "token_holders",
    "optimism":                     "token_holders",
    "arbitrum":                     "token_holders",
    "ethereum-name-service":        "token_holders",

    # ── Not yet implemented — mid-level placeholder until data is available ─
}

# ── Vesting / insider allocation data ─────────────────────────────────────────
# Required for the "vesting" diversity method.  If a coin is mapped to
# "vesting" but has no entry here, it falls back to "not_implemented".
# Values are best-available public estimates — update as data improves.
VESTING_DATA: dict[str, dict] = {
    "solana": {
        "insider_pct":       51.2,
        "circulating_ratio": 0.62,
        "risk_flags":        ["FTX estate liquidations ongoing", "High VC concentration"],
    },
    "cardano":          {"insider_pct": 22.0,  "circulating_ratio": 1.00},
    "avalanche-2":      {"insider_pct": 25.0,  "circulating_ratio": 0.72},
    "near":             {"insider_pct": 35.0,  "circulating_ratio": 0.88},
    "aptos":            {"insider_pct": 51.0,  "circulating_ratio": 0.55},
    "sui":              {"insider_pct": 47.0,  "circulating_ratio": 0.50},
    "cosmos":           {"insider_pct": 20.0,  "circulating_ratio": 0.85},
    "polkadot":         {"insider_pct": 30.0,  "circulating_ratio": 0.96},
    "the-open-network": {"insider_pct": 25.0,  "circulating_ratio": 0.70},
    "tron":             {"insider_pct": 40.0,  "circulating_ratio": 0.95},
    "hedera-hashgraph": {"insider_pct": 40.0,  "circulating_ratio": 0.75},
    "algorand":         {"insider_pct": 30.0,  "circulating_ratio": 0.90},
    "kusama":           {"insider_pct": 20.0,  "circulating_ratio": 1.00},
    "fantom":           {"insider_pct": 18.0,  "circulating_ratio": 0.78},
    "stellar":          {"insider_pct": 18.0,  "circulating_ratio": 0.88},
    "ripple":           {"insider_pct": 47.0,  "circulating_ratio": 0.48},
    "thorchain":        {"insider_pct": 15.0,  "circulating_ratio": 1.00},
    "filecoin":         {
        "insider_pct":       15.0,
        "circulating_ratio": 0.55,
        "risk_flags":        ["Linear vesting ongoing"],
    },
    "binancecoin":      {"insider_pct": 40.0,  "circulating_ratio": 0.90},
}

# ── EVM contract addresses ─────────────────────────────────────────────────────
# Required for the "token_holders" diversity method via Covalent richlist.
# chain_id: 1=Ethereum, 10=Optimism, 56=BSC, 42161=Arbitrum.
# Coins mapped to token_holders but absent from this dict are demoted to
# "not_implemented" at registry build time.
EVM_CONTRACTS: dict[str, dict] = {
    "chainlink":                 {"chain_id": 1,     "contract": "0x514910771af9ca656af840dff83e8264ecf986ca"},
    "uniswap":                   {"chain_id": 1,     "contract": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"},
    "aave":                      {"chain_id": 1,     "contract": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9"},
    "shiba-inu":                 {"chain_id": 1,     "contract": "0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce"},
    "pepe":                      {"chain_id": 1,     "contract": "0x6982508145454ce325ddbe47a25d4ec3d2311933"},
    "lido-dao":                  {"chain_id": 1,     "contract": "0x5a98fcbea516cf06857215779fd812ca3bef1b32"},
    "the-graph":                 {"chain_id": 1,     "contract": "0xc944e90c64b2c07662a292be6244bdf05cda44a7"},
    "curve-dao-token":           {"chain_id": 1,     "contract": "0xd533a949740bb3306d119cc777fa900ba034cd52"},
    "loopring":                  {"chain_id": 1,     "contract": "0xbbbbca6a901c926f240b89eacb641d8aec7aeafd"},
    "basic-attention-token":     {"chain_id": 1,     "contract": "0x0d8775f648430679a709e98d2b0cb6250d2887ef"},
    "sushi":                     {"chain_id": 1,     "contract": "0x6b3595068778dd592e39a122f4f5a5cf09c90fe2"},
    "yearn-finance":             {"chain_id": 1,     "contract": "0x0bc529c00c6401aef6d220be8c6ea1667f6ad93e"},
    "decentraland":              {"chain_id": 1,     "contract": "0x0f5d2fb29fb7d3cfee444a200298f468908cc942"},
    "the-sandbox":               {"chain_id": 1,     "contract": "0x3845badade8e6dff049820680d1f14bd3903a5d0"},
    "ocean-protocol":            {"chain_id": 1,     "contract": "0x967da4048cd07ab37855c090aaf366e4ce1b9f48"},
    "immutable-x":               {"chain_id": 1,     "contract": "0xf57e7e7c23978c3caec3c3548e3d615c346e79ff"},
    "havven":                    {"chain_id": 1,     "contract": "0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f"},
    "compound-governance-token": {"chain_id": 1,     "contract": "0xc00e94cb662c3520282e6f5717214004a7f26888"},
    "injective-protocol":        {"chain_id": 1,     "contract": "0xe28b3b32b6c345a34ff64674606124dd5aceca30"},
    "axie-infinity":             {"chain_id": 1,     "contract": "0xbb0e17ef65f82ab018d8edd776e8dd940327b28b"},
    "optimism":                  {"chain_id": 10,    "contract": "0x4200000000000000000000000000000000000042"},
    "arbitrum":                  {"chain_id": 42161, "contract": "0x912ce59144191c1204e64559fe8253a0e49e6548"},
    "ethereum-name-service":     {"chain_id": 1,     "contract": "0xc18360217d8f7ab5e7c516566761ea12ce7f9d72"},
}

_CHAIN_NAME: dict[int, str] = {
    1:     "ethereum",
    10:    "optimism",
    56:    "bsc",
    42161: "arbitrum-one",
}

# ── Public discourse overrides ─────────────────────────────────────────────────
# Per-coin subreddits and search queries for the discourse collector.
# Coins not listed receive auto-generated defaults.
_DISCOURSE_OVERRIDES: dict[str, dict] = {
    "bitcoin":             {"subreddits": ["Bitcoin", "CryptoCurrency"],          "search_queries": ["Bitcoin", "BTC"]},
    "ethereum":            {"subreddits": ["ethereum", "CryptoCurrency"],         "search_queries": ["Ethereum", "ETH"]},
    "solana":              {"subreddits": ["solana", "CryptoCurrency"],           "search_queries": ["Solana", "SOL"]},
    "chainlink":           {"subreddits": ["Chainlink", "CryptoCurrency"],        "search_queries": ["Chainlink", "LINK"]},
    "cardano":             {"subreddits": ["cardano", "CryptoCurrency"],          "search_queries": ["Cardano", "ADA"]},
    "polkadot":            {"subreddits": ["dot", "CryptoCurrency"],              "search_queries": ["Polkadot", "DOT"]},
    "cosmos":              {"subreddits": ["cosmosnetwork", "CryptoCurrency"],    "search_queries": ["Cosmos", "ATOM"]},
    "avalanche-2":         {"subreddits": ["Avax", "CryptoCurrency"],            "search_queries": ["Avalanche", "AVAX"]},
    "ripple":              {"subreddits": ["Ripple", "CryptoCurrency"],           "search_queries": ["Ripple", "XRP"]},
    "dogecoin":            {"subreddits": ["dogecoin", "CryptoCurrency"],         "search_queries": ["Dogecoin", "DOGE"]},
    "shiba-inu":           {"subreddits": ["SHIBArmy", "CryptoCurrency"],         "search_queries": ["Shiba Inu", "SHIB"]},
    "litecoin":            {"subreddits": ["litecoin", "CryptoCurrency"],         "search_queries": ["Litecoin", "LTC"]},
    "binancecoin":         {"subreddits": ["binance", "CryptoCurrency"],          "search_queries": ["Binance Coin", "BNB"]},
    "tron":                {"subreddits": ["Tronix", "CryptoCurrency"],           "search_queries": ["TRON", "TRX"]},
    "uniswap":             {"subreddits": ["Uniswap", "CryptoCurrency"],          "search_queries": ["Uniswap", "UNI"]},
    "aave":                {"subreddits": ["Aave", "CryptoCurrency"],             "search_queries": ["Aave", "AAVE"]},
    "the-open-network":    {"subreddits": ["Toncoin", "CryptoCurrency"],          "search_queries": ["Toncoin", "TON"]},
    "hyperliquid":         {"subreddits": ["HyperliquidTrading", "CryptoCurrency"], "search_queries": ["Hyperliquid", "HYPE"]},
    "thorchain":           {"subreddits": ["thorchain", "CryptoCurrency"],        "search_queries": ["THORChain", "RUNE"]},
    "near":                {"subreddits": ["nearprotocol", "CryptoCurrency"],     "search_queries": ["NEAR Protocol", "NEAR"]},
    "stellar":             {"subreddits": ["Stellar", "CryptoCurrency"],          "search_queries": ["Stellar", "XLM"]},
    "hedera-hashgraph":    {"subreddits": ["hashgraph", "CryptoCurrency"],        "search_queries": ["Hedera", "HBAR"]},
    "filecoin":            {"subreddits": ["filecoin", "CryptoCurrency"],         "search_queries": ["Filecoin", "FIL"]},
    "ethereum-classic":    {"subreddits": ["EthereumClassic", "CryptoCurrency"],  "search_queries": ["Ethereum Classic", "ETC"]},
    "algorand":            {"subreddits": ["algorand", "CryptoCurrency"],         "search_queries": ["Algorand", "ALGO"]},
    "aptos":               {"subreddits": ["Aptos", "CryptoCurrency"],            "search_queries": ["Aptos", "APT"]},
    "sui":                 {"subreddits": ["SuiNetwork", "CryptoCurrency"],       "search_queries": ["Sui", "SUI"]},
    "injective-protocol":  {"subreddits": ["injective", "CryptoCurrency"],        "search_queries": ["Injective", "INJ"]},
    "arbitrum":            {"subreddits": ["arbitrum", "CryptoCurrency"],         "search_queries": ["Arbitrum", "ARB"]},
    "optimism":            {"subreddits": ["optimismFND", "CryptoCurrency"],      "search_queries": ["Optimism", "OP"]},
    "polkadot":            {"subreddits": ["Polkadot", "CryptoCurrency"],         "search_queries": ["Polkadot", "DOT"]},
    "pepe":                {"subreddits": ["pepecoin", "CryptoCurrency"],         "search_queries": ["Pepe", "PEPE"]},
    "bitcoin-cash":        {"subreddits": ["Bitcoincash", "CryptoCurrency"],      "search_queries": ["Bitcoin Cash", "BCH"]},
    "zcash":               {"subreddits": ["zec", "CryptoCurrency"],              "search_queries": ["Zcash", "ZEC"]},
    "kusama":              {"subreddits": ["Kusama", "CryptoCurrency"],           "search_queries": ["Kusama", "KSM"]},
    "fantom":              {"subreddits": ["FantomFoundation", "CryptoCurrency"], "search_queries": ["Fantom", "FTM"]},
}


# ── CoinRegistry ──────────────────────────────────────────────────────────────

class CoinRegistry:
    """
    Builds per-collector coin config lists from the master coin_aliases.json.
    """

    def __init__(self, aliases_file: Path = _ALIASES_FILE):
        self._aliases = self._load_aliases(aliases_file)
        logger.info(f"[CoinRegistry] Loaded {len(self._aliases)} coins from {aliases_file}")

    @staticmethod
    def _load_aliases(path: Path) -> dict:
        try:
            data = json.loads(path.read_text())
            return data.get("assets", {})
        except Exception as exc:
            logger.error(f"[CoinRegistry] Failed to load {path}: {exc}")
            return {}

    # ── Per-collector views ───────────────────────────────────────────────────

    def get_tokenomics_coins(self) -> list[dict]:
        """All coins → CoinGecko tokenomics (no extra config needed)."""
        return [
            {"coin_id": cid, "symbol": info["symbol"], "source": "coingecko"}
            for cid, info in self._aliases.items()
        ]

    def get_github_coins(self) -> list[dict]:
        """Coins with a known primary GitHub repo."""
        coins = []
        for cid, info in self._aliases.items():
            cfg = GITHUB_CONFIG.get(cid)
            if cfg:
                coins.append({
                    "coin_id": cid,
                    "symbol":  info["symbol"],
                    "source":  "github_api",
                    **cfg,
                })
        return coins

    def get_decentralization_coins(self) -> list[dict]:
        """
        All coins with resolved diversity_method and required extra fields.

        Resolution rules:
          - token_holders:  requires an EVM contract in EVM_CONTRACTS;
                            falls back to not_implemented otherwise.
          - vesting:        requires insider_pct data in VESTING_DATA;
                            falls back to not_implemented otherwise.
          - not_implemented: mid-level placeholder score (17/35) will be used.
        """
        coins = []
        for cid, info in self._aliases.items():
            method = DIVERSITY_METHOD_MAP.get(cid, "not_implemented")
            coin: dict = {
                "coin_id":          cid,
                "symbol":           info["symbol"],
                "diversity_method": method,
            }

            if method == "token_holders":
                evm = EVM_CONTRACTS.get(cid)
                if evm:
                    coin["chain"]            = _CHAIN_NAME.get(evm["chain_id"], "ethereum")
                    coin["chain_id"]         = evm["chain_id"]
                    coin["contract_address"] = evm["contract"]
                else:
                    logger.warning(
                        f"[CoinRegistry] {cid}: token_holders but no EVM contract "
                        f"→ not_implemented"
                    )
                    coin["diversity_method"] = "not_implemented"

            elif method == "vesting":
                vesting = VESTING_DATA.get(cid)
                if vesting:
                    coin.update(vesting)
                else:
                    logger.warning(
                        f"[CoinRegistry] {cid}: vesting but no insider_pct data "
                        f"→ not_implemented"
                    )
                    coin["diversity_method"] = "not_implemented"

            coins.append(coin)
        return coins

    def get_discourse_coins(self) -> list[dict]:
        """All coins with subreddits and search queries for public discourse."""
        coins = []
        for cid, info in self._aliases.items():
            symbol   = info["symbol"]
            override = _DISCOURSE_OVERRIDES.get(cid, {})
            # Auto-generate reasonable defaults for coins without overrides
            default_sub    = cid.replace("-", "").replace(" ", "")
            default_name   = cid.replace("-", " ").title()
            coins.append({
                "coin_id":        cid,
                "symbol":         symbol,
                "source":         "reddit_news_trends",
                "subreddits":     override.get("subreddits",     [default_sub, "CryptoCurrency"]),
                "search_queries": override.get("search_queries", [default_name, symbol]),
            })
        return coins

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_all_coin_ids(self) -> list[str]:
        return list(self._aliases.keys())

    def get_symbol(self, coin_id: str) -> str:
        return self._aliases.get(coin_id, {}).get("symbol", coin_id.upper()[:6])

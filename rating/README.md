# Rating System: Coin Types and Security Metrics

This document explains the rating architecture, the security/transparency categories, and how different coin types are grouped for the rating engine.

## Goals

- Group coins by their core security model and data source.
- Use method-aware metrics for security and transparency.
- Keep static assumptions separate from dynamic, weekly-updated measurements.
- Preserve the existing rating shape while making the score more explainable.

## Primary coin categories

### 1. PoW L1
Examples: `bitcoin`, `litecoin`, `zcash`, `bitcoin-cash`, `dogecoin`, `ethereum-classic`

These are native proof-of-work networks. The security model depends on hashrate and mining pool decentralization.

**Security metrics**
- `nakamoto_coefficient`
- `top_1_pct` pool share
- `top_10_pct` / `top_100_pct`
- miner / pool concentration
- ASIC/hardware centralization
- network difficulty/hashrate stability

**Transparency metrics**
- mining pool publication
- consensus rules clarity
- issuance schedule visibility
- clear reward model

### 2. PoS L1
Examples: `ethereum`, `solana`, `cardano`, `near`, `polkadot`, `avalanche-2`, `sui`, `cosmos`, `algorand`

Security depends on staking/validator decentralization and insider ownership.

**Security metrics**
- validator concentration (`nakamoto_coefficient` for stake)
- top staking entity share (`top_1_pct`)
- total staked % of supply
- validator count / delegation concentration
- slashing/finality risk

**Transparency metrics**
- staking economics published
- validator identity / entity disclosure
- upgradeability and governance clarity
- inflation schedule and issuance rules

### 3. L2 / Rollups / Appchains
Examples: `optimism`, `arbitrum`, `immutable-x`, maybe `the-open-network`

Security depends on the underlying L1 plus operator/bridge design.

**Security metrics**
- L1 dependency and finality model
- sequencer/operator centralization
- challenge window length
- fraud-proof / validity-proof construction
- bridge custody risk

**Transparency metrics**
- operator control disclosures
- upgrade key and governance ownership
- audit coverage for bridges and contracts
- data availability model explained

### 4. Token / ERC-20 style
Examples: `chainlink`, `uniswap`, `aave`, `sushi`, `the-graph`, `curve-dao-token`, `havven`

These tokens derive security from the host chain and from token distribution.

**Security metrics**
- top holder concentration (`top_1_pct`, `top_10_pct`)
- holder count
- richlist distribution
- treasury / team wallet concentration
- exchange custody concentration

**Transparency metrics**
- tokenomics publication
- allocation / vesting schedule disclosure
- admin/ownership key transparency
- audit reports for token contracts

### 5. Stablecoins / collateral-backed assets
Examples: `usd-peg` assets (not necessarily in this repo yet)

These require special treatment because security is largely off-chain and legal.

**Security metrics**
- collateral composition
- redemption mechanism
- counterparty risk

**Transparency metrics**
- reserve proofs / audits
- regulatory status
- disclosure frequency
- governance of reserve assets

### 6. Hybrid / special cases
Examples: liquid staking derivatives, wrapped assets, governance tokens, tokenized products.

These should be treated as a separate category if their security assumptions differ from pure PoW/PoS/token.

---

## Recommended schema overview

The rating database should separate:

1. `coins` — static metadata and consensus/category classification
2. `coin_security_profiles` — manual / analyst-owned security assumptions
3. subtype metadata tables — type-specific security metadata
   - `pow_native_metadata`
   - `pos_native_metadata`
   - `evm_layer2_metadata`
   - `stablecoin_metadata`
   - `token_metadata`
4. `rating_scores` — final automated + manual score output
5. `rating_score_history` — weekly score audit trail

This keeps:
- static protocol facts in one place
- type-specific metrics stored only where they are relevant
- the final score model clean and stable

## Subtype metadata tables

The schema now uses a single shared `coins` table plus separate metadata tables for each security model.

### `coins`
Contains fields common to every asset, including:
- `consensus_type`
- `network_layer`
- `token_category`
- `diversity_method`
- shared descriptive metadata

### `coin_security_profiles`
Stores analyst-reviewed information that is not expected to change weekly:
- security model description
- admin / governance risk
- upgradeability risk
- team / treasury allocation notes
- audit status

### `pow_native_metadata`
PoW-specific metadata:
- mining algorithm
- pool concentration
- hashrate Nakamoto coefficient
- mining transparency notes

### `pos_native_metadata`
PoS-specific metadata:
- validator count
- staked % of supply
- top validator/entity concentration
- delegation concentration
- unstake period

### `evm_layer2_metadata`
Layer 2 / rollup metadata:
- underlying L1
- sequencer centralization
- challenge window
- bridge / operator risk

### `stablecoin_metadata`
Stablecoin-specific metadata:
- reserve type
- audit frequency
- peg mechanism
- reserve transparency score
- issuer regulatory status

### `token_metadata`
Token-specific metadata:
- holder count
- top holder concentration
- treasury allocation
- vesting %
- contract admin / audit transparency

## How scores should be grouped

### Security & Transparency (35 pts)
This bucket is method-aware and should be computed from:
- PoW: hashrate / pool concentration
- PoS: validator and staking concentration
- Vesting-heavy L1s: insider allocation / circulating ratio
- Token-richlist: top holder concentration
- Rollups: operator/bridge centralization and L1 dependency

### Tokenomics & Utility (20 pts)
This bucket should reflect:
- supply cap / mint schedule
- inflation potential
- vesting / team allocation
- utility of the token within its protocol

### Community & Dev Activity (15 pts)
This bucket should reflect GitHub/repo activity, contributor distribution, and ongoing development.

### Public Discourse (5 pts)
This bucket should reflect sentiment and search interest.

---

## Proposed field mappings

The `coins` table should include metadata fields such as:

- `consensus_type` — `pow`, `pos`, `rollup`, `token`, `stable`, `hybrid`
- `network_layer` — `l1`, `l2`, `l3`, `sidechain`, `appchain`, `bridge`
- `token_category` — `native`, `erc20`, `stablecoin`, `liquid_staking`, `governance`, `other`
- `diversity_method` — `hashrate`, `validator`, `vesting`, `token_holders`, `rollup`, `not_implemented`

These fields are the basis for method-aware scoring.

## Notes

- `manual_validation` should remain as a stable override / analyst anchor.
- The scoring engine should treat static fields as facts, and subtype metadata as type-specific data.
- `security_transparency` should remain a JSONB output, with detailed metrics inside `metrics`.

---

## What to do next

If you want, I can also create a concrete migration plan for these fields, including:
- the updated `coins` schema
- the subtype metadata tables
- how to preserve existing `rating_scores`

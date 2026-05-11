// CCS Mock Data — will be replaced with real API calls

export const MOCK_TOKENS = [
  {
    id: "bitcoin",
    name: "Bitcoin",
    ticker: "BTC",
    overallScore: 82,
    reviewStatus: "complete",
    automated: {
      total: 63,
      security: { score: 24, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 13, max: 17, label: "Tokenomics & Utility" },
      community: { score: 11, max: 13, label: "Community & Dev Activity" },
      market: { score: 14, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 1, max: 2, label: "Public Discourse Signal" },
    },
    manual: {
      total: 19,
      team: { score: 7, max: 9, label: "Team & Identity" },
      vision: { score: 5, max: 7, label: "Vision & Clarity" },
      transparency: { score: 4, max: 5, label: "Transparency" },
      execution: { score: 3, max: 4, label: "Execution Reality" },
    },
  },
  {
    id: "ethereum",
    name: "Ethereum",
    ticker: "ETH",
    overallScore: 78,
    reviewStatus: "complete",
    automated: {
      total: 58,
      security: { score: 21, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 12, max: 17, label: "Tokenomics & Utility" },
      community: { score: 12, max: 13, label: "Community & Dev Activity" },
      market: { score: 12, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 1, max: 2, label: "Public Discourse Signal" },
    },
    manual: {
      total: 20,
      team: { score: 8, max: 9, label: "Team & Identity" },
      vision: { score: 6, max: 7, label: "Vision & Clarity" },
      transparency: { score: 3, max: 5, label: "Transparency" },
      execution: { score: 3, max: 4, label: "Execution Reality" },
    },
  },
  {
    id: "cardano",
    name: "Cardano",
    ticker: "ADA",
    overallScore: 61,
    reviewStatus: "pending",
    automated: {
      total: 61,
      security: { score: 22, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 14, max: 17, label: "Tokenomics & Utility" },
      community: { score: 10, max: 13, label: "Community & Dev Activity" },
      market: { score: 13, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 2, max: 2, label: "Public Discourse Signal" },
    },
    manual: null,
  },
  {
    id: "solana",
    name: "Solana",
    ticker: "SOL",
    overallScore: 70,
    reviewStatus: "complete",
    automated: {
      total: 52,
      security: { score: 18, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 11, max: 17, label: "Tokenomics & Utility" },
      community: { score: 10, max: 13, label: "Community & Dev Activity" },
      market: { score: 12, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 1, max: 2, label: "Public Discourse Signal" },
    },
    manual: {
      total: 18,
      team: { score: 7, max: 9, label: "Team & Identity" },
      vision: { score: 5, max: 7, label: "Vision & Clarity" },
      transparency: { score: 3, max: 5, label: "Transparency" },
      execution: { score: 3, max: 4, label: "Execution Reality" },
    },
  },
  {
    id: "chainlink",
    name: "Chainlink",
    ticker: "LINK",
    overallScore: 55,
    reviewStatus: "pending",
    automated: {
      total: 55,
      security: { score: 20, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 10, max: 17, label: "Tokenomics & Utility" },
      community: { score: 9, max: 13, label: "Community & Dev Activity" },
      market: { score: 14, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 2, max: 2, label: "Public Discourse Signal" },
    },
    manual: null,
  },
  {
    id: "avalanche",
    name: "Avalanche",
    ticker: "AVAX",
    overallScore: 64,
    reviewStatus: "complete",
    automated: {
      total: 48,
      security: { score: 17, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 10, max: 17, label: "Tokenomics & Utility" },
      community: { score: 8, max: 13, label: "Community & Dev Activity" },
      market: { score: 11, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 2, max: 2, label: "Public Discourse Signal" },
    },
    manual: {
      total: 16,
      team: { score: 6, max: 9, label: "Team & Identity" },
      vision: { score: 4, max: 7, label: "Vision & Clarity" },
      transparency: { score: 3, max: 5, label: "Transparency" },
      execution: { score: 3, max: 4, label: "Execution Reality" },
    },
  },
  {
    id: "polkadot",
    name: "Polkadot",
    ticker: "DOT",
    overallScore: 58,
    reviewStatus: "pending",
    automated: {
      total: 58,
      security: { score: 21, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 12, max: 17, label: "Tokenomics & Utility" },
      community: { score: 11, max: 13, label: "Community & Dev Activity" },
      market: { score: 12, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 2, max: 2, label: "Public Discourse Signal" },
    },
    manual: null,
  },
  {
    id: "polygon",
    name: "Polygon",
    ticker: "MATIC",
    overallScore: 67,
    reviewStatus: "complete",
    automated: {
      total: 50,
      security: { score: 19, max: 28, label: "Security & Transparency" },
      tokenomics: { score: 11, max: 17, label: "Tokenomics & Utility" },
      community: { score: 9, max: 13, label: "Community & Dev Activity" },
      market: { score: 10, max: 15, label: "Market Data & Liquidity" },
      discourse: { score: 1, max: 2, label: "Public Discourse Signal" },
    },
    manual: {
      total: 17,
      team: { score: 7, max: 9, label: "Team & Identity" },
      vision: { score: 5, max: 7, label: "Vision & Clarity" },
      transparency: { score: 3, max: 5, label: "Transparency" },
      execution: { score: 2, max: 4, label: "Execution Reality" },
    },
  },
];

// Watchlist for dashboard — mock user preference
export const MOCK_WATCHLIST = ["bitcoin", "ethereum", "solana", "cardano"];

// Helper
export function getToken(id) {
  return MOCK_TOKENS.find((t) => t.id === id) || null;
}

export function getScoreColor(score) {
  if (score >= 75) return "score-excellent";
  if (score >= 55) return "score-good";
  if (score >= 35) return "score-fair";
  return "score-poor";
}

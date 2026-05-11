import "./About.css"

const AUTO_CATEGORIES = [
  { label: "Security & Transparency", max: 28, desc: "Smart-contract audits, on-chain transparency, open-source code availability, and known vulnerability history." },
  { label: "Tokenomics & Utility", max: 17, desc: "Token supply mechanics, vesting schedules, burn mechanisms, and real-world utility of the token within its ecosystem." },
  { label: "Community & Dev Activity", max: 13, desc: "GitHub commit frequency, contributor count, community growth trends, and developer engagement signals." },
  { label: "Market Data & Liquidity", max: 15, desc: "Market capitalisation, 24h trading volume, exchange listings, and order book depth." },
  { label: "Public Discourse Signal", max: 2, desc: "Sentiment analysis across curated sources — weighted low intentionally to avoid hype-driven distortion." },
]

const MANUAL_CATEGORIES = [
  { label: "Team & Identity", max: 9, desc: "Are the founders and core team publicly identifiable? Do they have relevant track records?" },
  { label: "Vision & Clarity", max: 7, desc: "Is there a clear, realistic roadmap? Does the whitepaper articulate a genuine problem and solution?" },
  { label: "Transparency", max: 5, desc: "Is the project forthcoming about risks, unlocks, and governance? Are communications honest and frequent?" },
  { label: "Execution Reality", max: 4, desc: "Has the project shipped what it promised? Are milestones being met on schedule?" },
]

function About() {
  return (
    <div className="page-wrap about-page">
      {/* Hero */}
      <section className="about-hero fade-in fade-in-1">
        <h1>CCS Methodology</h1>
        <p className="about-lead">
          Every CCS score is built from two pillars: 75 points of algorithmic data and 25 points
          of trained human review. This hybrid approach ensures that raw data is contextualised
          by experienced Crypto Currency Solutions analysts who can catch what algorithms miss.
        </p>
      </section>

      {/* Split explanation */}
      <section className="split-section fade-in fade-in-2">
        <div className="split-card">
          <span className="split-number">75</span>
          <h3>Algorithmic Data</h3>
          <p>
            Five categories of on-chain, market, and community data are pulled automatically,
            scored against benchmarks, and weighted by importance.
          </p>
        </div>
        <div className="split-plus">+</div>
        <div className="split-card">
          <span className="split-number">25</span>
          <h3>Human Review</h3>
          <p>
            A CCS analyst evaluates team credibility, vision clarity, transparency, and execution.
            This review is the differentiator that separates signals from noise.
          </p>
        </div>
        <div className="split-equals">=</div>
        <div className="split-card split-total">
          <span className="split-number">100</span>
          <h3>CCS Total Score</h3>
        </div>
      </section>

      {/* Automated categories */}
      <section className="categories-section fade-in fade-in-3">
        <h2>Section A — Automated Data Score (75 pts)</h2>
        <div className="cat-grid">
          {AUTO_CATEGORIES.map((cat) => (
            <div className="cat-card" key={cat.label}>
              <div className="cat-head">
                <span className="cat-label">{cat.label}</span>
                <span className="cat-max">/ {cat.max}</span>
              </div>
              <p className="cat-desc">{cat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Manual categories */}
      <section className="categories-section fade-in fade-in-5">
        <h2>Section B — Manual Human Review (25 pts)</h2>
        <div className="cat-grid">
          {MANUAL_CATEGORIES.map((cat) => (
            <div className="cat-card" key={cat.label}>
              <div className="cat-head">
                <span className="cat-label">{cat.label}</span>
                <span className="cat-max">/ {cat.max}</span>
              </div>
              <p className="cat-desc">{cat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pending disclaimer */}
      <section className="pending-note fade-in fade-in-7">
        <h2>What Does "Pending Review" Mean?</h2>
        <p>
          When a token shows "Manual review not yet completed," it simply means our analyst team
          hasn't finished their evaluation yet. It is <strong>not</strong> a negative signal.
          The automated data score is still fully available and accurate. Once the human review
          is complete, the full 100-point score will be published.
        </p>
      </section>

      {/* Disclaimer */}
      <section className="disclaimer fade-in fade-in-8">
        <p>
          CCS scores are for informational purposes only and do not constitute financial advice.
          Cryptocurrency investments carry significant risk. Always do your own research.
        </p>
      </section>
    </div>
  )
}

export default About

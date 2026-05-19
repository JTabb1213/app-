"""
Collectors package
==================
Each sub-package is a self-contained collector with a pluggable source layer.

Usage:
    from collectors.decentralization_risk import base as decentral_collector
    from collectors.github                import fetch as fetch_github
    from collectors.tokenomics            import fetch as fetch_tokenomics
    from collectors.public_discourse      import fetch as fetch_discourse
"""

from .decentralization_risk import base as fetch_decentralization
from .github                import fetch as fetch_github
from .tokenomics            import fetch as fetch_tokenomics
from .public_discourse      import fetch as fetch_discourse

# Legacy alias — kept so any existing code using fetch_holders still works
fetch_holders = fetch_decentralization.fetch

__all__ = [
    "fetch_decentralization",
    "fetch_holders",       # deprecated alias
    "fetch_github",
    "fetch_tokenomics",
    "fetch_discourse",
]

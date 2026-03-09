"""Medical Source Validation Service - validates credibility of medical sources."""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

TRUSTED_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov", "who.int", "cdc.gov", "mayoclinic.org",
    "medlineplus.gov", "nih.gov", "bmj.com", "nejm.org", "thelancet.com",
    "jamanetwork.com", "nature.com", "science.org", "uptodate.com"
]
UNTRUSTED_DOMAINS = ["wikipedia.org", "reddit.com", "quora.com", "yahoo.com"]

class MedicalSourceValidationService:
    def __init__(self):
        pass

    async def startup(self):
        logger.info("Medical Source Validation Service ready.")

    async def shutdown(self):
        pass

    def _extract_domain(self, url: str) -> str:
        match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', url)
        return match.group(1).lower() if match else ""

    def _validate_source(self, source: str) -> dict:
        domain = self._extract_domain(source)
        is_trusted = any(trusted in domain for trusted in TRUSTED_DOMAINS)
        is_untrusted = any(untrusted in domain for untrusted in UNTRUSTED_DOMAINS)
        if is_trusted:
            credibility = "high"
            score = 0.95
        elif is_untrusted:
            credibility = "low"
            score = 0.20
        else:
            credibility = "unknown"
            score = 0.50
        return {"source": source, "domain": domain, "credibility": credibility, "score": score, "is_valid": score >= 0.5}

    async def validate(self, source: str, claim: Optional[str] = None) -> dict:
        result = self._validate_source(source)
        result["claim"] = claim
        return result

    async def batch_validate(self, sources: List[str]) -> dict:
        results = [self._validate_source(s) for s in sources]
        valid = sum(1 for r in results if r["is_valid"])
        return {"results": results, "total": len(results), "valid": valid, "invalid": len(results) - valid}

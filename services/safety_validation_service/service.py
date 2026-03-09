import re
import logging
from typing import Optional, List

logger = logging.getLogger("safety_validation_service")

# Disclaimer phrases that indicate proper medical caveats
DISCLAIMER_PATTERNS = [
    r"consult\s+(a\s+)?(doctor|physician|healthcare\s+provider|medical\s+professional)",
    r"seek\s+(medical|professional|emergency)\s+(help|attention|care|advice)",
    r"this\s+is\s+not\s+(medical|professional)\s+advice",
    r"not\s+a\s+substitute\s+for\s+(professional\s+)?medical",
    r"speak\s+(with|to)\s+(a\s+)?(doctor|physician|healthcare)",
    r"call\s+(your\s+doctor|911|emergency\s+services|a\s+healthcare)",
    r"professional\s+medical\s+advice",
    r"medical\s+emergency",
]
DISCLAIMER_RE = re.compile("|".join(DISCLAIMER_PATTERNS), re.IGNORECASE)

# Emergency keywords that signal a crisis situation
EMERGENCY_KEYWORDS = {
    "cardiac arrest", "heart attack", "stroke", "chest pain", "not breathing",
    "unconscious", "unresponsive", "choking", "anaphylaxis", "anaphylactic",
    "severe bleeding", "hemorrhage", "seizure", "overdose", "poisoning",
    "difficulty breathing", "shortness of breath", "loss of consciousness",
    "suicidal", "suicide", "self-harm", "severe head injury",
}

# Emergency response indicators
EMERGENCY_RESPONSE_PATTERNS = [
    r"call\s+911",
    r"call\s+emergency",
    r"go\s+to\s+(the\s+)?emergency",
    r"emergency\s+(room|department|services)",
    r"er\s+immediately",
    r"seek\s+immediate\s+(medical|emergency)",
    r"call\s+an\s+ambulance",
    r"emergency\s+assistance",
]
EMERGENCY_RESPONSE_RE = re.compile("|".join(EMERGENCY_RESPONSE_PATTERNS), re.IGNORECASE)

# Dangerous advice patterns (specific dosages without qualification)
DANGEROUS_PATTERNS = [
    r"take\s+\d+\s*(mg|ml|tablets?|pills?|capsules?)\s+every\s+\d+\s*hours?",  # unqualified dosing
    r"double\s+the\s+dose",
    r"take\s+more\s+than\s+prescribed",
    r"ignore\s+(your\s+)?(doctor|physician|prescription)",
    r"stop\s+(taking|your)\s+medication\s+immediately\s+without",
    r"you\s+don[''t]+\s+need\s+(a\s+)?doctor",
    r"home\s+remedy\s+(will|can)\s+cure",
    r"definitely\s+(have|has|is)\s+(cancer|tumor|disease)",  # definitive non-professional diagnosis
]
DANGEROUS_RE = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)

# Dangerous but acceptable when sourced
SOURCE_MITIGATED_PATTERN = re.compile(
    r"(according\s+to|based\s+on|as\s+per|studies?\s+show|guidelines?\s+recommend|source[sd]?)",
    re.IGNORECASE,
)

# PII patterns
PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",                                       # SSN
    r"\b\d{16}\b",                                                    # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",        # Email
    r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",     # Phone
    r"\b\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|blvd|lane|ln|drive|dr)\b",  # Street addr
    r"\bDOB\s*:?\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",               # Date of birth label
    r"\bMRN\s*:?\s*\d+\b",                                           # Medical record number
]
PII_RE = re.compile("|".join(PII_PATTERNS), re.IGNORECASE)


def _check_disclaimer(response: str) -> bool:
    return bool(DISCLAIMER_RE.search(response))


def _check_emergency_handled(query: str, response: str, triage_level: str) -> bool:
    """If the query/triage level signals emergency, check the response directs to emergency care."""
    is_emergency_query = any(kw in query.lower() for kw in EMERGENCY_KEYWORDS)
    is_emergency_triage = triage_level.upper() == "EMERGENCY"

    if not (is_emergency_query or is_emergency_triage):
        return True  # No emergency — check passes trivially

    return bool(EMERGENCY_RESPONSE_RE.search(response))


def _check_no_dangerous_advice(response: str) -> tuple[bool, List[str]]:
    """
    Returns (is_safe, list_of_flagged_snippets).
    Dangerous patterns are acceptable when the response cites a source.
    """
    flagged: List[str] = []
    for match in DANGEROUS_RE.finditer(response):
        snippet = match.group(0)
        # Check context ±150 chars around the match for a source citation
        start = max(0, match.start() - 150)
        end = min(len(response), match.end() + 150)
        context = response[start:end]
        if not SOURCE_MITIGATED_PATTERN.search(context):
            flagged.append(snippet)
    return len(flagged) == 0, flagged


def _check_pii_free(response: str) -> tuple[bool, List[str]]:
    """Returns (is_clean, list_of_pii_types_found)."""
    matches = PII_RE.findall(response)
    return len(matches) == 0, matches


class SafetyValidationService:
    def validate(
        self,
        response: str,
        query: str = "",
        triage_level: str = "NON_URGENT",
        conversation_id: Optional[str] = None,
    ) -> dict:
        """Run all safety checks on a medical response."""
        disclaimer_present = _check_disclaimer(response)
        emergency_handled = _check_emergency_handled(query, response, triage_level)
        no_dangerous_advice, flagged_advice = _check_no_dangerous_advice(response)
        pii_free, pii_found = _check_pii_free(response)

        checks = {
            "disclaimer_present": disclaimer_present,
            "emergency_handled": emergency_handled,
            "no_dangerous_advice": no_dangerous_advice,
            "pii_free": pii_free,
        }

        # Weighted scoring
        weights = {
            "disclaimer_present": 0.20,
            "emergency_handled": 0.35,
            "no_dangerous_advice": 0.30,
            "pii_free": 0.15,
        }
        overall_score = sum(weights[k] * (1.0 if v else 0.0) for k, v in checks.items())

        issues: List[str] = []
        if not disclaimer_present:
            issues.append("Missing medical disclaimer / recommendation to consult a professional")
        if not emergency_handled:
            issues.append("Emergency situation detected but response does not direct to emergency care")
        if not no_dangerous_advice:
            issues.append(f"Potentially dangerous advice detected: {flagged_advice}")
        if not pii_free:
            issues.append(f"PII detected in response: {pii_found}")

        logger.info(
            "Safety validation — conv=%s triage=%s score=%.3f checks=%s",
            conversation_id, triage_level, overall_score, checks,
        )

        return {
            "conversation_id": conversation_id,
            "overall_score": round(overall_score, 4),
            "checks": checks,
            "issues": issues,
            "flagged_advice": flagged_advice,
            "pii_found": pii_found,
            "is_safe": overall_score >= 0.7,
        }

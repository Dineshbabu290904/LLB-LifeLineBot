import re
from typing import List, Tuple, Optional
from enum import Enum

MEDICAL_DISCLAIMER = (
    "\n\n⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
    "and does not constitute medical advice. Always consult a qualified healthcare "
    "professional for medical decisions. In case of emergency, call emergency services immediately."
)

EMERGENCY_DISCLAIMER = (
    "\n\n🚨 EMERGENCY ALERT: Based on the symptoms described, this may be a medical emergency. "
    "Please call 911 (or your local emergency number) immediately or go to the nearest emergency room. "
    "Do not delay seeking emergency medical care."
)

TRUSTED_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov",
    "who.int",
    "cdc.gov",
    "mayoclinic.org",
    "medlineplus.gov",
    "nih.gov",
    "uptodate.com",
    "nejm.org",
    "thelancet.com",
    "bmj.com",
    "jamanetwork.com",
    "medscape.com",
    "webmd.com",
    "healthline.com",
    "clevelandclinic.org",
    "hopkinsmedicine.org",
    "mountsinai.org",
    "drugs.com",
    "rxlist.com",
]

# Emergency keyword patterns (symptom combinations that indicate emergencies)
EMERGENCY_KEYWORDS = [
    # Cardiac emergencies
    r"chest pain.*(shortness of breath|sweating|arm pain|jaw pain)",
    r"(shortness of breath|difficulty breathing).*(chest pain|crushing)",
    r"heart attack",
    r"cardiac arrest",
    r"(severe|crushing) chest (pain|pressure)",
    # Stroke (FAST)
    r"(face drooping|arm weakness|speech difficulty).*(sudden)",
    r"sudden (numbness|weakness).*(face|arm|leg)",
    r"sudden (severe|worst) headache",
    r"stroke",
    r"sudden (confusion|trouble speaking|trouble understanding)",
    r"sudden (trouble seeing|vision loss)",
    # Breathing emergencies
    r"(cannot breathe|can't breathe|not breathing)",
    r"choking",
    r"anaphylaxis",
    r"severe allergic reaction",
    # Bleeding emergencies
    r"severe bleeding",
    r"uncontrolled bleeding",
    r"coughing (up|out) blood",
    r"vomiting blood",
    # Neurological
    r"(unconscious|unresponsive)",
    r"(seizure|convulsion).*(prolonged|ongoing|not stopping)",
    r"loss of consciousness",
    # Mental health crisis
    r"suicidal",
    r"suicide",
    r"self.harm",
    r"want to (die|kill myself)",
    # Poisoning/Overdose
    r"overdose",
    r"poisoning",
    r"swallowed.*(medication|pill|chemical)",
    # Trauma
    r"(severe|serious) accident",
    r"head (injury|trauma).*(unconscious|loss of consciousness)",
    r"spinal injury",
]

# Compile patterns once for efficiency
EMERGENCY_PATTERNS = [re.compile(p, re.IGNORECASE) for p in EMERGENCY_KEYWORDS]

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore (previous|all|above) (instructions?|prompt)",
    r"forget (everything|all) (you|previously)",
    r"you are now",
    r"jailbreak",
    r"DAN mode",
    r"pretend (you are|to be) (not|an?)",
    r"system prompt",
    r"<\|.*\|>",  # Special tokens
]

INJECTION_COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


class SafetyCheckResult:
    def __init__(
        self,
        is_safe: bool,
        is_emergency: bool = False,
        violations: List[str] = None,
        recommendation: str = "",
    ):
        self.is_safe = is_safe
        self.is_emergency = is_emergency
        self.violations = violations or []
        self.recommendation = recommendation


class MedicalSafety:
    @staticmethod
    def check_input(text: str) -> SafetyCheckResult:
        """Check if user input is safe to process."""
        violations = []

        # Check for prompt injection
        for pattern in INJECTION_COMPILED:
            if pattern.search(text):
                violations.append(f"Prompt injection detected: {pattern.pattern[:50]}")

        is_emergency = MedicalSafety.is_emergency(text)
        is_safe = len(violations) == 0

        return SafetyCheckResult(
            is_safe=is_safe,
            is_emergency=is_emergency,
            violations=violations,
        )

    @staticmethod
    def is_emergency(text: str) -> bool:
        """Check if text contains emergency symptoms."""
        for pattern in EMERGENCY_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @staticmethod
    def inject_disclaimer(response: str, is_emergency: bool = False) -> str:
        """Inject appropriate medical disclaimer into response."""
        if is_emergency:
            return response + EMERGENCY_DISCLAIMER
        return response + MEDICAL_DISCLAIMER

    @staticmethod
    def validate_source(url: str) -> bool:
        """Check if a URL is from a trusted medical domain."""
        url_lower = url.lower()
        return any(domain in url_lower for domain in TRUSTED_DOMAINS)

    @staticmethod
    def check_output(response: str) -> SafetyCheckResult:
        """Check if the generated response is safe to return."""
        violations = []

        # Must include disclaimer
        has_disclaimer = "disclaimer" in response.lower() or "consult" in response.lower()
        if not has_disclaimer:
            violations.append("Response missing medical disclaimer")

        # Check for dangerous dosage claims without sources
        dosage_pattern = re.compile(
            r"\b\d+\s*(mg|ml|mcg|units?)\b.*\b(take|give|administer|dose)\b",
            re.IGNORECASE
        )
        if dosage_pattern.search(response):
            if "[source]" not in response.lower() and "according to" not in response.lower():
                violations.append("Specific medication dosage mentioned without citation")

        is_safe = len(violations) == 0
        return SafetyCheckResult(is_safe=is_safe, violations=violations)

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """Remove or mask PII from text."""
        # Mask email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Mask SSN patterns
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
        return text

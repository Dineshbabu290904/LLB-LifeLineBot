"""Safety Guardrail Agent - applies safety guardrails to LLM inputs/outputs."""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

UNSAFE_INPUT_PATTERNS = [
    r"how to (make|create|synthesize) (drugs|poison|weapon)",
    r"how to (kill|harm|hurt) (myself|someone|people)",
    r"give me (illegal|controlled) (substances|drugs)",
]

UNSAFE_OUTPUT_PATTERNS = [
    r"you should (stop taking|ignore) your (medication|prescription|doctor)",
    r"(definitely|certainly) have (cancer|tumor|disease)",
    r"do not (call|see|consult) (a doctor|physician|emergency)",
]

REQUIRED_DISCLAIMERS = [
    "This is not medical advice",
    "consult a healthcare professional",
    "seek medical attention",
]

class SafetyGuardrailAgent:
    def __init__(self):
        self._input_patterns = [re.compile(p, re.IGNORECASE) for p in UNSAFE_INPUT_PATTERNS]
        self._output_patterns = [re.compile(p, re.IGNORECASE) for p in UNSAFE_OUTPUT_PATTERNS]

    async def startup(self):
        logger.info("Safety Guardrail Agent ready.")

    async def shutdown(self):
        pass

    async def check_input(self, text: str, user_id: Optional[str] = None) -> dict:
        violations = [p.pattern for p in self._input_patterns if p.search(text)]
        is_safe = len(violations) == 0
        return {
            "text": text,
            "is_safe": is_safe,
            "violations": violations,
            "action": "allow" if is_safe else "block",
            "user_id": user_id,
        }

    async def check_output(self, text: str) -> dict:
        violations = [p.pattern for p in self._output_patterns if p.search(text)]
        needs_disclaimer = not any(d.lower() in text.lower() for d in REQUIRED_DISCLAIMERS)
        is_safe = len(violations) == 0
        return {
            "is_safe": is_safe,
            "violations": violations,
            "needs_disclaimer": needs_disclaimer,
            "action": "allow" if is_safe else "flag",
        }

    async def filter(self, text: str, add_disclaimer: bool = True) -> dict:
        output_check = await self.check_output(text)
        filtered = text
        if output_check["needs_disclaimer"] and add_disclaimer:
            filtered += "\n\n*Note: This is for informational purposes only and is not a substitute for professional medical advice. Please consult a qualified healthcare provider.*"
        return {
            "original_text": text,
            "filtered_text": filtered,
            "was_modified": filtered != text,
            "safety_check": output_check,
        }

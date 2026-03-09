"""Context Builder Service - builds conversation context from history and knowledge."""
import logging
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    max_tokens_default: int = 4000
    class Config:
        env_prefix = "CONTEXT_BUILDER_"

settings = Settings()

def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

class ContextBuilderService:
    async def startup(self):
        logger.info("ContextBuilderService started")

    async def shutdown(self):
        pass

    def build_context(
        self,
        conversation_history: List[Dict[str, Any]],
        retrieved_knowledge: List[str],
        system_prompt: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        parts = []
        if system_prompt:
            parts.append({"role": "system", "content": system_prompt})

        knowledge_text = "\n\n".join(retrieved_knowledge)
        if knowledge_text:
            parts.append({"role": "system", "content": f"Relevant medical knowledge:\n{knowledge_text}"})

        for msg in conversation_history:
            parts.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        total_tokens = sum(_estimate_tokens(p["content"]) for p in parts)
        return {
            "context": parts,
            "total_tokens": total_tokens,
            "knowledge_snippets": len(retrieved_knowledge),
            "history_turns": len(conversation_history),
            "truncated": total_tokens > max_tokens,
        }

    def truncate_context(
        self,
        context: List[Dict[str, Any]],
        max_tokens: int,
    ) -> Dict[str, Any]:
        truncated = []
        token_count = 0
        system_msgs = [m for m in context if m.get("role") == "system"]
        non_system = [m for m in context if m.get("role") != "system"]

        for msg in system_msgs:
            tokens = _estimate_tokens(msg["content"])
            token_count += tokens
            truncated.append(msg)

        for msg in reversed(non_system):
            tokens = _estimate_tokens(msg["content"])
            if token_count + tokens <= max_tokens:
                truncated.insert(len(system_msgs), msg)
                token_count += tokens
            else:
                break

        return {
            "context": truncated,
            "total_tokens": token_count,
            "original_count": len(context),
            "truncated_count": len(truncated),
        }

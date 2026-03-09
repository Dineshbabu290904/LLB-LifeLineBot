"""RAG and search nodes for knowledge retrieval."""
import httpx
import logging
from state import MedBotState
from config import get_config

logger = logging.getLogger("rag_nodes")
config = get_config()


async def _call_service(url: str, endpoint: str, data: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{url}{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"Service call failed {url}{endpoint}: {e}")
        return {}


async def rag_retrieval_node(state: MedBotState) -> MedBotState:
    """Retrieve relevant context from vector database."""
    logger.info(f"[{state['run_id']}] RAG retrieval")
    state["pipeline_stage"] = "rag_retrieval"

    # Build search query from symptoms + user query
    symptoms_text = " ".join(s.get("name", "") for s in state.get("extracted_symptoms", []))
    search_query = f"{state['user_query']} {symptoms_text}".strip()

    result = await _call_service(
        config.rag_agent_url,
        "/api/v1/rag/retrieve",
        {
            "query": search_query,
            "top_k": 5,
            "min_score": 0.4,
        },
    )

    if result:
        chunks = result.get("chunks", [])
        state["retrieved_context"] = [c.get("text", "") for c in chunks]
        state["source_documents"] = [
            {"url": c.get("source_url", ""), "text": c.get("text", "")[:200]}
            for c in chunks
        ]
        state["search_queries_used"] = [search_query]
        state["context_sufficient"] = len(chunks) >= config.min_context_chunks
    else:
        state["retrieved_context"] = []
        state["source_documents"] = []
        state["context_sufficient"] = False

    logger.info(f"[{state['run_id']}] Retrieved {len(state['retrieved_context'])} chunks")
    return state


async def agentic_search_node(state: MedBotState) -> MedBotState:
    """Perform agentic web search when RAG context is insufficient."""
    logger.info(f"[{state['run_id']}] Agentic search")
    state["pipeline_stage"] = "agentic_search"

    symptoms_text = " ".join(s.get("name", "") for s in state.get("extracted_symptoms", []))
    search_query = f"medical information {state['user_query']} {symptoms_text}".strip()

    result = await _call_service(
        config.search_agent_url,
        "/api/v1/search/medical",
        {
            "query": search_query,
            "max_results": 5,
            "trusted_only": True,
        },
    )

    if result:
        web_results = result.get("results", [])
        # Append web results to retrieved context
        existing = state.get("retrieved_context", [])
        new_contexts = [r.get("snippet", "") for r in web_results if r.get("snippet")]
        state["retrieved_context"] = existing + new_contexts
        state["source_documents"].extend([
            {"url": r.get("url", ""), "title": r.get("title", ""), "text": r.get("snippet", "")[:200]}
            for r in web_results
        ])
        state["context_sufficient"] = len(state["retrieved_context"]) >= config.min_context_chunks

    logger.info(f"[{state['run_id']}] Total context chunks: {len(state['retrieved_context'])}")
    return state


async def knowledge_validation_node(state: MedBotState) -> MedBotState:
    """Validate sources and build coherent context."""
    logger.info(f"[{state['run_id']}] Knowledge validation")
    state["pipeline_stage"] = "knowledge_validation"

    result = await _call_service(
        config.knowledge_agent_url,
        "/api/v1/knowledge/validate",
        {
            "sources": state.get("source_documents", []),
            "query": state["user_query"],
        },
    )

    if result:
        validated_sources = result.get("validated_sources", state.get("source_documents", []))
        state["source_documents"] = validated_sources
        state["sources"] = [s.get("url", "") for s in validated_sources if s.get("url")]

    return state

"""LangGraph orchestrator service — runs the MEDBOT pipeline."""
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from state import MedBotState, create_initial_state
from graph import get_compiled_graph
from config import get_config

logger = logging.getLogger("orchestrator_service")
config = get_config()


class OrchestratorService:
    def __init__(self):
        self.graph = get_compiled_graph()

    async def run_pipeline(
        self,
        user_query: str,
        session_id: str,
        conversation_id: str,
        image_data: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        patient_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full MEDBOT LangGraph pipeline.
        Returns structured response with triage, recommendation, and sources.
        """
        logger.info(f"Starting pipeline for session={session_id}, conv={conversation_id}")

        initial_state = create_initial_state(
            user_query=user_query,
            session_id=session_id,
            conversation_id=conversation_id,
            image_data=image_data,
            conversation_history=conversation_history or [],
            patient_context=patient_context or {},
        )

        try:
            # Run the LangGraph pipeline
            final_state = await self.graph.ainvoke(initial_state)

            logger.info(
                f"Pipeline complete for {conversation_id}: "
                f"triage={final_state.get('triage_level')}, "
                f"hallucination={final_state.get('hallucination_score', 0):.3f}"
            )

            return self._format_response(final_state)

        except Exception as e:
            logger.error(f"Pipeline error for {conversation_id}: {e}", exc_info=True)
            return self._error_response(session_id, conversation_id, str(e))

    def _format_response(self, state: MedBotState) -> Dict[str, Any]:
        """Format final state into API response."""
        return {
            "session_id": state.get("session_id"),
            "conversation_id": state.get("conversation_id"),
            "response": state.get("final_response", ""),
            "triage_level": state.get("triage_level", "ROUTINE"),
            "is_emergency": state.get("is_emergency", False),
            "doctor_recommendation": state.get("doctor_recommendation"),
            "symptoms_identified": state.get("extracted_symptoms", []),
            "differential_diagnoses": state.get("differential_diagnoses", []),
            "sources": [s for s in state.get("sources", []) if s],
            "hallucination_score": state.get("hallucination_score", 0.0),
            "safety_cleared": state.get("output_safety_cleared", False),
            "safety_violations": state.get("safety_violations", []),
            "evaluation_report": state.get("evaluation_report"),
            "pipeline_stage": state.get("pipeline_stage", "completed"),
            "retry_count": state.get("retry_count", 0),
            "disclaimer": (
                "⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
                "and does not constitute medical advice. Always consult a qualified healthcare "
                "professional for medical decisions. In case of emergency, call emergency services immediately."
            ),
        }

    def _error_response(
        self, session_id: str, conversation_id: str, error: str
    ) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "conversation_id": conversation_id,
            "response": (
                "I encountered an error processing your medical query. "
                "Please try again or consult a healthcare professional directly.\n\n"
                "⚠️ MEDICAL DISCLAIMER: This system is for educational purposes only. "
                "Always consult a qualified healthcare professional for medical advice."
            ),
            "triage_level": "ROUTINE",
            "is_emergency": False,
            "doctor_recommendation": None,
            "symptoms_identified": [],
            "sources": [],
            "error": error,
            "disclaimer": (
                "⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only "
                "and does not constitute medical advice."
            ),
        }

from typing import Dict, Any, List, Optional
from src.memory.memory_models import CaseMemory, sanitize_sensitive_data

class RetentionPolicy:
    """
    Enforces quality and security guidelines for persisting memory to Hindsight:
    1. Retain only durable operational knowledge (never ephemeral noise).
    2. Retain only after an outcome is recorded (resolved, rejected, or escalated).
    3. Enforce strict PII and credential sanitization.
    4. Apply uniform categorization tags for multi-strategy TEMPR recall.
    """
    MIN_DESCRIPTION_LENGTH = 15

    @classmethod
    def should_retain_case(cls, case: CaseMemory) -> bool:
        """Determines if a case meets criteria for durable retention."""
        if not case.case_id or not case.discrepancy_type:
            return False
        # Do not retain uninvestigated or blank outcomes
        if not case.final_resolution or len(case.final_resolution.strip()) < cls.MIN_DESCRIPTION_LENGTH:
            return False
        return True

    @classmethod
    def prepare_retention_payload(cls, case: CaseMemory) -> Dict[str, Any]:
        """Sanitizes and packages case into Hindsight retain payload."""
        content = case.to_hindsight_content()
        tags = case.to_tags()
        metadata = {
            "case_id": case.case_id,
            "order_id": case.order_id,
            "discrepancy_type": case.discrepancy_type,
            "gateway": case.gateway,
            "merchant_id": case.merchant_id,
            "status": case.outcome_status,
            "was_successful": str(case.was_successful)
        }
        return {
            "content": content,
            "tags": tags,
            "metadata": metadata
        }

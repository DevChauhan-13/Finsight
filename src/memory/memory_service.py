import logging
from typing import Dict, Any, List, Optional
from src.memory.hindsight_client import FinSightHindsightWrapper
from src.memory.memory_models import CaseMemory, MerchantMemory, GatewayMemory
from src.memory.retention_policy import RetentionPolicy
from src.memory.memory_queries import (
    build_recall_query_for_discrepancy,
    build_reflection_query_for_discrepancy,
    build_merchant_query,
    build_gateway_query
)
from src.memory.memory_formatter import MemoryFormatter

logger = logging.getLogger(__name__)

class FinSightMemoryService:
    """
    High-level facade orchestrating Hindsight memory operations for the
    FinSight financial reconciliation pipeline.
    """
    def __init__(self, hindsight_client: Optional[FinSightHindsightWrapper] = None):
        self.client = hindsight_client or FinSightHindsightWrapper()
        self.formatter = MemoryFormatter()

    @property
    def is_online(self) -> bool:
        return self.client.is_connected

    def retain_case_experience(self, case: CaseMemory) -> Dict[str, Any]:
        """
        Validates, prepares, and retains a resolved case experience into Hindsight.
        """
        if not RetentionPolicy.should_retain_case(case):
            logger.info(f"Case {case.case_id} does not meet retention criteria; skipping.")
            return {"status": "skipped", "reason": "does not meet retention criteria"}

        payload = RetentionPolicy.prepare_retention_payload(case)
        result = self.client.retain(
            content=payload["content"],
            tags=payload["tags"],
            metadata=payload["metadata"]
        )
        logger.info(f"Retained case experience {case.case_id} into Hindsight. Source: {result.get('source')}")
        return result

    def recall_similar_exceptions(
        self,
        discrepancy_type: str,
        gateway: str = "Razorpay",
        merchant_name: str = "Apex Retail",
        failure_cause: str = "",
        net_variance: float = 0.0,
        max_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant historical experiences from Hindsight for a given discrepancy.
        """
        query = build_recall_query_for_discrepancy(
            discrepancy_type=discrepancy_type,
            gateway=gateway,
            merchant_name=merchant_name,
            failure_cause=failure_cause,
            net_variance=net_variance
        )
        tags = [f"discrepancy:{discrepancy_type.lower()}", f"gateway:{gateway.lower()}"]
        memories = self.client.recall(query=query, tags=tags, max_tokens=max_tokens)
        return memories

    def reflect_on_resolution_patterns(
        self,
        discrepancy_type: str,
        gateway: str = "Razorpay",
        merchant_name: str = "Apex Retail"
    ) -> str:
        """
        Performs Hindsight reflection across historical memories to synthesize
        recurring root causes and optimal dispute practices.
        """
        query = build_reflection_query_for_discrepancy(
            discrepancy_type=discrepancy_type,
            gateway=gateway,
            merchant_name=merchant_name
        )
        return self.client.reflect(query=query)

    def retain_merchant_knowledge(self, merchant: MerchantMemory) -> Dict[str, Any]:
        """Persists durable merchant contract & profile knowledge."""
        content = merchant.to_hindsight_content()
        tags = [f"merchant:{merchant.merchant_id.lower()}", "profile:merchant"]
        return self.client.retain(content=content, tags=tags)

    def retain_gateway_knowledge(self, gateway: GatewayMemory) -> Dict[str, Any]:
        """Persists durable gateway profile & SLA knowledge."""
        content = gateway.to_hindsight_content()
        tags = [f"gateway:{gateway.gateway_name.lower()}", "profile:gateway"]
        return self.client.retain(content=content, tags=tags)

    def clear_all_memories(self):
        """Clears memories for reproducible demo and testing purposes."""
        self.client.clear_bank()

    def total_memories(self) -> int:
        """Return total count of memories stored across all banks.

        Uses the local fallback store to compute the count. If the official
        Hindsight client is online, its banks are mirrored in the local store,
        ensuring the count reflects all retained memories.
        """
        # Access the internal local store dictionary which maps bank_id to a list of memory records.
        try:
            banks = getattr(self.client, "local_store", None)
            if banks is None:
                return 0
            # banks is a LocalFallbackMemoryStore instance with a .banks attribute.
            bank_dict = getattr(banks, "banks", {})
            return sum(len(mem_list) for mem_list in bank_dict.values())
        except Exception:
            # In case of unexpected structure, fail gracefully.
            return 0

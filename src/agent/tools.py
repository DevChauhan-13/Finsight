from typing import Dict, Any, List, Optional
from src.memory.memory_service import FinSightMemoryService
from src.memory.memory_models import CaseMemory, MerchantMemory, GatewayMemory
from src.agent.schemas import AgentCaseAnalysis, OperatorOutcomeInput, CaseLifecycleState

class ReconciliationAgentTools:
    """
    Explicit toolset callable by the Financial Reconciliation Agent.
    Implements tool calling boundaries:
    - Queries deterministic results
    - Interacts with Hindsight (recall, reflect, retain)
    - Records human operator resolutions
    - NEVER directly alters financial truth
    """
    def __init__(self, memory_service: Optional[FinSightMemoryService] = None):
        self.memory_service = memory_service or FinSightMemoryService()

    def get_discrepancy_details(self, case_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Inspects the exact deterministic math findings for an exception."""
        return {
            "order_id": case_dict.get("order_id"),
            "payment_id": case_dict.get("payment_id"),
            "bank_utr": case_dict.get("bank_utr"),
            "discrepancy_category": case_dict.get("discrepancy_category"),
            "gross_amount": case_dict.get("gross_amount"),
            "net_variance": case_dict.get("net_variance"),
            "failure_cause": case_dict.get("failure_cause"),
            "deterministic_action": case_dict.get("remediation_action")
        }

    def recall_similar_cases(
        self,
        discrepancy_type: str,
        gateway: str = "Razorpay",
        merchant_name: str = "Apex Retail",
        failure_cause: str = "",
        net_variance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Tool: Queries Hindsight memory for similar historical exceptions."""
        return self.memory_service.recall_similar_exceptions(
            discrepancy_type=discrepancy_type,
            gateway=gateway,
            merchant_name=merchant_name,
            failure_cause=failure_cause,
            net_variance=net_variance
        )

    def reflect_on_historical_resolutions(
        self,
        discrepancy_type: str,
        gateway: str = "Razorpay",
        merchant_name: str = "Apex Retail"
    ) -> str:
        """Tool: Requests Hindsight synthesis of recurring patterns across historical resolutions."""
        return self.memory_service.reflect_on_resolution_patterns(
            discrepancy_type=discrepancy_type,
            gateway=gateway,
            merchant_name=merchant_name
        )

    def get_merchant_history(self, merchant_id: str) -> Dict[str, Any]:
        """Tool: Retrieves merchant profile and recurring exception rules."""
        memories = self.memory_service.client.recall(
            query=f"Merchant contract and rules for {merchant_id}",
            tags=[f"merchant:{merchant_id.lower()}"]
        )
        return {"merchant_id": merchant_id, "memories": memories}

    def get_gateway_history(self, gateway_name: str) -> Dict[str, Any]:
        """Tool: Retrieves gateway operational history and fee dispute standards."""
        memories = self.memory_service.client.recall(
            query=f"Gateway SLA and dispute rules for {gateway_name}",
            tags=[f"gateway:{gateway_name.lower()}"]
        )
        return {"gateway": gateway_name, "memories": memories}

    def retain_resolution_experience(self, case_memory: CaseMemory) -> Dict[str, Any]:
        """Tool: Persists a resolved exception into durable Hindsight memory."""
        return self.memory_service.retain_case_experience(case_memory)

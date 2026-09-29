from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CaseLifecycleState(str, Enum):
    DETECTED = "DETECTED"
    INVESTIGATING = "INVESTIGATING"
    RECOMMENDATION_READY = "RECOMMENDATION_READY"
    ACTION_TAKEN = "ACTION_TAKEN"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"

class MemoryMatchItem(BaseModel):
    id: str
    summary: str
    outcome: str
    evidence_used: str = "Standard documentation"
    relevance_score: float = 0.95
    full_text: str = ""

class HistoricalPattern(BaseModel):
    pattern_description: str
    sample_count: int
    success_rate_pct: float
    recommended_evidence: List[str] = Field(default_factory=list)
    average_turnaround_hours: float = 24.0

class OperatorOutcomeInput(BaseModel):
    case_id: str
    outcome_status: str = "RESOLVED"  # RESOLVED / UNSUCCESSFUL / ESCALATED
    final_resolution: str
    operator_notes: str = ""
    evidence_submitted: List[str] = Field(default_factory=list)
    refund_or_credit_received: float = 0.0

class AgentCaseAnalysis(BaseModel):
    """
    Strictly structured AI Finance Controller exception audit result.
    Separates deterministic arithmetic facts from Hindsight memory context.
    """
    case_id: str
    order_id: str
    payment_id: str
    discrepancy_type: str
    lifecycle_state: CaseLifecycleState = CaseLifecycleState.RECOMMENDATION_READY
    
    # Deterministic layer outputs (authoritative mathematical truth)
    current_case_summary: str
    deterministic_findings: Dict[str, Any]
    
    # Hindsight Memory layer outputs
    memory_matches: List[MemoryMatchItem] = Field(default_factory=list)
    historical_pattern: Optional[HistoricalPattern] = None
    memory_influenced: bool = False
    
    # Agent synthesis & recommendation
    recommended_action: str
    reasoning_summary: str
    supporting_evidence: List[str] = Field(default_factory=list)
    expected_next_step: str
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    requires_human_review: bool = True

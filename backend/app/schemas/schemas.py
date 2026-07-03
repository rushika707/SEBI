from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

# Auth & User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "Compliance Officer"
    organization_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Document Schemas
class DocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    file_type: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# Clause Schemas
class ClauseResponse(BaseModel):
    id: int
    clause_number: str
    title: Optional[str] = None
    content: str
    section_path: Optional[str] = None

    class Config:
        from_attributes = True

# Obligation Schemas
class ObligationResponse(BaseModel):
    id: int
    clause_id: Optional[int] = None
    document_id: int
    title: str
    description: str
    applicability: Optional[str] = None
    deadline: Optional[str] = None
    frequency: str
    penalties: Optional[str] = None
    exceptions: Optional[str] = None
    risk_level: str
    status: str
    created_at: datetime
    dependencies: Optional[Any] = None

    class Config:
        from_attributes = True

# Task & Evidence Schemas
class EvidenceCreate(BaseModel):
    description: Optional[str] = None

class EvidenceResponse(BaseModel):
    id: int
    task_id: int
    filename: str
    file_path: str
    uploaded_by: int
    description: Optional[str] = None
    verification_status: str
    verifier_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TaskUpdateStatus(BaseModel):
    status: str

class TaskResponse(BaseModel):
    id: int
    obligation_id: int
    title: str
    description: Optional[str] = None
    assignee_id: Optional[int] = None
    department_id: int
    due_date: Optional[datetime] = None
    status: str
    evidence_required: Optional[str] = None
    evidence_items: List[EvidenceResponse] = []
    obligation: Optional[ObligationResponse] = None

    class Config:
        from_attributes = True

# Workflow Schemas
class WorkflowResponse(BaseModel):
    id: int
    obligation_id: int
    name: str
    status: str
    step_data: Optional[Any] = None
    current_step: int

    class Config:
        from_attributes = True

# RAG & Search Schemas
class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5

class RAGCitation(BaseModel):
    document_id: int
    document_title: str
    clause_number: str
    content: str
    confidence: float
    reasoning: Optional[str] = None

class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[RAGCitation]
    confidence_score: float

# Version Diff Schemas
class DiffComparisonRequest(BaseModel):
    base_doc_id: int
    compare_doc_id: int

class DiffClauseMatch(BaseModel):
    clause_number: str
    base_content: Optional[str] = None
    compare_content: Optional[str] = None
    change_type: str  # "added", "deleted", "modified", "unchanged"
    timeline_changed: bool = False
    penalty_changed: bool = False

class DiffResponse(BaseModel):
    base_doc_title: str
    compare_doc_title: str
    diffs: List[DiffClauseMatch]
    impact_summary: str

# Gap Detection
class GapCheckRequest(BaseModel):
    organization_id: int

class GapDetail(BaseModel):
    obligation_id: int
    obligation_title: str
    risk_level: str
    task_id: int
    task_title: str
    status: str  # "missing_evidence", "pending_review", "approved", "expired"
    message: str

class GapDetectionResponse(BaseModel):
    compliance_score: float
    total_obligations: int
    compliant_count: int
    gap_count: int
    gaps: List[GapDetail]

# Audit Log
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[Any] = None
    timestamp: datetime

    class Config:
        from_attributes = True

# Dashboard Stats
class DashboardStatsResponse(BaseModel):
    compliance_score: float
    pending_obligations: int
    recent_circular_count: int
    high_risk_pending: int
    upcoming_deadlines: List[Dict[str, Any]]
    department_performance: List[Dict[str, Any]]
    risk_distribution: Dict[str, int]
    audit_readiness_score: float

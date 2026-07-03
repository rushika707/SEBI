import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.models import Task, Obligation, Document, Department, Evidence, User
from app.schemas.schemas import DashboardStatsResponse, GapDetectionResponse, GapDetail
from app.api.auth import get_current_user
from app.services.graph_service import graph_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    
    compliance_score = (completed_tasks / max(1, total_tasks)) * 100.0
    pending_obligations = db.query(Obligation).count() - completed_tasks
    recent_docs_count = db.query(Document).filter(Document.created_at >= datetime.datetime.utcnow() - datetime.timedelta(days=30)).count()

    high_risk_pending = db.query(Task).join(Task.obligation).filter(
        Task.status != "completed",
        Obligation.risk_level == "High"
    ).count()

    # Upcoming Deadlines
    upcoming_tasks = db.query(Task).filter(
        Task.status != "completed",
        Task.due_date.isnot(None)
    ).order_by(Task.due_date.asc()).limit(5).all()

    deadlines_list = []
    for t in upcoming_tasks:
        deadlines_list.append({
            "task_id": t.id,
            "title": t.title,
            "due_date": t.due_date.strftime("%Y-%m-%d"),
            "risk_level": t.obligation.risk_level,
            "department": t.department.name
        })

    # Department Compliance
    depts = db.query(Department).all()
    dept_performance = []
    for d in depts:
        d_tasks = db.query(Task).filter(Task.department_id == d.id).count()
        d_completed = db.query(Task).filter(Task.department_id == d.id, Task.status == "completed").count()
        dept_performance.append({
            "name": d.name,
            "compliance_rate": (d_completed / max(1, d_tasks)) * 100.0,
            "pending_count": d_tasks - d_completed
        })

    # Risk Distribution
    risk_dist = {
        "High": db.query(Obligation).filter(Obligation.risk_level == "High").count(),
        "Medium": db.query(Obligation).filter(Obligation.risk_level == "Medium").count(),
        "Low": db.query(Obligation).filter(Obligation.risk_level == "Low").count()
    }

    # Audit Readiness (approved evidence / total tasks)
    approved_evidence = db.query(Evidence).filter(Evidence.verification_status == "approved").count()
    audit_readiness_score = (approved_evidence / max(1, total_tasks)) * 100.0

    return DashboardStatsResponse(
        compliance_score=compliance_score,
        pending_obligations=max(0, pending_obligations),
        recent_circular_count=recent_docs_count,
        high_risk_pending=high_risk_pending,
        upcoming_deadlines=deadlines_list,
        department_performance=dept_performance,
        risk_distribution=risk_dist,
        audit_readiness_score=audit_readiness_score
    )

@router.get("/gaps", response_model=GapDetectionResponse)
def get_gap_detection(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_obligations = db.query(Obligation).count()
    
    tasks = db.query(Task).all()
    compliant_count = 0
    gaps: List[GapDetail] = []

    for t in tasks:
        # Check active evidence
        evidence = db.query(Evidence).filter(Evidence.task_id == t.id).order_by(Evidence.created_at.desc()).first()
        
        status = "missing_evidence"
        message = f"Compliance evidence missing. Assignee needs to upload: '{t.evidence_required or 'PDF File'}'."

        if t.status == "completed":
            compliant_count += 1
            status = "approved"
            message = "Task completed and verified by Compliance Lead."
        elif evidence:
            if evidence.verification_status == "pending":
                status = "pending_review"
                message = f"Evidence uploaded ('{evidence.filename}') is pending Compliance Officer review."
            elif evidence.verification_status == "rejected":
                status = "missing_evidence"
                message = f"Previous evidence '{evidence.filename}' was REJECTED. Please re-upload updated file."

        if status != "approved":
            gaps.append(GapDetail(
                obligation_id=t.obligation_id,
                obligation_title=t.obligation.title,
                risk_level=t.obligation.risk_level,
                task_id=t.id,
                task_title=t.title,
                status=status,
                message=message
            ))

    compliance_score = (compliant_count / max(1, len(tasks))) * 100.0

    return GapDetectionResponse(
        compliance_score=compliance_score,
        total_obligations=total_obligations,
        compliant_count=compliant_count,
        gap_count=len(gaps),
        gaps=gaps
    )

@router.get("/graph", response_model=Dict[str, Any])
def get_compliance_graph(current_user: User = Depends(get_current_user)):
    return graph_service.get_entire_graph()

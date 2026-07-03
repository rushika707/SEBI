import os
import shutil
import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.models import Workflow, Task, Evidence, User, Department, AuditLog, Report, Obligation
from app.schemas.schemas import WorkflowResponse, TaskResponse, EvidenceResponse, TaskUpdateStatus
from app.api.auth import get_current_user, check_role
from app.services.graph_service import graph_service
from app.services.pdf_generator import pdf_generator

router = APIRouter(prefix="/workflows", tags=["workflows"])

EVIDENCE_DIR = "./evidence"
os.makedirs(EVIDENCE_DIR, exist_ok=True)
REPORTS_DIR = "./reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Fetch workflows through obligations linked to documents in the user's organization
    return db.query(Workflow).join(Workflow.obligation).filter(Workflow.obligation.has(document_id=Workflow.obligation.property.mapper.class_.document_id)).all()

@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if department_id:
        query = query.filter(Task.department_id == department_id)
        
    return query.order_by(Task.due_date.asc()).all()

@router.get("/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/tasks/{task_id}/evidence", response_model=EvidenceResponse)
def upload_evidence(
    task_id: int,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Save evidence file
    filename = file.filename or "evidence_file"
    file_path = os.path.join(EVIDENCE_DIR, f"task_{task_id}_{int(datetime.datetime.utcnow().timestamp())}_{filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save Evidence record
    evidence = Evidence(
        task_id=task_id,
        filename=filename,
        file_path=file_path,
        uploaded_by=current_user.id,
        description=description,
        verification_status="pending",
        audit_trail={"actions": [{"action": "uploaded", "user": current_user.email, "timestamp": str(datetime.datetime.utcnow())}]}
    )
    db.add(evidence)
    
    # Update Task Status
    task.status = "in_progress" # Pending verification
    
    # Log Audit Log
    log = AuditLog(
        user_id=current_user.id,
        action="UPLOAD_EVIDENCE",
        target_type="task",
        target_id=task_id,
        details={"filename": filename, "task_title": task.title}
    )
    db.add(log)
    db.commit()
    db.refresh(evidence)

    # Add Evidence node to Neo4j graph
    graph_service.add_node(
        node_id=f"evidence_{evidence.id}",
        label="Evidence",
        properties={
            "filename": evidence.filename,
            "status": evidence.verification_status,
            "uploaded_by": current_user.full_name
        }
    )
    # Link Employee/User to Evidence
    graph_service.add_relationship(
        source_id=f"evidence_{evidence.id}",
        target_id=f"obligation_{task.obligation_id}",
        rel_type="PROVES_OBLIGATION"
    )

    return evidence

@router.post("/tasks/{task_id}/verify", response_model=TaskResponse)
def verify_task_evidence(
    task_id: int,
    action: str = Form(...),  # approve, reject
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role(["Compliance Officer", "Compliance Manager", "Admin"]))
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    evidence = db.query(Evidence).filter(Evidence.task_id == task_id).order_by(Evidence.created_at.desc()).first()
    if not evidence:
        raise HTTPException(status_code=404, detail="No evidence found for this task")

    if action == "approve":
        evidence.verification_status = "approved"
        evidence.verifier_id = current_user.id
        task.status = "completed"
        
        # Update Neo4j Node Status
        graph_service.add_node(
            node_id=f"evidence_{evidence.id}",
            label="Evidence",
            properties={
                "filename": evidence.filename,
                "status": "approved",
                "uploaded_by": evidence.uploader.full_name if evidence.uploader else ""
            }
        )
    elif action == "reject":
        evidence.verification_status = "rejected"
        evidence.verifier_id = current_user.id
        task.status = "pending" # Send back to pending compliance action
        
        graph_service.add_node(
            node_id=f"evidence_{evidence.id}",
            label="Evidence",
            properties={
                "filename": evidence.filename,
                "status": "rejected",
                "uploaded_by": evidence.uploader.full_name if evidence.uploader else ""
            }
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid verification action. Choose 'approve' or 'reject'.")

    # Update audit trail
    trail = dict(evidence.audit_trail or {})
    actions = trail.get("actions", [])
    actions.append({
        "action": action,
        "user": current_user.email,
        "comment": comment,
        "timestamp": str(datetime.datetime.utcnow())
    })
    evidence.audit_trail = {"actions": actions}

    log = AuditLog(
        user_id=current_user.id,
        action="VERIFY_EVIDENCE",
        target_type="task",
        target_id=task_id,
        details={"status": action, "comment": comment}
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    return task

@router.post("/export-report")
def export_audit_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Calculate compliance metrics
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    
    score = (completed_tasks / max(1, total_tasks)) * 100.0
    
    # 2. Extract Gaps
    gaps = []
    pending_tasks = db.query(Task).filter(Task.status != "completed").all()
    for t in pending_tasks:
        gaps.append({
            "obligation_title": t.obligation.title,
            "risk_level": t.obligation.risk_level,
            "message": f"Task '{t.title}' is currently {t.status}. Assignee needs to upload evidence: '{t.evidence_required}'"
        })

    # 3. Extract Evidence
    evidence_list = []
    ev_records = db.query(Evidence).order_by(Evidence.created_at.desc()).all()
    for ev in ev_records:
        evidence_list.append({
            "filename": ev.filename,
            "task_title": ev.task.title,
            "status": ev.verification_status,
            "uploaded_at": ev.created_at.strftime("%Y-%m-%d %H:%M")
        })

    report_data = {
        "compliance_score": score,
        "total_obligations": db.query(Obligation).count(),
        "compliant_count": completed_tasks,
        "gap_count": len(gaps),
        "gaps": gaps,
        "evidence_items": evidence_list,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    # Generate File
    report_filename = f"sebi_audit_report_{int(datetime.datetime.utcnow().timestamp())}.pdf"
    filepath = os.path.join(REPORTS_DIR, report_filename)
    
    pdf_generator.generate_audit_report(filepath, report_data)

    # Save report metadata
    rep = Report(
        title=f"Audit Report {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        file_path=filepath,
        type="summary"
    )
    db.add(rep)
    
    # Audit trail log
    log = AuditLog(
        user_id=current_user.id,
        action="GENERATE_REPORT",
        target_type="report",
        target_id=None,
        details={"filename": report_filename}
    )
    db.add(log)
    db.commit()

    return FileResponse(
        filepath, 
        media_type="application/pdf", 
        filename=report_filename
    )

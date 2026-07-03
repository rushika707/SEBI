import os
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.models import Document, Clause, Obligation, User
from app.schemas.schemas import DocumentResponse, ClauseResponse, ObligationResponse, DiffComparisonRequest, DiffResponse, RAGQueryRequest, RAGQueryResponse
from app.api.auth import get_current_user, check_role
from app.agents.agent_orchestrator import agent_orchestrator
from app.services.diff_service import diff_service
from app.services.rag_service import rag_service

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def process_document_pipeline(doc_id: int, db_session_creator):
    db: Session = db_session_creator()
    try:
        # Step 1: Parse Document
        parse_res = agent_orchestrator.parse_document(db, doc_id)
        
        # Fetch clauses for document
        clauses = db.query(Clause).filter(Clause.document_id == doc_id).all()
        
        # Step 2 & 3: For each clause, extract obligations and build workflows
        for c in clauses:
            obligations = agent_orchestrator.extract_obligations(db, c.id)
            for o in obligations:
                agent_orchestrator.generate_workflow(db, o.id)
                
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        # Log to document status
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "error"
            doc.error_message = f"Pipeline failed: {str(e)}\n{error_details}"
            db.commit()
    finally:
        db.close()

@router.post("/upload", response_model=DocumentResponse)
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    file_type: str = Form("circular"), # circular, notification, master_circular
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Save the file locally
    filename = file.filename or "uploaded_file"
    file_path = os.path.join(UPLOAD_DIR, f"{int(datetime.datetime.utcnow().timestamp())}_{filename}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save initial Document metadata
    doc = Document(
        title=title,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        status="pending",
        uploaded_by=current_user.id,
        organization_id=current_user.organization_id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Spawn background task for ingestion pipeline
    from app.core.database import SessionLocal
    background_tasks.add_task(process_document_pipeline, doc.id, SessionLocal)

    return doc

@router.get("/", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Document).filter(Document.organization_id == current_user.organization_id).order_by(Document.created_at.desc()).all()

@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.organization_id == current_user.organization_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/{doc_id}/clauses", response_model=List[ClauseResponse])
def get_document_clauses(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.organization_id == current_user.organization_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return db.query(Clause).filter(Clause.document_id == doc_id).all()

@router.get("/{doc_id}/obligations", response_model=List[ObligationResponse])
def get_document_obligations(doc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doc = db.query(Document).filter(Document.id == doc_id, Document.organization_id == current_user.organization_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return db.query(Obligation).filter(Obligation.document_id == doc_id).all()

@router.post("/diff", response_model=DiffResponse)
def compare_document_versions(
    payload: DiffComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    base_doc = db.query(Document).filter(Document.id == payload.base_doc_id).first()
    compare_doc = db.query(Document).filter(Document.id == payload.compare_doc_id).first()

    if not base_doc or not compare_doc:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    base_clauses = db.query(Clause).filter(Clause.document_id == base_doc.id).all()
    compare_clauses = db.query(Clause).filter(Clause.document_id == compare_doc.id).all()

    base_clauses_data = [{"clause_number": c.clause_number, "content": c.content} for c in base_clauses]
    compare_clauses_data = [{"clause_number": c.clause_number, "content": c.content} for c in compare_clauses]

    # Optionally pass a dummy/mock AI service for diff summaries
    res = diff_service.compare_documents(
        base_title=base_doc.title,
        base_clauses=base_clauses_data,
        compare_title=compare_doc.title,
        compare_clauses=compare_clauses_data
    )
    return res

@router.post("/rag", response_model=RAGQueryResponse)
def execute_hybrid_rag(
    payload: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return rag_service.query(db, payload.query, top_k=payload.top_k)
import datetime

import os
import sys

# Add backend directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.models import User, Organization, Document, Clause, Obligation, Task, Department
from app.services.diff_service import diff_service
from app.services.rag_service import rag_service

def test_settings_load():
    print("[OK] Config Settings Loaded successfully.")
    assert settings.PROJECT_NAME == "SEBI CoPilot API"

def test_database_initialization():
    print("Creating local test schemas...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Verify seeding check
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Test Intermediary Corp")
            db.add(org)
            db.commit()
            db.refresh(org)
        print(f"[OK] Database Initialized and seeded organization: {org.name}")
        assert org.id is not None
    finally:
        db.close()

def test_diff_service():
    base_clauses = [{"clause_number": "1.1", "content": "Initial timeline is 30 days."}]
    compare_clauses = [{"clause_number": "1.1", "content": "Amended timeline is 15 days."}]
    
    diff = diff_service.compare_documents(
        base_title="Version A",
        base_clauses=base_clauses,
        compare_title="Version B",
        compare_clauses=compare_clauses
    )
    
    print("[OK] Diff Engine compared versions correctly.")
    assert len(diff.diffs) == 1
    assert diff.diffs[0].change_type == "modified"
    assert diff.diffs[0].timeline_changed == True

def test_rag_fallback():
    db = SessionLocal()
    try:
        res = rag_service.query(db, "VAPT Audits", top_k=2)
        print("[OK] RAG fallback Query execution successfully completed.")
        assert res.answer is not None
        assert isinstance(res.citations, list)
    finally:
        db.close()


if __name__ == "__main__":
    print("=== STARTING BACKEND PIPELINE CHECKS ===")
    test_settings_load()
    test_database_initialization()
    test_diff_service()
    test_rag_fallback()
    print("=== ALL PIPELINE CHECKS COMPLETED SUCCESSFULY ===")

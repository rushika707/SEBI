import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="Compliance Officer")  # Admin, Compliance Officer, Compliance Manager, Auditor
    is_active = Column(Boolean, default=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="users")
    evidence_submitted = relationship("Evidence", back_populates="uploader", foreign_keys="[Evidence.uploaded_by]")
    evidence_verified = relationship("Evidence", back_populates="verifier", foreign_keys="[Evidence.verifier_id]")
    tasks_assigned = relationship("Task", back_populates="assignee")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # circular, notification, master_circular
    status = Column(String, default="pending")  # pending, processing, parsed, error
    error_message = Column(Text, nullable=True)
    parsed_content = Column(JSON, nullable=True)  # Store parsed paragraphs/metadata
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    organization = relationship("Organization", back_populates="documents")
    clauses = relationship("Clause", back_populates="document", cascade="all, delete-orphan")
    obligations = relationship("Obligation", back_populates="document", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    clause_number = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    section_path = Column(String, nullable=True) # e.g. "Section I > Chapter 2"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="clauses")
    obligations = relationship("Obligation", back_populates="clause", cascade="all, delete-orphan")


class Obligation(Base):
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    clause_id = Column(Integer, ForeignKey("clauses.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    applicability = Column(String, nullable=True)  # Affected Intermediaries
    deadline = Column(String, nullable=True)
    frequency = Column(String, default="Ad-hoc")  # Monthly, Quarterly, Annually, Ad-hoc
    penalties = Column(Text, nullable=True)
    exceptions = Column(Text, nullable=True)
    dependencies = Column(JSON, nullable=True)  # References to other clauses
    risk_level = Column(String, default="Medium")  # Low, Medium, High
    status = Column(String, default="active")  # active, superseded
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="obligations")
    clause = relationship("Clause", back_populates="obligations")
    tasks = relationship("Task", back_populates="obligation", cascade="all, delete-orphan")
    workflows = relationship("Workflow", back_populates="obligation", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    tasks = relationship("Task", back_populates="department")


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, default="draft")  # draft, active, suspended
    step_data = Column(JSON, nullable=True)  # React Flow state representation or checklist steps
    current_step = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    obligation = relationship("Obligation", back_populates="workflows")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    obligation_id = Column(Integer, ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, in_progress, completed, overdue
    evidence_required = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    obligation = relationship("Obligation", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks_assigned")
    department = relationship("Department", back_populates="tasks")
    evidence_items = relationship("Evidence", back_populates="task", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=True)
    verification_status = Column(String, default="pending")  # pending, approved, rejected
    verifier_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    audit_trail = Column(JSON, nullable=True)  # History of actions
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="evidence_items")
    uploader = relationship("User", back_populates="evidence_submitted", foreign_keys=[uploaded_by])
    verifier = relationship("User", back_populates="evidence_verified", foreign_keys=[verifier_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # e.g., "UPLOAD_DOCUMENT", "APPROVE_EVIDENCE"
    target_type = Column(String, nullable=True)  # e.g., "document", "task"
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info")  # info, reminder, alert
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    type = Column(String, nullable=False)  # summary, matrix, risk
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

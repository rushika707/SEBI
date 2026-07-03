import re
import json
import logging
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import pdfplumber

from app.core.config import settings
from app.models.models import Document, Clause, Obligation, Task, Department, Workflow, Evidence
from app.services.vector_service import vector_service
from app.services.graph_service import graph_service

logger = logging.getLogger("sebi_copilot.agents")

class AgentOrchestrator:
    # ----------------------------------------------------
    # 1. Document Parser Agent
    # ----------------------------------------------------
    def parse_document(self, db: Session, doc_id: int) -> Dict[str, Any]:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError("Document not found")
        
        logger.info(f"Parser Agent starting for Document {doc_id}: {document.filename}")
        document.status = "processing"
        db.commit()

        clauses_data = []
        try:
            # Check file extension
            text_content = ""
            if document.file_path.endswith(".pdf"):
                with pdfplumber.open(document.file_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- PAGE {i+1} ---\n{page_text}"
            else:
                # Text/Markdown/Fallback
                with open(document.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text_content = f.read()

            if not text_content.strip():
                raise ValueError("Extracted text content is empty.")

            # Simple clause parsing heuristic: split by lines starting with numbers/bullet points
            # e.g., "1. Scope", "2. Applicability", or "(a) Mutual Funds"
            lines = text_content.split("\n")
            current_clause_num = "General"
            current_clause_title = "Introductory Information"
            current_clause_text = []
            clause_idx = 1

            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                # Regex to check if line starts with a clause identifier: e.g. "1.", "2.3", "Chapter III", "A."
                match = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.*)', line_str)
                chapter_match = re.match(r'^(Chapter\s+[IVXLCDM]+|Section\s+[A-Z\d]+)\.?\s*(.*)', line_str, re.IGNORECASE)
                
                if match:
                    # Save preceding clause
                    if current_clause_text:
                        clauses_data.append({
                            "clause_number": current_clause_num,
                            "title": current_clause_title,
                            "content": "\n".join(current_clause_text).strip(),
                            "section_path": "General"
                        })
                    current_clause_num = match.group(1)
                    current_clause_title = match.group(2)[:100]
                    current_clause_text = [line_str]
                    clause_idx += 1
                elif chapter_match:
                    if current_clause_text:
                        clauses_data.append({
                            "clause_number": current_clause_num,
                            "title": current_clause_title,
                            "content": "\n".join(current_clause_text).strip(),
                            "section_path": "General"
                        })
                    current_clause_num = chapter_match.group(1)
                    current_clause_title = chapter_match.group(2)[:100] or "Heading"
                    current_clause_text = [line_str]
                else:
                    current_clause_text.append(line_str)

            # Add final clause
            if current_clause_text:
                clauses_data.append({
                    "clause_number": current_clause_num,
                    "title": current_clause_title,
                    "content": "\n".join(current_clause_text).strip(),
                    "section_path": "General"
                })

            # Save clauses to SQLite/Postgres DB
            for idx, c in enumerate(clauses_data):
                db_clause = Clause(
                    document_id=doc_id,
                    clause_number=c["clause_number"],
                    title=c["title"],
                    content=c["content"],
                    section_path=c["section_path"]
                )
                db.add(db_clause)
                db.commit()
                db.refresh(db_clause)

                # Add to Vector database (Qdrant)
                vector_service.upsert_clause(
                    clause_id=db_clause.id,
                    document_id=doc_id,
                    clause_number=db_clause.clause_number,
                    text=db_clause.content,
                    title=document.title
                )

                # Add to Graph Database (Neo4j)
                graph_service.add_node(
                    node_id=f"clause_{db_clause.id}",
                    label="Clause",
                    properties={
                        "clause_number": db_clause.clause_number,
                        "title": db_clause.title or "",
                        "content": db_clause.content[:100]
                    }
                )
                graph_service.add_relationship(
                    source_id=f"doc_{doc_id}",
                    target_id=f"clause_{db_clause.id}",
                    rel_type="HAS_CLAUSE"
                )

            # Update document status
            document.status = "parsed"
            document.parsed_content = {"clauses_count": len(clauses_data)}
            db.commit()

            # Add Document to Graph
            graph_service.add_node(
                node_id=f"doc_{doc_id}",
                label="Regulation",
                properties={
                    "title": document.title,
                    "file_type": document.file_type,
                    "date": datetime.datetime.now().strftime("%Y-%m-%d")
                }
            )

            logger.info(f"Parser Agent completed successfully. Extracted {len(clauses_data)} clauses.")
            return {"status": "success", "clauses_count": len(clauses_data)}

        except Exception as e:
            logger.error(f"Parser Agent failed: {e}")
            document.status = "error"
            document.error_message = str(e)
            db.commit()
            raise e

    # ----------------------------------------------------
    # 2. Obligation Extraction Agent
    # ----------------------------------------------------
    def extract_obligations(self, db: Session, clause_id: int) -> List[Dict[str, Any]]:
        clause = db.query(Clause).filter(Clause.id == clause_id).first()
        if not clause:
            return []

        logger.info(f"Obligation Agent analyzing Clause {clause.clause_number}...")
        
        # Default procedural parsing if no AI key configured
        title = f"Compliance requirement for clause {clause.clause_number}"
        description = clause.content
        applicability = "All Intermediaries"
        deadline = "Immediate"
        frequency = "Ad-hoc"
        penalties = "As per SEBI regulations"
        risk_level = "Medium"
        exceptions = "None"
        
        # Simple keywords search heuristics
        lower_content = clause.content.lower()
        if "mutual fund" in lower_content:
            applicability = "Mutual Funds"
        elif "broker" in lower_content or "stock broker" in lower_content:
            applicability = "Stock Brokers"
        elif "portfolio manager" in lower_content:
            applicability = "Portfolio Managers"

        if "monthly" in lower_content:
            frequency = "Monthly"
            deadline = "Within 10 days of end of month"
        elif "quarterly" in lower_content:
            frequency = "Quarterly"
            deadline = "Within 21 days of end of quarter"
        elif "annual" in lower_content or "yearly" in lower_content:
            frequency = "Annually"
            deadline = "Within 60 days of financial year end"

        if any(w in lower_content for w in ["fine", "penalty", "liable", "imprisonment"]):
            penalties = "Financial penalty or suspension of registration"
            risk_level = "High"

        # AI Augmentation
        ai_extracted = None
        if settings.OPENAI_API_KEY or settings.GEMINI_API_KEY:
            prompt = (
                "You are an expert SEBI Compliance Officer. Analyze this clause and extract structured compliance obligations:\n\n"
                f"Clause Content: {clause.content}\n\n"
                "Return a JSON object containing keys: 'title', 'description', 'applicability', 'deadline', 'frequency', 'penalties', 'exceptions', 'risk_level'."
            )
            try:
                raw_ai = None
                if settings.OPENAI_API_KEY:
                    from openai import OpenAI
                    client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        response_format={"type": "json_object"},
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw_ai = resp.choices[0].message.content
                elif settings.GEMINI_API_KEY:
                    import google.generativeai as genai
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
                    resp = model.generate_content(prompt)
                    raw_ai = resp.text

                if raw_ai:
                    ai_extracted = json.loads(raw_ai)
            except Exception as e:
                logger.error(f"LLM Obligation extraction failed: {e}")

        if ai_extracted:
            title = ai_extracted.get("title", title)
            description = ai_extracted.get("description", description)
            applicability = ai_extracted.get("applicability", applicability)
            deadline = ai_extracted.get("deadline", deadline)
            frequency = ai_extracted.get("frequency", frequency)
            penalties = ai_extracted.get("penalties", penalties)
            exceptions = ai_extracted.get("exceptions", exceptions)
            risk_level = ai_extracted.get("risk_level", risk_level)

        # Create Obligation database model
        obligation = Obligation(
            clause_id=clause_id,
            document_id=clause.document_id,
            title=title,
            description=description,
            applicability=applicability,
            deadline=deadline,
            frequency=frequency,
            penalties=penalties,
            exceptions=exceptions,
            risk_level=risk_level,
            dependencies={}
        )
        db.add(obligation)
        db.commit()
        db.refresh(obligation)

        # Add node and relationships to graph
        graph_service.add_node(
            node_id=f"obligation_{obligation.id}",
            label="Obligation",
            properties={
                "title": obligation.title,
                "risk_level": obligation.risk_level,
                "frequency": obligation.frequency
            }
        )
        graph_service.add_relationship(
            source_id=f"clause_{clause_id}",
            target_id=f"obligation_{obligation.id}",
            rel_type="HAS_OBLIGATION"
        )

        return [obligation]

    # ----------------------------------------------------
    # 3. Workflow Generation Agent
    # ----------------------------------------------------
    def generate_workflow(self, db: Session, obligation_id: int) -> Workflow:
        obligation = db.query(Obligation).filter(Obligation.id == obligation_id).first()
        if not obligation:
            raise ValueError("Obligation not found")

        logger.info(f"Workflow Agent generating executable tasks for Obligation {obligation_id}...")

        # Resolve department names in organization or default
        dept_names = ["Compliance", "Operations", "Finance", "Legal"]
        depts = {}
        for name in dept_names:
            dept = db.query(Department).filter(Department.name == name).first()
            if not dept:
                dept = Department(name=name)
                db.add(dept)
                db.commit()
                db.refresh(dept)
            depts[name] = dept

        # Default tasks matching obligation frequency and applicability
        default_dept = depts["Compliance"]
        if "finance" in obligation.description.lower() or "audit" in obligation.description.lower():
            default_dept = depts["Finance"]
        elif "trading" in obligation.description.lower() or "portfolio" in obligation.description.lower():
            default_dept = depts["Operations"]

        workflow_tasks_data = [
            {
                "title": f"Review SEBI Obligation: {obligation.title}",
                "description": f"Detailed review of obligation: {obligation.description}. Identify implementation requirements.",
                "department_id": default_dept.id,
                "evidence_required": "Internal policy draft or analysis document signed by the compliance lead."
            },
            {
                "title": f"Implement Compliance Checklist Tasks",
                "description": f"Perform required configurations, operational processes, or filings to meet deadline: {obligation.deadline}.",
                "department_id": default_dept.id,
                "evidence_required": "Screenshots of systems configuration or filing confirmation receipts."
            },
            {
                "title": f"Upload Audit Verification Files",
                "description": "Upload evidence files confirming the organization meets the standards defined.",
                "department_id": default_dept.id,
                "evidence_required": "Formal compliance report PDF."
            }
        ]

        # AI Workflow Compiler
        ai_tasks = None
        if settings.OPENAI_API_KEY or settings.GEMINI_API_KEY:
            prompt = (
                "You are a compliance systems compiler. Turn the following SEBI compliance obligation into an executable workflow checklist:\n\n"
                f"Obligation: {obligation.title}\n"
                f"Description: {obligation.description}\n"
                f"Frequency: {obligation.frequency}\n"
                f"Applicability: {obligation.applicability}\n\n"
                "Return a JSON array of tasks where each task is an object with fields: 'title', 'description', 'department', 'evidence_required'. "
                "Departments should be one of: 'Compliance', 'Operations', 'Finance', 'Legal'."
            )
            try:
                raw_ai = None
                if settings.OPENAI_API_KEY:
                    from openai import OpenAI
                    client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        response_format={"type": "json_object"},
                        messages=[{"role": "user", "content": prompt}]
                    )
                    raw_ai = resp.choices[0].message.content
                elif settings.GEMINI_API_KEY:
                    import google.generativeai as genai
                    genai.configure(api_key=settings.GEMINI_API_KEY)
                    model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
                    resp = model.generate_content(prompt)
                    raw_ai = resp.text

                if raw_ai:
                    ai_res = json.loads(raw_ai)
                    if isinstance(ai_res, dict) and "tasks" in ai_res:
                        ai_tasks = ai_res["tasks"]
                    elif isinstance(ai_res, list):
                        ai_tasks = ai_res
            except Exception as e:
                logger.error(f"LLM Workflow compilation failed: {e}")

        if ai_tasks:
            workflow_tasks_data = []
            for t in ai_tasks:
                dept_name = t.get("department", "Compliance")
                if dept_name not in depts:
                    # Auto create
                    new_dept = Department(name=dept_name)
                    db.add(new_dept)
                    db.commit()
                    db.refresh(new_dept)
                    depts[dept_name] = new_dept
                workflow_tasks_data.append({
                    "title": t.get("title", "Checklist Task"),
                    "description": t.get("description", ""),
                    "department_id": depts[dept_name].id,
                    "evidence_required": t.get("evidence_required", "Upload verified PDF")
                })

        # Save workflow model
        workflow = Workflow(
            obligation_id=obligation_id,
            name=f"Workflow: {obligation.title}",
            status="active",
            step_data={"steps_count": len(workflow_tasks_data)},
            current_step=1
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)

        # Create tasks
        for idx, t in enumerate(workflow_tasks_data):
            task = Task(
                obligation_id=obligation_id,
                title=t["title"],
                description=t["description"],
                department_id=t["department_id"],
                due_date=datetime.datetime.utcnow() + datetime.timedelta(days=(idx + 1) * 7),
                status="pending",
                evidence_required=t["evidence_required"]
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            # Add Department node to graph (if not exists)
            dept = db.query(Department).filter(Department.id == t["department_id"]).first()
            graph_service.add_node(
                node_id=f"dept_{dept.id}",
                label="Department",
                properties={"name": dept.name}
            )
            # Link Obligation to Department
            graph_service.add_relationship(
                source_id=f"obligation_{obligation_id}",
                target_id=f"dept_{dept.id}",
                rel_type="ASSIGNED_TO"
            )

        logger.info(f"Workflow compilation complete. Created {len(workflow_tasks_data)} tasks.")
        return workflow

# Global instance
agent_orchestrator = AgentOrchestrator()

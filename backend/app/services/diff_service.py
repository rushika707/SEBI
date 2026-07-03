import difflib
import re
from typing import List, Dict, Any, Tuple
from app.schemas.schemas import DiffClauseMatch, DiffResponse

class DiffService:
    def clean_text(self, text: str) -> str:
        # Standardize text for cleaner diffs
        return re.sub(r'\s+', ' ', text).strip()

    def extract_dates_and_amounts(self, text: str) -> Tuple[List[str], List[str]]:
        # Extract date-like strings
        dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b', text, re.IGNORECASE)
        # Extract currency/penalty amounts (e.g. Rs. 5,000, 10 lakhs, etc.)
        penalties = re.findall(r'(?:Rs\.?|INR|rupees|fine|penalty of)\s*\d+[\d,]*\s*(?:lakh|crore)?', text, re.IGNORECASE)
        return dates, penalties

    def compare_documents(self, base_title: str, base_clauses: List[Dict[str, Any]], compare_title: str, compare_clauses: List[Dict[str, Any]], llm_service=None) -> DiffResponse:
        base_dict = {c["clause_number"]: c["content"] for c in base_clauses}
        compare_dict = {c["clause_number"]: c["content"] for c in compare_clauses}

        all_clause_numbers = sorted(list(set(base_dict.keys()).union(set(compare_dict.keys()))), key=lambda x: [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', x)])

        diffs = []
        modified_count = 0
        added_count = 0
        deleted_count = 0

        for num in all_clause_numbers:
            base_content = base_dict.get(num)
            compare_content = compare_dict.get(num)

            if base_content and compare_content:
                base_clean = self.clean_text(base_content)
                compare_clean = self.clean_text(compare_content)

                if base_clean == compare_clean:
                    diffs.append(DiffClauseMatch(
                        clause_number=num,
                        base_content=base_content,
                        compare_content=compare_content,
                        change_type="unchanged"
                    ))
                else:
                    modified_count += 1
                    base_dates, base_penalties = self.extract_dates_and_amounts(base_clean)
                    comp_dates, comp_penalties = self.extract_dates_and_amounts(compare_clean)

                    timeline_changed = base_dates != comp_dates
                    penalty_changed = base_penalties != comp_penalties

                    diffs.append(DiffClauseMatch(
                        clause_number=num,
                        base_content=base_content,
                        compare_content=compare_content,
                        change_type="modified",
                        timeline_changed=timeline_changed,
                        penalty_changed=penalty_changed
                    ))
            elif compare_content:
                added_count += 1
                diffs.append(DiffClauseMatch(
                    clause_number=num,
                    base_content=None,
                    compare_content=compare_content,
                    change_type="added"
                ))
            else:
                deleted_count += 1
                diffs.append(DiffClauseMatch(
                    clause_number=num,
                    base_content=base_content,
                    compare_content=None,
                    change_type="deleted"
                ))

        # Generate impact summary
        impact_summary = (
            f"Comparison between Base Regulation '{base_title}' and New Regulation '{compare_title}':\n"
            f"- Total structural clauses processed: {len(all_clause_numbers)}\n"
            f"- Modified clauses: {modified_count}\n"
            f"- Added clauses: {added_count}\n"
            f"- Deleted clauses: {deleted_count}\n\n"
        )

        if modified_count > 0 or added_count > 0 or deleted_count > 0:
            impact_summary += "Key Changes Summary:\n"
            for d in diffs:
                if d.change_type == "modified":
                    impact_summary += f"- Clause {d.clause_number} has been updated. "
                    if d.timeline_changed:
                        impact_summary += "[TIMELINE UPDATE DETECTED] "
                    if d.penalty_changed:
                        impact_summary += "[PENALTY UPDATE DETECTED] "
                    impact_summary += "\n"
                elif d.change_type == "added":
                    impact_summary += f"- Clause {d.clause_number} is newly introduced.\n"
                elif d.change_type == "deleted":
                    impact_summary += f"- Clause {d.clause_number} has been removed.\n"
        else:
            impact_summary += "No functional or wording changes were identified between the versions."

        # If LLM service is available, we can augment with a nice summary
        if llm_service:
            try:
                # Compile changes text to pass to LLM
                changes_payload = []
                for d in diffs:
                    if d.change_type != "unchanged":
                        changes_payload.append({
                            "clause": d.clause_number,
                            "type": d.change_type,
                            "before": d.base_content,
                            "after": d.compare_content
                        })
                
                # Truncate to avoid context limit
                serialized_changes = json.dumps(changes_payload[:20]) 
                prompt = (
                    f"Analyze these regulatory changes from SEBI and write a concise, professional executive impact summary for compliance officers:\n"
                    f"Base Document: {base_title}\n"
                    f"New Document: {compare_title}\n"
                    f"Changes list: {serialized_changes}\n"
                    f"Output a summary highlighting operational impacts, timeline changes, and penalty modifications in clean markdown."
                )
                ai_summary = llm_service.generate_summary(prompt)
                if ai_summary:
                    impact_summary = ai_summary
            except Exception as e:
                # Fallback to standard summary
                pass

        return DiffResponse(
            base_doc_title=base_title,
            compare_doc_title=compare_title,
            diffs=diffs,
            impact_summary=impact_summary
        )

diff_service = DiffService()

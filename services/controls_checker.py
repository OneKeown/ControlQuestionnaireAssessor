import json
from typing import List
from models.assessment_models import ControlResult


class ControlService:
    def load_controls(self, path: str = "data/controls.json") -> List[dict]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def assess_control_from_chunks(self, control: dict, chunks: list[dict]) -> ControlResult:
        combined_text = " ".join(chunk["text"] for chunk in chunks).lower()

        expected_hits = [term for term in control["expected_terms"] if term.lower() in combined_text]
        fail_hits = [term for term in control["fail_terms"] if term.lower() in combined_text]

        best_chunk = chunks[0] if chunks else None
        excerpt = best_chunk["text"][:500] if best_chunk else None
        source_file = best_chunk["source"] if best_chunk else None
        source_page = best_chunk.get("page_number") if best_chunk else None

        if fail_hits:
            return ControlResult(
                control_id=control["control_id"],
                category=control["category"],
                requirement=control["requirement"],
                status="Fail",
                reason=f"Relevant answer contains weak or failing language: {', '.join(fail_hits)}.",
                confidence=0.85,
                source_excerpt=excerpt,
                source_file=source_file,
                source_page=source_page,
            )

        if len(expected_hits) >= 2:
            return ControlResult(
                control_id=control["control_id"],
                category=control["category"],
                requirement=control["requirement"],
                status="Pass",
                reason=f"Relevant answer contains expected evidence terms: {', '.join(expected_hits)}.",
                confidence=0.85,
                source_excerpt=excerpt,
                source_file=source_file,
                source_page=source_page,
            )

        if len(expected_hits) == 1:
            return ControlResult(
                control_id=control["control_id"],
                category=control["category"],
                requirement=control["requirement"],
                status="Needs review",
                reason=f"Some relevant evidence was found ({expected_hits[0]}), but not enough to confirm the control.",
                confidence=0.55,
                source_excerpt=excerpt,
                source_file=source_file,
                source_page=source_page,
            )

        return ControlResult(
            control_id=control["control_id"],
            category=control["category"],
            requirement=control["requirement"],
            status="Needs review",
            reason="Could not find enough relevant evidence in the retrieved questionnaire content.",
            confidence=0.3,
            source_excerpt=excerpt,
            source_file=source_file,
            source_page=source_page,
        )
        
    def summarise_results(self, controls: list[dict], results: list) -> dict:
        control_map = {c["control_id"]: c for c in controls}

        total = len(results)
        passed = sum(1 for r in results if r.status == "Pass")
        failed = sum(1 for r in results if r.status == "Fail")
        needs_review = sum(1 for r in results if r.status == "Needs review")

        critical_failures = []
        for result in results:
            control = control_map.get(result.control_id, {})
            if result.status == "Fail" and control.get("critical", False):
                critical_failures.append(result.control_id)

        overall_status = "Pass"
        if critical_failures or failed > 0:
            overall_status = "Fail"
        elif needs_review > 0:
            overall_status = "Needs review"

        summary_reason = []
        if critical_failures:
            summary_reason.append(
                f"Critical control failures: {', '.join(critical_failures)}"
            )
        if failed > 0:
            summary_reason.append(f"{failed} control(s) failed")
        if needs_review > 0:
            summary_reason.append(f"{needs_review} control(s) need review")
        if not summary_reason:
            summary_reason.append("All assessed controls passed")

        return {
            "overall_status": overall_status,
            "total": total,
            "passed": passed,
            "failed": failed,
            "needs_review": needs_review,
            "critical_failures": critical_failures,
            "summary_reason": " | ".join(summary_reason),
        }    
    def assess_with_llm_fallback(self, control: dict, chunks: list[dict], llm_service) -> ControlResult:
        rule_result = self.assess_control_from_chunks(control, chunks)

        if rule_result.status in ["Pass", "Fail"]:
            return rule_result

        context = "\n\n".join(
            [
                f"Source: {c['source']} | Page: {c.get('page_number')} | Type: {c.get('doc_type')}\n{c['text']}"
                for c in chunks
            ]
    )

        prompt = f"""
Assess whether the supplier response meets this security control.

Control:
{control['requirement']}

Retrieved questionnaire content:
{context}

Return:
1. Status: Pass, Fail, or Needs review
2. One short reason

Be strict. If the answer is vague, partial, planned, or unclear, use Needs review or Fail.
"""

        answer = llm_service.answer_question(prompt, chunks)

        status = "Needs review"
        upper = answer.upper()
        if "STATUS: PASS" in upper or upper.startswith("PASS"):
            status = "Pass"
        elif "STATUS: FAIL" in upper or upper.startswith("FAIL"):
            status = "Fail"
        elif "STATUS: NEEDS REVIEW" in upper or "NEEDS REVIEW" in upper:
            status = "Needs review"

        best_chunk = chunks[0] if chunks else None

        return ControlResult(
            control_id=control["control_id"],
            category=control["category"],
            requirement=control["requirement"],
            status=status,
            reason=answer.strip(),
            confidence=0.7,
            source_excerpt=best_chunk["text"][:500] if best_chunk else None,
            source_file=best_chunk["source"] if best_chunk else None,
            source_page=best_chunk.get("page_number") if best_chunk else None,
        )
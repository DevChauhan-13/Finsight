from typing import Dict, Any, List, Optional

class MemoryFormatter:
    """
    Formats recalled memories and reflection summaries for downstream consumption
    by the AI Agent, Streamlit Dashboard, and Rich CLI.
    Enforces clear epistemic separation between deterministic facts and historical context.
    """
    @staticmethod
    def format_recalled_cases_for_prompt(memories: List[Dict[str, Any]]) -> str:
        if not memories:
            return "NO PRIOR HISTORICAL MEMORIES FOUND IN HINDSIGHT FOR THIS EXCEPTION TYPE."

        formatted_lines = [f"FOUND {len(memories)} RELEVANT HISTORICAL EXCEPTION EXPERIENCES IN HINDSIGHT:"]
        for idx, mem in enumerate(memories, 1):
            text = mem.get("text", "").strip()
            mem_id = mem.get("id", f"case_{idx}")
            formatted_lines.append(f"\n[Historical Memory #{idx} (Ref: {mem_id})]")
            formatted_lines.append(text)

        return "\n".join(formatted_lines)

    @staticmethod
    def format_reflection_for_prompt(reflection_text: str) -> str:
        if not reflection_text or "no prior" in reflection_text.lower():
            return "NO AGGREGATED MENTAL MODEL / REFLECTION AVAILABLE."
        return f"SYNTHESIZED HISTORICAL PATTERN (Hindsight Reflect):\n{reflection_text.strip()}"

    @staticmethod
    def parse_recalled_items(memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parses memory records into clean UI-ready dictionaries."""
        parsed = []
        for mem in memories:
            text = mem.get("text", "")
            lines = text.split("\n")
            meta = {}
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    k = parts[0].strip().replace("-", "").strip().lower()
                    v = parts[1].strip()
                    meta[k] = v
            parsed.append({
                "id": mem.get("id", ""),
                "summary": meta.get("discrepancy category", "Discrepancy"),
                "outcome": meta.get("resolution outcome", "Resolved"),
                "evidence": meta.get("supporting evidence submitted", "Standard"),
                "full_text": text,
                "tags": mem.get("tags", [])
            })
        return parsed

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class ConflictResolver:
    LAYER_PRIORITY = settings.LAYER_PRIORITY

    def resolve(self, chunks: List[Dict]) -> Tuple[List[Dict], Optional[str]]:
        if not chunks:
            return chunks, None
        conflicts = self._detect_conflicts(chunks)
        if not conflicts:
            return self._sort(chunks), None
        resolved, note = self._apply_resolution(chunks, conflicts)
        logger.info("conflict_resolved", conflict_count=len(conflicts), note=note)
        return self._sort(resolved), note

    def _sort(self, chunks: List[Dict]) -> List[Dict]:
        return sorted(
            chunks,
            key=lambda chunk: (
                self.LAYER_PRIORITY.get(chunk.get("source_layer", "SOP"), 99),
                -(chunk.get("rerank_score", chunk.get("fused_score", 0.0))),
            ),
        )

    def _detect_conflicts(self, chunks: List[Dict]) -> List[Dict]:
        topics: dict[str, list[dict]] = {}
        for chunk in chunks:
            key = chunk.get("section_no") or chunk.get("clause_no") or chunk.get("heading") or chunk["id"]
            topics.setdefault(key, []).append(chunk)
        conflicts = []
        for topic, group in topics.items():
            layers = {item.get("source_layer") for item in group}
            if len(layers) > 1:
                conflicts.append({"topic": topic, "chunks": group, "layers": list(layers)})
        return conflicts

    def _apply_resolution(self, chunks: List[Dict], conflicts: List[Dict]) -> Tuple[List[Dict], str]:
        downranked_ids = set()
        notes: list[str] = []
        for conflict in conflicts:
            layers = conflict["layers"]
            topic = conflict["topic"]
            best_layer = min(layers, key=lambda layer: self.LAYER_PRIORITY.get(layer, 99))
            worst_layer = max(layers, key=lambda layer: self.LAYER_PRIORITY.get(layer, 99))
            if "SOP" in layers and best_layer != "SOP":
                for chunk in conflict["chunks"]:
                    if chunk.get("source_layer") == "SOP":
                        downranked_ids.add(chunk["id"])
                notes.append(f"Topic {topic}: SOP guidance conflicts with {best_layer}. Regulatory source preferred.")
            elif best_layer != worst_layer:
                for chunk in conflict["chunks"]:
                    if chunk.get("source_layer") != best_layer:
                        downranked_ids.add(chunk["id"])
                notes.append(f"Topic {topic}: {best_layer} overrides {worst_layer} per immutable hierarchy.")
        result = []
        tail = []
        for chunk in chunks:
            row = dict(chunk)
            if row["id"] in downranked_ids:
                row["_downranked"] = True
                row["fused_score"] = row.get("fused_score", 0.0) * 0.3
                tail.append(row)
            else:
                result.append(row)
        result.extend(tail)
        return result, " | ".join(notes)


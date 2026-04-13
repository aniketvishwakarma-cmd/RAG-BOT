from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import func

from app.core.config import settings
from app.db.models import Chunk, GraphRelation
from app.db.session import SessionLocal, init_db
from app.graph.entity_extractor import EntityExtractor


BATCH_SIZE = 10
EXTRACTION_MODEL = "gpt-4o-mini"
MAX_CHARS_PER_CHUNK = 4000

SYSTEM_PROMPT = """
You extract a knowledge graph from RBI/CIBIL compliance text.

Return valid JSON with this shape:
{
  "entities": [
    {"label": "RBI", "type": "regulator"},
    {"label": "CICRA 2005", "type": "act"}
  ],
  "relations": [
    {"source": "RBI", "target": "CICRA 2005", "relation": "governs"}
  ]
}

Rules:
- Keep only high-signal entities from the chunk.
- Prefer entity types: regulator, act, section, process, timeline, penalty, entity, document.
- Keep relation labels short and action-oriented.
- Only emit relations when both entities appear in the chunk.
- Deduplicate entities and relations.
- Return JSON only.
""".strip()


@dataclass
class ChunkGraph:
    chunk_id: str
    document_id: str | None
    entities: list[dict[str, str]]
    relations: list[dict[str, str]]


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return normalized or "unknown"


def entity_id(label: str, entity_type: str) -> str:
    return f"{entity_type}:{slugify(label)}"


def normalize_entity(entity: dict[str, Any]) -> dict[str, str] | None:
    label = str(entity.get("label") or entity.get("text") or "").strip()
    entity_type = str(entity.get("type") or entity.get("label_type") or entity.get("label") or "entity").strip().lower()
    if not label:
        return None
    return {
        "id": entity_id(label, entity_type),
        "label": label,
        "type": entity_type,
    }


def normalize_relation(relation: dict[str, Any], entity_lookup: dict[str, dict[str, str]]) -> dict[str, str] | None:
    source_label = str(relation.get("source") or "").strip()
    target_label = str(relation.get("target") or "").strip()
    relation_name = str(relation.get("relation") or "related_to").strip().lower().replace(" ", "_")
    if not source_label or not target_label or source_label == target_label:
        return None

    source = entity_lookup.get(source_label.lower())
    target = entity_lookup.get(target_label.lower())
    if not source or not target:
        return None

    return {
        "source_id": source["id"],
        "target_id": target["id"],
        "source_type": source["type"],
        "target_type": target["type"],
        "relation": relation_name or "related_to",
    }


def fallback_extract(chunk_id: str, document_id: str | None, content: str) -> ChunkGraph:
    extractor = EntityExtractor()
    raw_entities = extractor.extract(content)
    entities: list[dict[str, str]] = []
    seen_entities: set[str] = set()

    type_map = {
        "SOURCE": "document",
        "TIMELINE": "timeline",
        "CONSUMER_PENALTY": "penalty",
        "REGULATOR_PENALTY": "penalty",
    }

    for raw in raw_entities:
        label = str(raw.get("text") or "").strip()
        entity_type = type_map.get(str(raw.get("label") or ""), "entity")
        normalized = normalize_entity({"label": label, "type": entity_type})
        if not normalized or normalized["id"] in seen_entities:
            continue
        seen_entities.add(normalized["id"])
        entities.append(normalized)

    relations: list[dict[str, str]] = []
    for index, source in enumerate(entities):
        for target in entities[index + 1 :]:
            relations.append(
                {
                    "source_id": source["id"],
                    "target_id": target["id"],
                    "source_type": source["type"],
                    "target_type": target["type"],
                    "relation": "co_occurs_in_chunk",
                }
            )

    return ChunkGraph(chunk_id=chunk_id, document_id=document_id, entities=entities, relations=relations)


async def extract_chunk_graph(client: AsyncOpenAI, chunk_id: str, document_id: str | None, content: str) -> ChunkGraph:
    prompt = (
        f"Chunk ID: {chunk_id}\n"
        "Extract the entity graph from this chunk.\n\n"
        f"{content[:MAX_CHARS_PER_CHUNK]}"
    )

    try:
        response = await client.chat.completions.create(
            model=EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=900,
        )
        payload = json.loads(response.choices[0].message.content or "{}")
    except Exception:
        return fallback_extract(chunk_id, document_id, content)

    entities: list[dict[str, str]] = []
    seen_entities: set[str] = set()
    entity_lookup: dict[str, dict[str, str]] = {}

    for raw in payload.get("entities", []):
        normalized = normalize_entity(raw)
        if not normalized or normalized["id"] in seen_entities:
            continue
        seen_entities.add(normalized["id"])
        entities.append(normalized)
        entity_lookup[normalized["label"].lower()] = normalized

    relations: list[dict[str, str]] = []
    seen_relations: set[tuple[str, str, str]] = set()
    for raw in payload.get("relations", []):
        normalized = normalize_relation(raw, entity_lookup)
        if not normalized:
            continue
        key = (normalized["source_id"], normalized["target_id"], normalized["relation"])
        if key in seen_relations:
            continue
        seen_relations.add(key)
        relations.append(normalized)

    if not relations and len(entities) >= 2:
        for index, source in enumerate(entities):
            for target in entities[index + 1 :]:
                relations.append(
                    {
                        "source_id": source["id"],
                        "target_id": target["id"],
                        "source_type": source["type"],
                        "target_type": target["type"],
                        "relation": "co_occurs_in_chunk",
                    }
                )

    return ChunkGraph(chunk_id=chunk_id, document_id=document_id, entities=entities, relations=relations)


async def process_batch(client: AsyncOpenAI, chunks: list[Chunk]) -> list[ChunkGraph]:
    tasks = [
        extract_chunk_graph(
            client=client,
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content or "",
        )
        for chunk in chunks
    ]
    return await asyncio.gather(*tasks)


async def main() -> None:
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required to build graph relations.")

    init_db()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    db = SessionLocal()

    try:
        total_chunks = db.query(func.count(Chunk.id)).scalar() or 0
        existing_edges = {
            (row.source_id, row.target_id, row.relation or "related_to")
            for row in db.query(GraphRelation).all()
        }

        inserted = 0
        processed = 0

        for offset in range(0, total_chunks, BATCH_SIZE):
            batch = (
                db.query(Chunk)
                .order_by(Chunk.created_at.asc())
                .offset(offset)
                .limit(BATCH_SIZE)
                .all()
            )
            if not batch:
                break

            graphs = await process_batch(client, batch)
            new_rows: list[GraphRelation] = []

            for graph in graphs:
                entity_by_id = {entity["id"]: entity for entity in graph.entities}
                for relation in graph.relations:
                    key = (
                        relation["source_id"],
                        relation["target_id"],
                        relation["relation"],
                    )
                    if key in existing_edges:
                        continue
                    existing_edges.add(key)

                    source_entity = entity_by_id.get(relation["source_id"], {})
                    target_entity = entity_by_id.get(relation["target_id"], {})

                    new_rows.append(
                        GraphRelation(
                            source_id=relation["source_id"],
                            target_id=relation["target_id"],
                            source_type=relation["source_type"],
                            target_type=relation["target_type"],
                            relation=relation["relation"],
                            confidence=0.85,
                            metadata_json={
                                "chunk_id": graph.chunk_id,
                                "document_id": graph.document_id,
                                "source_label": source_entity.get("label", relation["source_id"]),
                                "target_label": target_entity.get("label", relation["target_id"]),
                            },
                        )
                    )

            if new_rows:
                db.add_all(new_rows)
                db.commit()
                inserted += len(new_rows)

            processed += len(batch)
            print(
                f"Processed {processed}/{total_chunks} chunks "
                f"({min(offset + BATCH_SIZE, total_chunks)} total in scanned batches). "
                f"Inserted {inserted} graph relations so far."
            )

        print(f"Done. Inserted {inserted} new graph_relations rows.")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

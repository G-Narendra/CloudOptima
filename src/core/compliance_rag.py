"""
The AI Architect Panel — Compliance RAG Engine

Hybrid approach:
1. Hardcoded ComplianceRule objects (primary) — curated, accurate, no hallucination
2. Vector DB fallback (secondary) — for countries/regions not yet in the hardcoded set

The vector store is seeded with the existing hardcoded rules so ALL lookups
go through a unified interface. When new regulations need to be added,
you can either write a new ComplianceRule (preferred) or upload documents
to the vector store.

Usage:
    from src.core.compliance_rag import hybrid_get_rules
    rules = hybrid_get_rules("brazil")  # Tries hardcoded first, then RAG
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from src.core.models import ComplianceRule

logger = logging.getLogger(__name__)

# ─── Lazy-loaded RAG engine ────────────────────────────────────────────────

_vector_store: Optional[object] = None
_embedder: Optional[object] = None


def _get_embedder():
    """Lazy-load the sentence-transformers model."""
    global _embedder
    if _embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded embedding model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed. RAG fallback disabled.")
            return None
    return _embedder


def _get_vector_store():
    """Lazy-load or create the ChromaDB vector store, seeded with hardcoded rules."""
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    embedder = _get_embedder()
    if embedder is None:
        return None

    try:
        import chromadb
        from chromadb.config import Settings

        db_path = Path(".freebuff/compliance_db")
        db_path.mkdir(parents=True, exist_ok=True)

        client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(anonymized_telemetry=False),
        )

        collection_name = "compliance_rules"
        try:
            collection = client.get_collection(collection_name)
            count = collection.count()
            logger.info(f"Loaded existing vector store with {count} documents")
        except ValueError:
            collection = client.create_collection(collection_name)
            _seed_collection(collection, embedder)
            count = collection.count()
            logger.info(f"Created and seeded vector store with {count} documents")

        _vector_store = collection
        return collection

    except ImportError:
        logger.warning("chromadb not installed. RAG fallback disabled.")
        return None


def _seed_collection(collection, embedder):
    """Seed the vector store with all existing hardcoded compliance rules."""
    from src.core.compliance_rules import get_all_rules
    rules = get_all_rules()

    if not rules:
        logger.warning("No hardcoded rules found to seed the vector store.")
        return

    texts = []
    metadatas = []
    ids = []

    for rule in rules:
        # Create a rich text embedding from the rule's fields
        text = (
            f"Region: {rule.region}. "
            f"Framework: {rule.governing_framework}. "
            f"Constraint type: {rule.constraint_type}. "
            f"Requirement: {rule.constraint_text}. "
            f"Source: {rule.source_citation}. "
            f"Applies to: {', '.join(rule.applies_to_services)}."
        )
        texts.append(text)
        metadatas.append({
            "id": rule.id,
            "region": rule.region,
            "framework": rule.governing_framework,
            "constraint_type": rule.constraint_type,
            "source_citation": rule.source_citation,
        })
        ids.append(rule.id)

    # Embed and add in batches
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        batch_metadatas = metadatas[i : i + batch_size]
        batch_ids = ids[i : i + batch_size]
        embeddings = embedder.encode(batch_texts, show_progress_bar=False).tolist()
        collection.add(
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_metadatas,
            ids=batch_ids,
        )


# ─── Public API ────────────────────────────────────────────────────────────


def hybrid_get_rules(region: str, top_k: int = 5) -> list[ComplianceRule]:
    """Get compliance rules for a region.

    1. Try hardcoded rules first (curated, accurate).
    2. If none found, fall back to vector DB similarity search.
    3. Return empty list if neither source has results.
    """
    region = region.lower().strip()

    # Step 1: Try hardcoded rules (lazy import to avoid circular dependency chain)
    from src.core.compliance_rules import get_rules_for_region as get_hardcoded
    hardcoded = get_hardcoded(region)
    if hardcoded:
        logger.info(f"Found {len(hardcoded)} hardcoded rules for region '{region}'")
        return hardcoded

    # Step 2: Fall back to RAG
    logger.info(f"No hardcoded rules for '{region}'. Trying RAG fallback...")
    rag_rules = _rag_search(region, top_k)
    if rag_rules:
        logger.info(f"RAG returned {len(rag_rules)} rules for region '{region}'")
        return rag_rules

    logger.info(f"No rules found for region '{region}' from any source.")
    return []


def hybrid_get_frameworks(region: str) -> list[str]:
    """Get governing frameworks for a region (hybrid source)."""
    rules = hybrid_get_rules(region)
    return list(set(r.governing_framework for r in rules))


def _rag_search(region: str, top_k: int = 5) -> list[ComplianceRule]:
    """Search the vector store for compliance rules similar to the given region."""
    collection = _get_vector_store()
    embedder = _get_embedder()

    if collection is None or embedder is None:
        return []

    try:
        query_text = f"Data protection and compliance regulations for {region}"
        query_embedding = embedder.encode([query_text]).tolist()[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        rules = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            rules.append(ComplianceRule(
                id=meta.get("id", f"rag_{region}_{i}"),
                region=region,
                governing_framework=meta.get("framework", "Unknown"),
                constraint_type=meta.get("constraint_type", "general"),
                constraint_text=doc[:500],
                source_citation=meta.get("source_citation", "Retrieved via semantic search"),
                applies_to_services=["*"],
            ))
        return rules

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        return []


def add_document(
    region: str,
    framework: str,
    constraint_type: str,
    text: str,
    source_citation: str,
    doc_id: Optional[str] = None,
) -> bool:
    """Add a new compliance document to the vector store.

    Use this to seed new regulations without writing code.
    For production-quality rules, prefer adding ComplianceRule objects
    to compliance_rules.py instead.
    """
    collection = _get_vector_store()
    embedder = _get_embedder()

    if collection is None or embedder is None:
        logger.error("Cannot add document: RAG engine not available.")
        return False

    try:
        # Use text prefix for stable ID (avoid Python's randomized hash())
        text_id = text[:30].replace(" ", "_").replace("\n", "")
        doc_id = doc_id or f"doc_{region}_{constraint_type}_{text_id}"
        embedding = embedder.encode([text]).tolist()[0]
        collection.add(
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "id": doc_id,
                "region": region,
                "framework": framework,
                "constraint_type": constraint_type,
                "source_citation": source_citation,
            }],
            ids=[doc_id],
        )
        logger.info(f"Added document '{doc_id}' to vector store for region '{region}'")
        return True

    except Exception as e:
        logger.error(f"Failed to add document: {e}")
        return False


def list_regions() -> list[str]:
    """List all regions available in the hardcoded rules."""
    from src.core.compliance_rules import get_all_rules
    rules = get_all_rules()
    return sorted(set(r.region for r in rules))

"""
Context Builder Module

Provides controlled context building with:
- Token budget enforcement
- Deduplication
- Source attribution
- Project filtering
- Deterministic ordering

Sized for qwen2.5:7b (32K context), not 128K.
"""

import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("SecondBrain.ContextBuilder")


@dataclass
class ContextChunk:
    """A chunk of context with metadata."""

    content: str
    project_id: str
    file_path: str
    chunk_name: str | None
    similarity: float
    rank: float
    language: str | None = None
    chunk_type: str | None = None
    token_estimate: int = 0


class ContextBuilder:
    """
    Controlled context builder with token budget enforcement.

    Features:
    - Token budget limiting (sized for qwen2.5:7b 32K context)
    - Content deduplication
    - Source attribution
    - Deterministic ordering
    """

    # Default budget for qwen2.5:7b (32K context)
    # Leave room for system prompt and user query
    DEFAULT_TOKEN_BUDGET = 24000

    # Approximate tokens per character (conservative estimate)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        token_budget: int = None,
        source_attribution: bool = True,
        deduplicate: bool = True,
    ):
        """
        Initialize the context builder.

        Args:
            token_budget: Maximum tokens for context (default: 24000 for qwen2.5:7b)
            source_attribution: If True, add source labels to chunks
            deduplicate: If True, remove duplicate content
        """
        self.token_budget = token_budget or self.DEFAULT_TOKEN_BUDGET
        self.source_attribution = source_attribution
        self.deduplicate = deduplicate
        self._seen_hashes: set[str] = set()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses conservative estimate of 4 chars per token.
        """
        if not text:
            return 0
        return len(text) // self.CHARS_PER_TOKEN

    def _content_hash(self, content: str) -> str:
        """Generate a content hash for deduplication."""
        # Normalize whitespace for deduplication
        normalized = re.sub(r"\s+", " ", content.strip())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def build_context(
        self,
        search_results: list[dict],
        max_chunks: int = 50,
        project_filter: str | None = None,
    ) -> str:
        """
        Build context from search results with token budget enforcement.

        Args:
            search_results: List of search result dictionaries
            max_chunks: Maximum number of chunks to include
            project_filter: Optional project ID to filter by

        Returns:
            Formatted context string within token budget
        """
        # Reset dedup state
        self._seen_hashes = set()

        # Convert to ContextChunk objects
        chunks = []
        for r in search_results:
            chunk = ContextChunk(
                content=r.get("content", ""),
                project_id=r.get("project_id", "unknown"),
                file_path=r.get("file_path", "unknown"),
                chunk_name=r.get("chunk_name"),
                similarity=float(r.get("similarity", 0)),
                rank=float(r.get("rank", 0)),
                language=r.get("language"),
                chunk_type=r.get("chunk_type"),
            )
            chunk.token_estimate = self.estimate_tokens(chunk.content)
            chunks.append(chunk)

        # Apply project filter if specified
        if project_filter:
            chunks = [c for c in chunks if c.project_id == project_filter]

        # Sort by rank (lower is better) then similarity (higher is better)
        chunks.sort(key=lambda c: (c.rank, -c.similarity))

        # Build context within budget
        context_parts = []
        total_tokens = 0
        chunks_included = 0

        for chunk in chunks:
            if chunks_included >= max_chunks:
                break

            # Check deduplication
            if self.deduplicate:
                content_hash = self._content_hash(chunk.content)
                if content_hash in self._seen_hashes:
                    continue
                self._seen_hashes.add(content_hash)

            # Check token budget
            # Add overhead for attribution label (approx 20 tokens)
            overhead = 20 if self.source_attribution else 0
            if total_tokens + chunk.token_estimate + overhead > self.token_budget:
                # Try to fit a truncated version
                remaining_tokens = self.token_budget - total_tokens - overhead
                if remaining_tokens > 100:  # Minimum useful chunk size
                    truncated_chars = remaining_tokens * self.CHARS_PER_TOKEN
                    truncated_content = chunk.content[:truncated_chars] + "... [truncated]"
                    chunk.content = truncated_content
                    chunk.token_estimate = remaining_tokens
                else:
                    break

            # Add source attribution if enabled
            if self.source_attribution:
                label = f"[{chunk.project_id}/{chunk.file_path}"
                if chunk.chunk_name:
                    label += f":{chunk.chunk_name}"
                label += "]"
                context_parts.append(f"{label}\n{chunk.content}")
            else:
                context_parts.append(chunk.content)

            total_tokens += chunk.token_estimate + overhead
            chunks_included += 1

        # Log statistics
        logger.debug(
            "Context built: %d chunks, ~%d tokens (budget: %d)",
            chunks_included,
            total_tokens,
            self.token_budget,
        )

        return "\n\n".join(context_parts)

    def get_statistics(self) -> dict:
        """Get statistics about the last build_context call."""
        return {
            "token_budget": self.token_budget,
            "seen_hashes": len(self._seen_hashes),
            "chars_per_token": self.CHARS_PER_TOKEN,
        }


def build_agent_context(
    search_results: list[dict],
    token_budget: int = None,
    source_attribution: bool = True,
    project_filter: str | None = None,
) -> str:
    """
    Convenience function to build context for agent execution.

    Args:
        search_results: Search results from search_brain()
        token_budget: Maximum tokens (default: 24000 for qwen2.5:7b)
        source_attribution: If True, add source labels
        project_filter: Optional project ID to filter by

    Returns:
        Formatted context string
    """
    builder = ContextBuilder(
        token_budget=token_budget,
        source_attribution=source_attribution,
    )
    return builder.build_context(
        search_results,
        project_filter=project_filter,
    )

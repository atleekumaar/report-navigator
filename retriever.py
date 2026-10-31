import re
from typing import List, Dict, Any, Optional, Set, Tuple
import numpy as np

import config
from index import Indexer, tokenize_for_bm25, build_contextual_text


class HybridRetriever:
    def __init__(self, indexer: Optional[Indexer] = None):
        if indexer is None:
            self.indexer = Indexer()
            self.indexer.load()
        else:
            self.indexer = indexer

        self.reranker = None
        if config.USE_RERANK:
            self._init_reranker()

    def _init_reranker(self):
        try:
            from sentence_transformers import CrossEncoder
            print(f"[Retriever] Loading reranker model: {config.RERANK_MODEL_NAME}...")
            self.reranker = CrossEncoder(config.RERANK_MODEL_NAME)
        except Exception as e:
            print(f"[Retriever] Warning: Failed to load cross-encoder ({e}). Reranking will be disabled.")
            self.reranker = None

    def detect_pinned_pages(self, query: str) -> Set[int]:
        """Detect explicit page references in the query, e.g. 'page 45', 'p. 45', 'p45'."""
        pinned = set()
        matches = re.findall(r'\b(?:page|p\.?)\s*(\d{1,4})\b', query, re.IGNORECASE)
        for m in matches:
            pinned.add(int(m))
        return pinned

    def detect_table_references(self, query: str) -> Set[str]:
        """Detect explicit table references in the query, e.g. 'Table 3.1', 'table 5'."""
        refs = set()
        matches = re.findall(r'\btable\s+(\d+(?:\.\d+)?)\b', query, re.IGNORECASE)
        for m in matches:
            refs.add(m)
        return refs

    def search_bm25(self, query: str, top_k: int = config.BM25_TOP_K) -> List[Tuple[int, float]]:
        """Run BM25 search returning list of (chunk_idx, score). Uses synonym expansion."""
        if self.indexer.bm25 is None or not self.indexer.chunks:
            return []
        # Use synonym expansion at query time for better recall
        tokens = tokenize_for_bm25(query, use_synonyms=True)
        if not tokens:
            return []
        scores = self.indexer.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    def search_dense(self, query: str, top_k: int = config.DENSE_TOP_K) -> List[Tuple[int, float]]:
        """Run dense embedding cosine similarity search returning list of (chunk_idx, score)."""
        if not config.USE_DENSE or self.indexer.embeddings is None or len(self.indexer.embeddings) == 0:
            return []
        if self.indexer.embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.indexer.embed_model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
            except Exception as e:
                print(f"[Retriever] Failed to load embedding model: {e}")
                return []

        query_vec = self.indexer.embed_model.encode([query], normalize_embeddings=True)[0]
        # Dot product with normalized vectors equals cosine similarity
        sims = np.dot(self.indexer.embeddings, query_vec)
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(int(idx), float(sims[idx])) for idx in top_indices]

    def rrf_fuse(
        self,
        ranked_lists: List[List[Tuple[int, float]]],
        rrf_k: int = config.RRF_K
    ) -> List[Tuple[int, float]]:
        """
        Merge multiple ranked lists using Reciprocal Rank Fusion:
        RRF_score(chunk) = SUM( 1 / (k + rank) )
        """
        scores: Dict[int, float] = {}
        for ranked in ranked_lists:
            for rank_0, (chunk_idx, _) in enumerate(ranked):
                rank = rank_0 + 1
                scores[chunk_idx] = scores.get(chunk_idx, 0.0) + 1.0 / (rrf_k + rank)

        sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_chunks

    def expand_sibling_tables(
        self,
        candidate_indices: List[int],
        max_extra: int = 3
    ) -> List[int]:
        """
        If a retrieved chunk is part of a multi-part table, include sibling table parts
        to preserve headers and surrounding rows.
        """
        result = list(candidate_indices)
        added_count = 0
        existing_set = set(candidate_indices)

        for idx in candidate_indices:
            if idx >= len(self.indexer.chunks):
                continue
            chunk = self.indexer.chunks[idx]
            table_id = chunk.get("table_id")
            if table_id:
                # Find all siblings in index
                for s_idx, c in enumerate(self.indexer.chunks):
                    if c.get("table_id") == table_id and s_idx not in existing_set:
                        result.append(s_idx)
                        existing_set.add(s_idx)
                        added_count += 1
                        if added_count >= max_extra:
                            return result
        return result

    def retrieve(
        self,
        queries: List[str],
        top_k: int = config.FINAL_TOP_K,
        use_rerank: bool = config.USE_RERANK
    ) -> Dict[str, Any]:
        """
        Execute hybrid search over queries (standalone question + keyword variants).
        Returns a dictionary with top chunks, scores, and trace metadata.
        """
        if not queries:
            return {"chunks": [], "trace": {}}

        if not self.indexer.chunks:
            print("[Retriever] Warning: No chunks loaded.")
            return {"chunks": [], "trace": {"error": "no_chunks_loaded"}}

        primary_query = queries[0]
        pinned_pages = self.detect_pinned_pages(primary_query)
        table_refs = self.detect_table_references(primary_query)

        all_rankings = []
        trace_rankings = {}

        for q in queries:
            bm25_res = self.search_bm25(q, top_k=config.BM25_TOP_K)
            dense_res = self.search_dense(q, top_k=config.DENSE_TOP_K)
            if bm25_res:
                all_rankings.append(bm25_res)
            if dense_res:
                all_rankings.append(dense_res)
            trace_rankings[q] = {
                "bm25_count": len(bm25_res),
                "dense_count": len(dense_res),
                "bm25_top_score": round(bm25_res[0][1], 4) if bm25_res else 0.0,
                "dense_top_score": round(dense_res[0][1], 4) if dense_res else 0.0,
            }

        if not all_rankings:
            # Fallback to returning initial chunks if index exists
            top_candidates = [(i, 0.0) for i in range(min(top_k, len(self.indexer.chunks)))]
        else:
            fused = self.rrf_fuse(all_rankings, rrf_k=config.RRF_K)
            top_candidates = fused[:config.FUSED_POOL_SIZE]

        # Apply page pinning boost if user mentioned explicit pages
        if pinned_pages:
            boosted = []
            for chunk_idx, score in top_candidates:
                chunk = self.indexer.chunks[chunk_idx]
                p_num = chunk.get("page")
                p_label = str(chunk.get("label", ""))
                if p_num in pinned_pages or any(str(p) == p_label for p in pinned_pages):
                    boosted.append((chunk_idx, score + 1.0))
                else:
                    boosted.append((chunk_idx, score))
            top_candidates = sorted(boosted, key=lambda x: x[1], reverse=True)

        # Apply table reference boost
        if table_refs:
            boosted = []
            for chunk_idx, score in top_candidates:
                chunk = self.indexer.chunks[chunk_idx]
                caption = (chunk.get("caption") or "").lower()
                table_id = (chunk.get("table_id") or "").lower()
                for ref in table_refs:
                    if ref in caption or ref in table_id or f"table {ref}" in chunk.get("text", "").lower()[:200]:
                        score += 0.8
                        break
                boosted.append((chunk_idx, score))
            top_candidates = sorted(boosted, key=lambda x: x[1], reverse=True)

        candidate_indices = [idx for idx, _ in top_candidates]

        # Sibling table expansion
        expanded_indices = self.expand_sibling_tables(candidate_indices, max_extra=3)

        # Cross-encoder Reranking
        scored_candidates = []
        if use_rerank and self.reranker is not None and len(expanded_indices) > 0:
            pairs = []
            for idx in expanded_indices:
                chunk = self.indexer.chunks[idx]
                chunk_repr = build_contextual_text(chunk)
                pairs.append((primary_query, chunk_repr))
            try:
                rerank_scores = self.reranker.predict(pairs)
                for idx, score in zip(expanded_indices, rerank_scores):
                    scored_candidates.append((idx, float(score)))
                scored_candidates.sort(key=lambda x: x[1], reverse=True)
                final_indices = [idx for idx, _ in scored_candidates[:top_k]]
            except Exception as e:
                print(f"[Retriever] Reranking failed: {e}. Using RRF scores.")
                final_indices = expanded_indices[:top_k]
                rrf_dict = dict(top_candidates)
                scored_candidates = [(idx, rrf_dict.get(idx, 0.0)) for idx in final_indices]
        else:
            final_indices = expanded_indices[:top_k]
            rrf_dict = dict(top_candidates)
            scored_candidates = [(idx, rrf_dict.get(idx, 0.0)) for idx in final_indices]

        # Coverage quality check
        retrieval_quality = "good"
        if scored_candidates:
            top_score = scored_candidates[0][1]
            if use_rerank and self.reranker is not None:
                if top_score < config.MIN_COVERAGE_RERANK:
                    retrieval_quality = "low"
            else:
                if top_score < config.MIN_COVERAGE_BM25:
                    retrieval_quality = "low"

        # Build output chunk payloads
        final_chunks = []
        for rank, (idx, score) in enumerate(scored_candidates[:top_k]):
            c = dict(self.indexer.chunks[idx])
            c["score"] = round(score, 4)
            c["rank"] = rank + 1
            final_chunks.append(c)

        trace = {
            "queries": queries,
            "pinned_pages": list(pinned_pages),
            "table_refs": list(table_refs),
            "rerank_applied": use_rerank and (self.reranker is not None),
            "total_candidates": len(expanded_indices),
            "retrieval_quality": retrieval_quality,
            "trace_rankings": trace_rankings
        }

        return {
            "chunks": final_chunks,
            "trace": trace
        }

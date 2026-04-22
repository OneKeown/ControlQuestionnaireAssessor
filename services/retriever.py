import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class RetrievalService:
    def retrieve(self, query, chunks, chunk_embeddings, embedding_service, top_k: int = 4):
        query_embedding = embedding_service.embed_query(query)
        scores = cosine_similarity(query_embedding, chunk_embeddings)[0]
        indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in indices:
            results.append({
                "source": chunks[idx].source,
                "page_number": chunks[idx].page_number,
                "text": chunks[idx].text,
                "score": float(scores[idx]),
                "doc_type": chunks[idx].doc_type,
            })
        return results
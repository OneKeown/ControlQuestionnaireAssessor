from models.document_models import DocumentChunk, ExtractedDocument


class ChunkingService:
    def chunk_document(self, document: ExtractedDocument, chunk_size: int = 900, overlap: int = 120):
        chunks = []

        for page in document.pages:
            text = page.text.strip()
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        DocumentChunk(
                            source=document.file_name,
                            page_number=page.page_number,
                            text=chunk_text,
                            doc_type=document.doc_type,
                        )
                    )
                start += max(1, chunk_size - overlap)

        return chunks
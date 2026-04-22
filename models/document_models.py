from pydantic import BaseModel
from typing import Optional, List


class ExtractedPage(BaseModel):
    page_number: int
    text: str


class ExtractedDocument(BaseModel):
    file_name: str
    file_type: str
    pages: List[ExtractedPage]
    full_text: str
    doc_type: Optional[str] = "unknown"


class DocumentChunk(BaseModel):
    source: str
    page_number: Optional[int] = None
    text: str
    doc_type: Optional[str] = "unknown"
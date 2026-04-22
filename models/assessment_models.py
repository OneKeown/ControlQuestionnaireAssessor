from pydantic import BaseModel
from typing import Optional


class CertificateDetails(BaseModel):
    cert_type: Optional[str] = None
    company_name: Optional[str] = None
    issuer: Optional[str] = None
    certificate_number: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 0.0
    

class ControlResult(BaseModel):
    control_id: str
    category: str
    requirement: str
    status: str
    reason: str
    confidence: float = 0.0
    source_excerpt: Optional[str] = None
    source_file: Optional[str] = None
    source_page: Optional[int] = None
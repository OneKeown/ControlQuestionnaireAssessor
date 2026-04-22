import re
from datetime import datetime
from typing import Optional
from models.assessment_models import CertificateDetails


class CertificateService:
    DATE_PATTERNS = [
        r"expiry date[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
        r"valid until[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
        r"valid to[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
        r"expires on[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
        r"expiration date[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
        r"expiry[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"expiry date[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"valid until[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"valid to[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"expires on[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"expiration date[:\s]*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"valid until[:\s]*([A-Za-z]+\s+[0-9]{1,2},\s+[0-9]{4})",
        r"valid to[:\s]*([A-Za-z]+\s+[0-9]{1,2},\s+[0-9]{4})",
        r"expiry date[:\s]*([A-Za-z]+\s+[0-9]{1,2},\s+[0-9]{4})",
        r"expires on[:\s]*([A-Za-z]+\s+[0-9]{1,2},\s+[0-9]{4})",
        r"([0-9]{4}-[0-9]{2}-[0-9]{2})",
    ]

    def extract_expiry_date(self, text: str):
        lowered = text.lower()

        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, lowered)
            if match:
                return match.group(1)

        return None

    def parse_date(self, date_str: str):
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%d",
            "%d/%m/%y",
            "%d-%m-%y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    def assess_certificate(self, text: str, cert_type: Optional[str] = None) -> CertificateDetails:
        expiry = self.extract_expiry_date(text)
        status = "Needs review"
        notes = "Could not confidently identify expiry date"
        confidence = 0.3

        if expiry:
            parsed = self.parse_date(expiry)
            if parsed:
                status = "Fail" if parsed.date() < datetime.today().date() else "Pass"
                notes = "Expiry date extracted automatically"
                confidence = 0.9
            else:
                notes = f"Found possible expiry date '{expiry}' but could not parse it"
                confidence = 0.3

        return CertificateDetails(
            cert_type=cert_type,
            expiry_date=expiry,
            status=status,
            notes=notes,
            confidence=confidence
        )

    def assess_from_chunks(self, chunks, cert_type: Optional[str] = None) -> CertificateDetails:
        for chunk in chunks:
            result = self.assess_certificate(chunk["text"], cert_type)
            if result.expiry_date:
                return result

        combined_text = "\n".join(chunk["text"] for chunk in chunks)
        return self.assess_certificate(combined_text, cert_type)
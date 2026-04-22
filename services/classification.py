class ClassificationService:
    def classify(self, text: str) -> str:
        sample = text.lower()

        if "iso/iec 27001" in sample or "iso 27001" in sample:
            return "ISO 27001 Certificate"
        if "cyber essentials plus" in sample or "ce+" in sample:
            return "Cyber Essentials Plus Certificate"
        if "cyber essentials" in sample:
            return "Cyber Essentials Certificate"
        if "questionnaire" in sample or "yes/no" in sample or "n/a" in sample:
            return "Security Questionnaire"
        return "Unknown"
import os
from openai import OpenAI


class LLMService:
    def __init__(self, model: str = "gpt-5.4-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def answer_question(self, question: str, retrieved_chunks: list[dict]) -> str:
        context = "\n\n".join(
            [
                f"Source: {c['source']} | Page: {c.get('page_number')} | Type: {c.get('doc_type')}\n{c['text']}"
                for c in retrieved_chunks
            ]
        )

        prompt = f"""
        You are answering questions about uploaded security documents.
        Use only the supplied context.
        If the answer is not present, say you could not find it in the uploaded documents.
        Be brief and specific.

        Question:
        {question}

        Context:
        {context}
        """

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        return response.output_text
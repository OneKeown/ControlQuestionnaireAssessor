import streamlit as st
from services.extractors import ExtractorService
from services.chunker import ChunkingService
from services.embedding import EmbeddingService
from services.retriever import RetrievalService
from services.classification import ClassificationService
from services.certificates import CertificateService
from services.llm_assess import LLMService
from services.controls_checker import ControlService
from services.report import ReportService
from utils.highlighter import highlight_terms

import sys
import os
import datetime as dt


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="Security Document Chat", layout="wide")
st.title("Security Document Chat")

extractor = ExtractorService()
chunker = ChunkingService()
classifier = ClassificationService()
cert_service = CertificateService()
st.write(hasattr(cert_service, "assess_from_chunks"))
retrieval = RetrievalService()
control_service = ControlService()
report_service = ReportService()

@st.cache_resource
def get_embedding_service():
    return EmbeddingService()

@st.cache_resource
def get_llm_service():
    return LLMService()

embedder = get_embedding_service()
llm = get_llm_service()

uploaded_files = st.file_uploader(
    "Upload certificates or questionnaires",
    type=["pdf", "txt", "docx", "xlsx", "xlsm"],
    accept_multiple_files=True,
)



if uploaded_files and "prepared" not in st.session_state:
    documents = []
    chunks = []

    with st.spinner("Reading and indexing documents..."):
        for file in uploaded_files:
            doc = extractor.extract(file)
            doc.doc_type = classifier.classify(doc.full_text)
            documents.append(doc)
            chunks.extend(chunker.chunk_document(doc))

        chunk_texts = [c.text for c in chunks]
        chunk_embeddings = embedder.embed_texts(chunk_texts)

        st.session_state["documents"] = documents
        st.session_state["chunks"] = chunks
        st.session_state["chunk_embeddings"] = chunk_embeddings
        st.session_state["prepared"] = True
        st.session_state["messages"] = []

if st.session_state.get("prepared"):
    st.subheader("Loaded documents")
    for doc in st.session_state["documents"]:
        st.write(f"- {doc.file_name} ({doc.doc_type})")
        #if "certificate" in doc.doc_type.lower():
        #    cert_details = cert_service.assess_certificate(doc.full_text, doc.doc_type)
        #    st.caption(f"Expiry: {cert_details.expiry_date or 'Not found'} | Status: {cert_details.status}")

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sources" in msg:
                with st.expander("Sources"):
                    for src in msg["sources"]:
                        st.markdown(
                            f"**{src['source']}** | page {src.get('page_number')} | {src.get('doc_type')} | score {src['score']:.3f}"
                        )
                        st.code(src["text"][:1200])

    
    
    st.subheader("Certificate checks")

    if st.button("Run certificate check"):
        certificate_docs = [
            doc for doc in st.session_state["documents"]
            if "certificate" in doc.doc_type.lower()
        ]

        if not certificate_docs:
            st.warning("No certificate documents found.")
        else:
            for doc in certificate_docs:
                certificate_results = []
                doc_chunks = [
                    c for c in st.session_state["chunks"]
                    if c.source == doc.file_name
                ]

                doc_chunk_texts = [c.text for c in doc_chunks]
                doc_chunk_embeddings = embedder.embed_texts(doc_chunk_texts)

                relevant_chunks = retrieval.retrieve(
                    query="expiry date valid until expiration date certificate expires",
                    chunks=doc_chunks,
                    chunk_embeddings=doc_chunk_embeddings,
                    embedding_service=embedder,
                    top_k=5,
                )

                cert_result = cert_service.assess_from_chunks(
                    relevant_chunks,
                    cert_type=doc.doc_type,
                )
                certificate_results.append({
                    "file_name": doc.file_name,
                    "cert_type": doc.doc_type,
                    "expiry_date": cert_result.expiry_date,
                    "status": cert_result.status,
                    "notes": cert_result.notes,
                    "confidence": cert_result.confidence,
                })
                if not cert_result.expiry_date:
                    llm_prompt = (
                        "What is the expiry date of this certificate? "
                        "Return only the expiry date. "
                        "If you cannot find one, return NOT FOUND."
                    )

                    llm_answer = llm.answer_question(llm_prompt, relevant_chunks).strip()

                    if llm_answer and "NOT FOUND" not in llm_answer.upper():
                        parsed = cert_service.parse_date(llm_answer)
                        if parsed:
                            cert_result.expiry_date = llm_answer
                            cert_result.status = "Fail" if parsed.date() < dt.datetime.today().date() else "Pass"
                            cert_result.notes = "Expiry date found using LLM fallback"
                            cert_result.confidence = 0.7
                        else:
                            cert_result.notes = f"LLM suggested '{llm_answer}' but it could not be parsed"
                            cert_result.confidence = 0.4
                    certificate_results.append({
                        "file_name": doc.file_name,
                        "cert_type": doc.doc_type,
                        "expiry_date": cert_result.expiry_date,
                        "status": cert_result.status,
                        "notes": cert_result.notes,
                        "confidence": cert_result.confidence,
                    })
                st.markdown(f"**{doc.file_name}**")
                st.write(f"Type: {doc.doc_type}")
                st.write(f"Expiry date: {cert_result.expiry_date or 'Not found'}")
                st.write(f"Status: {cert_result.status}")
                st.write(f"Confidence: {cert_result.confidence:.2f}")
                st.caption(cert_result.notes)

                with st.expander(f"Certificate evidence for {doc.file_name}"):
                    for chunk in relevant_chunks:
                        st.markdown(
                            f"Page {chunk.get('page_number')} | score {chunk['score']:.3f}"
                        )
                        st.code(chunk["text"][:1200])
        st.session_state["certificate_results"] = certificate_results
    
    
    
    st.subheader("Control assessment")

    if st.button("Run control assessment"):
        controls = control_service.load_controls()
        st.session_state["controls"] = controls

        questionnaire_chunks = [
            c for c in st.session_state["chunks"]
            if "questionnaire" in (c.doc_type or "").lower()
        ]

        if not questionnaire_chunks:
            st.warning("No questionnaire documents found.")
        else:
            results = []
            result_chunks_map = {}

            for control in controls:
                retrieval_query = " ".join(control.get("question_hints", [])) + " " + control["requirement"]

                question_chunk_texts = [c.text for c in questionnaire_chunks]
                question_chunk_embeddings = embedder.embed_texts(question_chunk_texts)

                relevant_chunks = retrieval.retrieve(
                    query=retrieval_query,
                    chunks=questionnaire_chunks,
                    chunk_embeddings=question_chunk_embeddings,
                    embedding_service=embedder,
                    top_k=4,
                )

                result = control_service.assess_with_llm_fallback(control, relevant_chunks, llm)

                results.append(result)

                result_chunks_map[control["control_id"]] = relevant_chunks

            st.session_state["control_results"] = results
            st.session_state["result_chunks_map"] = result_chunks_map
            overall_summary = control_service.summarise_results(controls, results)
            st.session_state["overall_summary"] = overall_summary
            

        
    control_lookup = {
    c["control_id"]: c for c in st.session_state.get("controls", [])
}
    if "control_results" in st.session_state:
        st.subheader("Assessment results")
        control_lookup = {c["control_id"]: c for c in st.session_state.get("controls", [])}
        for result in st.session_state["control_results"]:
            st.markdown(f"**{result.control_id} — {result.category}**")
            st.write(f"Requirement: {result.requirement}")
            st.write(f"Status: {result.status}")
            st.write(f"Confidence: {result.confidence:.2f}")
            st.write(f"Reason: {result.reason}")
            
            control_def = control_lookup.get(result.control_id, {})

            expected_terms = control_def.get("expected_terms", [])
            fail_terms = control_def.get("fail_terms", [])


            chunks = st.session_state["result_chunks_map"].get(result.control_id, [])
            
            if result.source_file:
                st.caption(f"Source: {result.source_file} | Page: {result.source_page}")

            if result.source_excerpt:
                with st.expander(f"Evidence for {result.control_id}"):
                    st.code(result.source_excerpt)
                    with st.expander(f"Debug for {result.control_id}"):

                        for chunk in chunks:
                            highlighted_html = highlight_terms(
                                chunk["text"],
                                expected_terms=expected_terms,
                                fail_terms=fail_terms,
                            )

                            st.markdown(highlighted_html, unsafe_allow_html=True)

    
        if "overall_summary" in st.session_state:
            summary = st.session_state["overall_summary"]

            st.subheader("Overall Assessment")
            st.write(f"Overall result: **{summary['overall_status']}**")
            st.write(f"Passed: {summary['passed']} / {summary['total']}")
            st.write(f"Failed: {summary['failed']} / {summary['total']}")
            st.write(f"Needs review: {summary['needs_review']} / {summary['total']}")
            st.caption(summary["summary_reason"])
            
        if "overall_summary" in st.session_state and "control_results" in st.session_state:
            report_buffer = report_service.build_docx_report(
                overall_summary=st.session_state["overall_summary"],
                control_results=st.session_state["control_results"],
                certificate_results=st.session_state.get("certificate_results", []),
            )
        with st.expander(f"Debug for {result.control_id}"):
            st.write("Status:", result.status)
            st.write("Confidence:", result.confidence)
            st.write("Reason:", result.reason)
            st.write("Retrieved chunks:")
            st.markdown(
            """
            <div style="margin-bottom:10px;">
                <span style="background-color:#d4edda; padding:2px 6px; border-radius:4px;">Expected term</span>
                &nbsp;
                <span style="background-color:#ffcccc; padding:2px 6px; border-radius:4px;">Fail term</span>
            </div>
            """,
            unsafe_allow_html=True,
)
            for chunk in chunks:
                st.markdown(
                    f"**{chunk['source']}** | page {chunk.get('page_number')} | score {chunk['score']:.3f}"
                )
                highlighted_html = highlight_terms(
                    chunk["text"][:1500],
                    expected_terms=expected_terms,
                    fail_terms=fail_terms,
                )

                st.markdown(highlighted_html, unsafe_allow_html=True)
               

        st.download_button(
            label="Download assessment report (.docx)",
            data=report_buffer,
            file_name="security_controls_assessment_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    prompt = st.chat_input("Ask a question about the uploaded documents")
    
    #debugs panel
    
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})

        relevant = retrieval.retrieve(
            prompt,
            st.session_state["chunks"],
            st.session_state["chunk_embeddings"],
            embedder,
            top_k=4,
        )

        answer = llm.answer_question(prompt, relevant)

        st.session_state["messages"].append(
            {"role": "assistant", "content": answer, "sources": relevant}
        )
        st.rerun()
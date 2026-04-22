import streamlit as st
import plotly.graph_objects as go
import assess as am 



st.write("Upload Control Questionnaire and Certificates:")

uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True, type=["pdf", "docx", "xlsx"])

feedback = st.text_area("Assessment Feedback", key= "feedback_area", placeholder="A description of the assessment will be generated here based on the uploaded files.", height=200)

def on_upper_clicked():
    feedback = am.assess_files(uploaded_files)
    feedback += "\n\n" + am.get_cert_text(uploaded_files)
    feedback+= "\n\n" + am.LLM_assessment(uploaded_files)
    
    st.session_state.feedback_area = feedback
    
question = st.chat_input("Ask a question about the uploaded documents")

st.button("Assess!", on_click=on_upper_clicked)

fig = go.Figure(go.Indicator(
    mode = "gauge+number+delta",
    value = 0,
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': "Overall rating", 'font': {'size': 24}},
    gauge = {
        'axis': {'range': [None, 300], 'tickwidth': 1, 'tickcolor': "darkblue"},
        'bar': {'color': "darkblue"},
        'bgcolor': "white",
        'borderwidth': 2,
        'bordercolor': "gray",
        'steps': [
            {'range': [0, 100], 'color': 'red'},
            {'range': [101, 200], 'color': 'yellow'},
            {'range': [201, 300], 'color': 'green'}],
        'threshold': {
            'line': {'color': "red", 'width': 4},
            'thickness': 0.75,
            'value': 201}}))


feedback = am.assess_files(uploaded_files)

#st.session_state.feedback_area = feedback

fig.update_layout(paper_bgcolor = "lavender", font = {'color': "darkblue", 'family': "Arial"})
st.plotly_chart(fig)
#fig.show()


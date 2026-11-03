import streamlit as st

from ai_analyzer import LANGUAGES, analyze_code
from code_chat import answer_question
from flowchart import generate_flowchart


st.set_page_config(page_title="AI Code Mentor", page_icon="🤖", layout="wide")
st.title("🤖 AI Code Mentor")
st.caption("Understand code with static checks, language-aware diagnostics, and a visual outline.")
st.info("Your code is analyzed as text and is never executed. Static analysis can find syntax errors and suspicious patterns, but cannot prove that a program is correct.")

language_choice = st.selectbox("Programming language", LANGUAGES, help="Auto detect works for common Python, Java, C, and C++ source. Choose a language if detection is ambiguous.")
code = st.text_area("Paste your code here", height=260, placeholder="Paste a Python, Java, C, or C++ program...")

if st.button("Analyze code", type="primary", disabled=not code.strip()):
    st.session_state.analysis = analyze_code(code, language_choice)
    st.session_state.analyzed_code = code

result = st.session_state.get("analysis")
analyzed_code = st.session_state.get("analyzed_code", "")
if result:
    st.divider()
    st.subheader("Analysis summary")
    left, middle, right = st.columns(3)
    left.metric("Language", result["language"])
    middle.metric("Errors", result["errors"])
    right.metric("Warnings", result["warnings"])
    st.write(result["explanation"])
    st.write("**Syntax check:**", result["syntax_status"])
    st.write("**Estimated complexity:**", result["complexity"])

    st.subheader("Findings")
    for finding in result["findings"]:
        label = f"{finding['severity']} · line {finding['line']} · {finding['rule']}"
        body = finding["message"]
        if finding.get("suggestion"):
            body += "\n\nSuggestion: " + finding["suggestion"]
        if finding["severity"] == "Error":
            st.error(label + "\n\n" + body)
        elif finding["severity"] == "Warning":
            st.warning(label + "\n\n" + body)
        else:
            st.info(label + "\n\n" + body)

    st.caption(result["limitations"])
    with st.expander("Show analyzed code"):
        st.code(analyzed_code, language=result["language"].lower().replace("++", "pp"))
    st.subheader("Flowchart outline")
    chart = generate_flowchart(analyzed_code, result["language"])
    if chart:
        try:
            st.graphviz_chart(chart, use_container_width=True)
        except Exception:
            st.code(chart.source, language="dot")

    st.subheader("Ask about this code")
    question = st.text_input("Your question", key="code_question", placeholder="What does this code do? Are there any warnings?")
    if st.button("Ask mentor", disabled=not question.strip()):
        st.write(answer_question(analyzed_code, question, result))


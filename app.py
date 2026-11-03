import streamlit as st

from ai_analyzer import LANGUAGES, analyze_code
from code_chat import answer_question
from flowchart import generate_flowchart


st.set_page_config(page_title="VioletLint", page_icon="🟣", layout="wide")

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp {
      background:
        radial-gradient(ellipse at 12% 0%, rgba(111, 48, 210, .20), transparent 36%),
        radial-gradient(ellipse at 90% 25%, rgba(82, 53, 188, .13), transparent 32%),
        #0b0917;
      color: #f5f1ff;
    }
    [data-testid="stHeader"] { background: rgba(11, 9, 23, .72); }
    [data-testid="stMainBlockContainer"] { max-width: 1480px; padding-top: 2.3rem; }
    [data-testid="stSidebar"] { background: #100d20; border-right: 1px solid #28223f; }
    h1, h2, h3 { color: #f6f0ff !important; letter-spacing: -.025em; }
    p, label, [data-testid="stCaptionContainer"] { color: #bcb5ce; }
    .brandbar { display:flex; align-items:center; gap:14px; margin: 0 0 8px; }
    .brandmark { width:42px; height:42px; border-radius:14px; display:grid; place-items:center;
      background:linear-gradient(145deg,#b18cff,#762fff); box-shadow:0 0 28px #8f48ff55;
      color:white; font-size:20px; font-weight:800; }
    .brandname { font-size:27px; font-weight:750; color:#fff; line-height:1.1; }
    .brandtag { color:#a89dbd; font-size:13px; margin-top:4px; }
    .statuspill { margin-left:auto; border:1px solid #3d315b; border-radius:999px; padding:7px 12px;
      color:#cbb8ff; background:#18122a; font-size:12px; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background:rgba(19,16,35,.86); border-color:#302746; border-radius:18px; }
    [data-testid="stTextArea"] textarea { background:#0d0b19; color:#e9e2fa; border:1px solid #332a4a;
      border-radius:12px; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }
    [data-testid="stTextArea"] textarea:focus { border-color:#9560ff; box-shadow:0 0 0 1px #9560ff; }
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div { background:#151126; border-color:#352b4e; border-radius:10px; }
    div.stButton > button[kind="primary"] { color:#fff; border:0; border-radius:11px;
      background:linear-gradient(100deg,#a14cff,#7138e8); font-weight:700; min-height:44px;
      box-shadow:0 7px 22px #7f3cff33; }
    div.stButton > button[kind="primary"]:hover { border:0; background:linear-gradient(100deg,#b169ff,#8050f5); }
    div.stButton > button:not([kind="primary"]) { color:#d9ceef; border:1px solid #3b3152; border-radius:10px; background:#171328; }
    [data-testid="stMetric"] { background:#151126; border:1px solid #302746; padding:12px 14px; border-radius:13px; }
    [data-testid="stMetricLabel"] { color:#aaa0bf; }
    [data-testid="stMetricValue"] { color:#eee8ff; }
    [data-testid="stAlert"] { border-radius:12px; }
    hr { border-color:#2a233d; }
    code { color:#d5b6ff !important; }
    @media (max-width: 800px) { [data-testid="stMainBlockContainer"] { padding:1.2rem 1rem; }
      .statuspill { display:none; } }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="brandbar"><div class="brandmark">V</div><div><div class="brandname">VioletLint</div>'
    '<div class="brandtag">A calmer place to understand and review code</div></div>'
    '<div class="statuspill">PYTHON · JAVA · C · C++</div></div>',
    unsafe_allow_html=True,
)
st.write("")

editor, review = st.columns([1.65, 1], gap="large")

with editor:
    with st.container(border=True):
        st.subheader("Code editor")
        st.caption("Paste a snippet to inspect it. VioletLint analyzes source text and never executes your code.")
        code = st.text_area(
            "Code to review",
            height=370,
            label_visibility="collapsed",
            placeholder="Paste Python, Java, C, or C++ code here...",
            key="source_code",
        )
        analyze_clicked = st.button("✦  Analyze code", type="primary", use_container_width=True, disabled=not code.strip())

with review:
    with st.container(border=True):
        st.subheader("Review settings")
        language_choice = st.selectbox("Language", LANGUAGES, key="language_choice")
        review_mode = st.selectbox("Review mode", ("Full review", "Syntax only"), key="review_mode")
        st.caption("Full review checks syntax and selected suspicious patterns. Syntax only shows parser errors when available.")
        st.markdown("---")
        st.markdown("**Supported languages**")
        st.caption("Python · Java · C · C++")
        st.caption("Static checks can miss bugs. Review the code and use a compiler or test suite before relying on it.")

if analyze_clicked:
    st.session_state.analysis = analyze_code(code, language_choice)
    st.session_state.analyzed_code = code

result = st.session_state.get("analysis")
analyzed_code = st.session_state.get("analyzed_code", "")

if result:
    st.write("")
    findings = result["findings"]
    if st.session_state.get("review_mode") == "Syntax only":
        findings = [item for item in findings if item["rule"].startswith("syntax.") or item["rule"] == "parser.unavailable"]
        if not findings:
            findings = [{"severity": "Info", "line": 1, "rule": "syntax.status", "message": result["syntax_status"], "suggestion": ""}]
    shown_errors = sum(item["severity"] == "Error" for item in findings)
    shown_warnings = sum(item["severity"] == "Warning" for item in findings)

    with st.container(border=True):
        st.subheader("Analysis results")
        language_col, syntax_col, error_col, warning_col = st.columns(4)
        language_col.metric("Language", result["language"])
        syntax_col.metric("Syntax", result["syntax_status"])
        error_col.metric("Errors", shown_errors)
        warning_col.metric("Warnings", shown_warnings)
        st.write(result["explanation"])
        st.write("**Estimated complexity:**", result["complexity"])

        st.markdown("#### Findings")
        for finding in findings:
            title = f"{finding['severity']} · line {finding['line']} · {finding['rule']}"
            body = finding["message"]
            if finding.get("suggestion"):
                body += "\n\nSuggestion: " + finding["suggestion"]
            if finding["severity"] == "Error":
                st.error(title + "\n\n" + body)
            elif finding["severity"] == "Warning":
                st.warning(title + "\n\n" + body)
            else:
                st.info(title + "\n\n" + body)

        st.caption(result["limitations"])
        with st.expander("View code and flowchart"):
            code_language = {"Python": "python", "Java": "java", "C": "c", "C++": "cpp"}.get(result["language"], "text")
            st.code(analyzed_code, language=code_language)
            chart = generate_flowchart(analyzed_code, result["language"])
            try:
                st.graphviz_chart(chart, use_container_width=True)
            except Exception:
                st.code(chart.source, language="dot")

    with st.container(border=True):
        st.subheader("Ask VioletLint")
        question = st.text_input("Ask about this review", placeholder="For example: What does the warning mean?", key="code_question")
        if st.button("Ask", disabled=not question.strip()):
            st.write(answer_question(analyzed_code, question, result))


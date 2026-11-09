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
        radial-gradient(ellipse at 8% 4%, rgba(133, 65, 246, .20), transparent 30%),
        radial-gradient(ellipse at 95% 18%, rgba(84, 70, 218, .15), transparent 27%),
        radial-gradient(ellipse at 50% 70%, rgba(46, 25, 92, .12), transparent 40%),
        #090812;
      color: #f6f3ff;
    }
    [data-testid="stHeader"] { background: rgba(9, 8, 18, .68); }
    [data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 1.6rem 2.2rem 4rem; }
    [data-testid="stSidebar"] { background: #100e1b; border-right: 1px solid #282239; }
    .brandbar { display:flex; align-items:center; gap:12px; margin:0 0 26px; }
    .brandmark { width:40px; height:40px; border-radius:13px; display:grid; place-items:center;
      background:linear-gradient(145deg,#d2b7ff,#873dff 68%,#6331d7); box-shadow:0 0 25px #9c5cff50;
      color:white; font-size:19px; font-weight:850; }
    .brandname { font:750 20px/1.1 'Segoe UI Variable','Segoe UI',system-ui,sans-serif; letter-spacing:-.04em; color:#fff; }
    .brandmeta { margin-top:4px; color:#928ba5; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
    .topbadge { margin-left:auto; border:1px solid #39304f; border-radius:999px; padding:8px 12px;
      color:#c9b5ff; background:#151222; font-size:11px; letter-spacing:.07em; }
    .hero { position:relative; overflow:hidden; min-height:285px; padding:38px 42px; border-radius:28px;
      border:1px solid rgba(196,169,255,.19);
      background:linear-gradient(116deg,rgba(43,29,70,.97),rgba(20,17,36,.96) 60%,rgba(18,16,32,.94));
      box-shadow:0 24px 75px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.06); }
    .hero:before { content:''; position:absolute; width:330px; height:330px; right:7%; top:-135px; border-radius:50%;
      background:radial-gradient(circle,rgba(154,92,255,.31),rgba(112,61,230,.11) 44%,transparent 70%); }
    .hero:after { content:''; position:absolute; width:210px; height:210px; right:10%; bottom:-155px; border-radius:50%;
      border:1px solid rgba(196,169,255,.18); box-shadow:0 0 0 22px rgba(196,169,255,.025),0 0 0 44px rgba(196,169,255,.02); }
    .hero-inner { position:relative; z-index:1; max-width:760px; }
    .eyebrow { display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border:1px solid #514073;
      border-radius:999px; background:#1c1630; color:#d2bdff; font-size:10px; font-weight:700;
      letter-spacing:.13em; text-transform:uppercase; }
    .eyedot { width:7px; height:7px; border-radius:50%; background:#b28aff; box-shadow:0 0 12px #ae7cff; }
    .hero-title { margin:20px 0 12px; color:#fff; font:750 clamp(36px,5.1vw,64px)/1.02 'Segoe UI Variable','Segoe UI',system-ui,sans-serif;
      letter-spacing:-.065em; }
    .hero-title span { background:linear-gradient(95deg,#e5d6ff 2%,#be91ff 48%,#8d65ff 95%);
      -webkit-background-clip:text; background-clip:text; color:transparent; }
    .hero-copy { max-width:650px; margin:0; color:#bcb3cf; font-size:15px; line-height:1.72; }
    .hero-actions { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-top:24px; }
    a.hero-cta { display:inline-flex; align-items:center; gap:11px; padding:11px 17px; border-radius:11px;
      background:linear-gradient(100deg,#a85cff,#7138e7); box-shadow:0 8px 24px #8b4cff35;
      color:white !important; font-weight:700; text-decoration:none !important; }
    a.hero-cta:hover { filter:brightness(1.12); }
    .hero-note { color:#958ca8; font-size:12px; }
    .metric-row { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:16px 0 30px; }
    .metric-tile { min-height:76px; padding:16px 18px; border:1px solid #2d273d; border-radius:16px;
      background:linear-gradient(145deg,rgba(24,21,38,.95),rgba(15,13,25,.9)); }
    .metric-num { color:#dac7ff; font:700 19px/1.1 'Segoe UI Variable','Segoe UI',system-ui,sans-serif; letter-spacing:-.03em; }
    .metric-label { margin-top:7px; color:#8f899f; font-size:11px; letter-spacing:.07em; text-transform:uppercase; }
    .section-kicker { margin-bottom:7px; color:#ae8cff; font-size:10px; font-weight:750; letter-spacing:.15em; text-transform:uppercase; }
    h1,h2,h3 { color:#f8f5ff !important; letter-spacing:-.035em; }
    p,label,[data-testid="stCaptionContainer"] { color:#aaa3bb; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background:rgba(17,15,29,.89); border-color:#302a42; border-radius:19px; }
    [data-testid="stTextArea"] textarea { background:#0c0b14; color:#eee8fa; border:1px solid #38314a;
      border-radius:13px; font:13px/1.65 'Cascadia Code','Consolas','SFMono-Regular',monospace; }
    [data-testid="stTextArea"] textarea:focus { border-color:#a171ff; box-shadow:0 0 0 1px #a171ff; }
    div[data-baseweb="select"] > div { background:#151222 !important; border-color:#3a324e !important; border-radius:10px !important; }
    div[data-baseweb="select"] input,div[data-baseweb="select"] span { color:#eee8fa !important; }
    div[role="listbox"] { background:#151222 !important; border:1px solid #3a324e !important; }
    div[role="option"] { background:#151222 !important; color:#eee8fa !important; }
    div[role="option"]:hover { background:#28203c !important; }
    div.stButton > button[kind="primary"] { color:#fff; border:0; border-radius:11px;
      background:linear-gradient(100deg,#a85cff,#7138e7); font-weight:750; min-height:45px;
      box-shadow:0 8px 24px #8b4cff35; }
    div.stButton > button[kind="primary"]:hover { border:0; filter:brightness(1.12); }
    div.stButton > button:not([kind="primary"]) { color:#d8ccef; border:1px solid #3b3350; border-radius:10px; background:#171423; }
    [data-testid="stMetric"] { background:#151222; border:1px solid #302a42; padding:13px 15px; border-radius:14px; }
    [data-testid="stMetricLabel"] { color:#aaa0bf; }
    [data-testid="stMetricValue"] {
      color:#e9ddff;
      font-size:1.25rem !important;
      line-height:1.35 !important;
      font-weight:600 !important;
      white-space:normal !important;
      overflow-wrap:anywhere;
    }
    [data-testid="stMetricValue"] > div {
      font-size:inherit !important;
      line-height:inherit !important;
      white-space:normal !important;
      overflow-wrap:anywhere;
    }
    [data-testid="stMetric"] { min-width:0; }
    [data-testid="stAlert"] { border-radius:12px; }
    hr { border-color:#2c263b; }
    code { color:#d8bcff !important; }
    @media(max-width:780px) { [data-testid="stMainBlockContainer"]{padding:1.1rem 1rem 3rem;}
      .hero{padding:28px 24px; min-height:260px;} .hero-inner{max-width:100%;} .hero:before,.hero:after{right:-90px;}
      .metric-row{grid-template-columns:1fr;} .topbadge{display:none;} }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="brandbar"><div class="brandmark">V</div><div><div class="brandname">VioletLint</div>'
    '<div class="brandmeta">Your code review studio</div></div>'
    '<div class="topbadge">PYTHON &nbsp;·&nbsp; JAVA &nbsp;·&nbsp; C &nbsp;·&nbsp; C++</div></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<section class="hero"><div class="hero-inner">'
    '<div class="eyebrow"><span class="eyedot"></span> A smarter way to review code</div>'
    '<div class="hero-title">Make your next line<br>of code <span>make sense.</span></div>'
    '<p class="hero-copy">Catch syntax issues, spot suspicious patterns, and understand complexity—all in one calm workspace built for learning.</p>'
    '<div class="hero-actions"><a class="hero-cta" href="#workspace">Open the workspace <span>↘</span></a>'
    '<span class="hero-note">Your code is analyzed as text and never executed.</span></div>'
    '</div></section>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="metric-row">'
    '<div class="metric-tile"><div class="metric-num">04</div><div class="metric-label">Languages supported</div></div>'
    '<div class="metric-tile"><div class="metric-num">Clear</div><div class="metric-label">Line-by-line findings</div></div>'
    '<div class="metric-tile"><div class="metric-num">Safe</div><div class="metric-label">No code execution</div></div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<div id="workspace"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-kicker">Your workspace</div>', unsafe_allow_html=True)
editor, review = st.columns([1.65, 1], gap="large")

with editor:
    with st.container(border=True):
        st.subheader("Code editor")
        st.caption("Paste a snippet and choose how you want it reviewed.")
        code = st.text_area(
            "Code to review",
            height=330,
            label_visibility="collapsed",
            placeholder="Paste Python, Java, C, or C++ code here...",
            key="source_code",
        )
        analyze_clicked = st.button("✦  Analyze my code", type="primary", use_container_width=True, disabled=not code.strip())

with review:
    with st.container(border=True):
        st.subheader("Review settings")
        language_choice = st.selectbox("Language", LANGUAGES, key="language_choice")
        review_mode = st.selectbox("Review mode", ("Full review", "Syntax only"), key="review_mode")
        st.caption("Full review checks syntax and selected suspicious patterns. Syntax only shows parser errors when available.")
        st.markdown("---")
        st.markdown("**What you’ll get**")
        st.caption("Syntax status · likely issues · complexity estimate · flowchart outline")
        st.caption("Static checks can miss bugs. Review findings and use a compiler or test suite before relying on code.")

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

        complexity_col, space_col = st.columns(2)
        complexity_col.metric("Estimated time complexity", result.get("time_complexity", result["complexity"]))
        space_col.metric("Estimated auxiliary space", result.get("space_complexity", "Not estimated"))

        for optimization in result.get("optimizations", []):
            with st.container(border=True):
                st.markdown("#### Optimization idea")
                st.write(optimization["title"])
                st.caption(optimization["detail"])
                if optimization.get("example"):
                    st.code(optimization["example"], language={"Python": "python", "Java": "java", "C": "c", "C++": "cpp"}.get(result["language"], "text"))

        st.markdown("#### Findings")
        for finding in findings:
            title = f"{finding['severity']} · line {finding['line']} · {finding['rule']}"
            body = finding["message"]
            if finding.get("suggestion"):
                body += "\n\nSuggestion: " + finding["suggestion"]
            if finding.get("replacement"):
                body += "\n\nSuggested replacement:"
            if finding["severity"] == "Error":
                st.error(title + "\n\n" + body)
            elif finding["severity"] == "Warning":
                st.warning(title + "\n\n" + body)
            else:
                st.info(title + "\n\n" + body)
            if finding.get("replacement"):
                st.code(finding["replacement"], language={"Python": "python", "Java": "java", "C": "c", "C++": "cpp"}.get(result["language"], "text"))

        st.caption(result["limitations"])
        with st.expander("View code and flowchart"):
            code_language = {"Python": "python", "Java": "java", "C": "c", "C++": "cpp"}.get(result["language"], "text")
            st.code(analyzed_code, language=code_language)
            chart = generate_flowchart(analyzed_code, result["language"])
            try:
                st.graphviz_chart(chart, use_container_width=False)
            except Exception:
                st.code(chart.source, language="dot")

    with st.container(border=True):
        st.subheader("Ask VioletLint")
        question = st.text_input("Ask about this review", placeholder="For example: What does the warning mean?", key="code_question")
        if st.button("Ask", disabled=not question.strip()):
            st.write(answer_question(analyzed_code, question, result))


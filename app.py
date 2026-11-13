import streamlit as st

from ai_analyzer import LANGUAGES, analyze_code, detect_language
from code_chat import answer_question
from flowchart import generate_flowchart
from sandbox_runner import SandboxError, run_code


st.set_page_config(page_title="VioletLint", page_icon="🔷", layout="wide")

st.markdown(
    """
    <style>
    :root { color-scheme: dark; }
    .stApp {
      background:
        radial-gradient(ellipse at 8% 4%, rgba(42, 190, 230, .18), transparent 30%),
        radial-gradient(ellipse at 95% 18%, rgba(48, 126, 220, .16), transparent 27%),
        radial-gradient(ellipse at 50% 70%, rgba(24, 92, 132, .12), transparent 40%),
        #070c14;
      color: #edf7ff;
    }
    [data-testid="stHeader"] { background: rgba(7, 12, 20, .76); }
    [data-testid="stMainBlockContainer"] { max-width: 1440px; padding: 1.6rem 2.2rem 4rem; }
    [data-testid="stSidebar"] { background: #0b1220; border-right: 1px solid #1d2b3d; }
    .brandbar { display:flex; align-items:center; gap:12px; margin:0 0 26px; }
    .brandmark { width:40px; height:40px; border-radius:13px; display:grid; place-items:center;
      background:linear-gradient(145deg,#b8f0ff,#258cc7 68%,#145e9a); box-shadow:0 0 25px #45c8f255;
      color:white; font-size:19px; font-weight:850; }
    .brandname { font:750 20px/1.1 'Segoe UI Variable','Segoe UI',system-ui,sans-serif; letter-spacing:-.04em; color:#fff; }
    .brandmeta { margin-top:4px; color:#8ba2b8; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
    .topbadge { margin-left:auto; border:1px solid #273d52; border-radius:999px; padding:8px 12px;
      color:#a9e9ff; background:#0d1724; font-size:11px; letter-spacing:.07em; }
    .hero { position:relative; overflow:hidden; min-height:285px; padding:38px 42px; border-radius:28px;
      border:1px solid rgba(120,209,255,.20);
      background:linear-gradient(116deg,rgba(14,37,58,.98),rgba(13,22,36,.96) 60%,rgba(10,19,31,.94));
      box-shadow:0 24px 75px rgba(0,0,0,.24), inset 0 1px rgba(255,255,255,.06); }
    .hero:before { content:''; position:absolute; width:330px; height:330px; right:7%; top:-135px; border-radius:50%;
      background:radial-gradient(circle,rgba(53,195,235,.25),rgba(37,126,205,.11) 44%,transparent 70%); }
    .hero:after { content:''; position:absolute; width:210px; height:210px; right:10%; bottom:-155px; border-radius:50%;
      border:1px solid rgba(120,209,255,.18); box-shadow:0 0 0 22px rgba(120,209,255,.025),0 0 0 44px rgba(120,209,255,.02); }
    .hero-inner { position:relative; z-index:1; max-width:760px; }
    .eyebrow { display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border:1px solid #25546d;
      border-radius:999px; background:#0e2234; color:#bcefff; font-size:10px; font-weight:700;
      letter-spacing:.13em; text-transform:uppercase; }
    .eyedot { width:7px; height:7px; border-radius:50%; background:#54d7ef; box-shadow:0 0 12px #54d7ef; }
    .hero-title { margin:20px 0 12px; color:#fff; font:750 clamp(36px,5.1vw,64px)/1.02 'Segoe UI Variable','Segoe UI',system-ui,sans-serif;
      letter-spacing:-.065em; }
    .hero-title span { background:linear-gradient(95deg,#c4f6ff 2%,#56c7ec 48%,#4d9cff 95%);
      -webkit-background-clip:text; background-clip:text; color:transparent; }
    .hero-copy { max-width:650px; margin:0; color:#b5c9d7; font-size:15px; line-height:1.72; }
    .hero-actions { display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-top:24px; }
    a.hero-cta { display:inline-flex; align-items:center; gap:11px; padding:11px 17px; border-radius:11px;
      background:linear-gradient(100deg,#29c5dc,#176fd1); box-shadow:0 8px 24px #16a8d84d;
      color:white !important; font-weight:700; text-decoration:none !important; }
    a.hero-cta:hover { filter:brightness(1.12); }
    .hero-note { color:#8ea5b9; font-size:12px; }
    .metric-row { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin:16px 0 30px; }
    .metric-tile { min-height:76px; padding:16px 18px; border:1px solid #263b4e; border-radius:16px;
      background:linear-gradient(145deg,rgba(14,26,40,.95),rgba(9,18,29,.92)); }
    .metric-num { color:#bdecff; font:700 19px/1.1 'Segoe UI Variable','Segoe UI',system-ui,sans-serif; letter-spacing:-.03em; }
    .metric-label { margin-top:7px; color:#8197ab; font-size:11px; letter-spacing:.07em; text-transform:uppercase; }
    .section-kicker { margin-bottom:7px; color:#58c5ec; font-size:10px; font-weight:750; letter-spacing:.15em; text-transform:uppercase; }
    h1,h2,h3 { color:#f1f8ff !important; letter-spacing:-.035em; }
    p,label,[data-testid="stCaptionContainer"] { color:#a5bacb; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background:rgba(12,23,36,.90); border-color:#283e52; border-radius:19px; }
    [data-testid="stTextArea"] textarea { background:#08111c; color:#e8f6ff; border:1px solid #2b4157;
      border-radius:13px; font:13px/1.65 'Cascadia Code','Consolas','SFMono-Regular',monospace; }
    [data-testid="stTextArea"] textarea:focus { border-color:#38c3e6; box-shadow:0 0 0 1px #38c3e6; }
    div[data-baseweb="select"] > div { background:#0d1724 !important; border-color:#2b4359 !important; border-radius:10px !important; }
    div[data-baseweb="select"] input,div[data-baseweb="select"] span { color:#e8f6ff !important; }
    div[role="listbox"] { background:#0d1724 !important; border:1px solid #2b4359 !important; }
    div[role="option"] { background:#0d1724 !important; color:#e8f6ff !important; }
    div[role="option"]:hover { background:#19354b !important; }
    div.stButton > button[kind="primary"] { color:#fff; border:0; border-radius:11px;
      background:linear-gradient(100deg,#29c5dc,#176fd1); font-weight:750; min-height:45px;
      box-shadow:0 8px 24px #16a8d84d; }
    div.stButton > button[kind="primary"]:hover { border:0; filter:brightness(1.12); }
    div.stButton > button:not([kind="primary"]) { color:#beeafa; border:1px solid #314b62; border-radius:10px; background:#102033; }
    [data-testid="stMetric"] { background:#0d1724; border:1px solid #283e52; padding:13px 15px; border-radius:14px; }
    [data-testid="stMetricLabel"] { color:#9cb1c4; }
    [data-testid="stMetricValue"] {
      color:#e5f7ff;
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
    hr { border-color:#293d52; }
    code { color:#8be1ff !important; }
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
    '<span class="hero-note">Reviews stay static. Optional runs use an isolated Judge0 sandbox.</span></div>'
    '</div></section>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="metric-row">'
    '<div class="metric-tile"><div class="metric-num">04</div><div class="metric-label">Languages supported</div></div>'
    '<div class="metric-tile"><div class="metric-num">Clear</div><div class="metric-label">Line-by-line findings</div></div>'
    '<div class="metric-tile"><div class="metric-num">Optional</div><div class="metric-label">Sandboxed code runs</div></div>'
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
        st.caption("Run sends this code to Judge0 to compile and execute it in a sandbox. Don’t run private code or secrets.")
        run_clicked = st.button("▶  Run code in sandbox", use_container_width=True, disabled=not code.strip())

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
        with st.expander("Program input (stdin)"):
            program_input = st.text_area("Input passed to your program", height=100, key="program_stdin", placeholder="Optional input, for example: 5")

if analyze_clicked:
    st.session_state.analysis = analyze_code(code, language_choice)
    st.session_state.analyzed_code = code

if run_clicked:
    run_language = detect_language(code, language_choice)
    if run_language not in {"Python", "Java", "C", "C++"}:
        st.session_state.run_result = None
        st.error("Choose Python, Java, C, or C++ before running this code.")
    else:
        try:
            try:
                rapidapi_key = st.secrets.get("JUDGE0_RAPIDAPI_KEY", "")
                default_url = "https://judge0-ce.p.rapidapi.com" if rapidapi_key else "https://ce.judge0.com"
                api_url = st.secrets.get("JUDGE0_API_URL", default_url)
                api_token = st.secrets.get("JUDGE0_AUTH_TOKEN", "")
                rapidapi_host = st.secrets.get("JUDGE0_RAPIDAPI_HOST", "judge0-ce.p.rapidapi.com")
            except Exception:
                api_url, api_token, rapidapi_key = "https://ce.judge0.com", "", ""
                rapidapi_host = "judge0-ce.p.rapidapi.com"
            with st.spinner(f"Running {run_language} in the Judge0 sandbox…"):
                run_result = run_code(
                    code, run_language, program_input, api_url=api_url,
                    api_token=api_token, rapidapi_key=rapidapi_key,
                    rapidapi_host=rapidapi_host,
                )
            st.session_state.run_result = {
                "result": run_result,
                "code": code,
                "language": run_language,
            }
        except SandboxError as exc:
            st.session_state.run_result = None
            st.error(str(exc))

saved_run = st.session_state.get("run_result")
if saved_run and saved_run.get("code") == code and saved_run.get("language") == detect_language(code, language_choice):
    run_result = saved_run["result"]
    with st.container(border=True):
        st.subheader("Program output")
        run_status = run_result.get("status_description", "Finished")
        st.caption(f"{saved_run['language']} · {run_status} · sandboxed run")
        if run_result.get("compile_output"):
            st.error("Compilation error")
            st.code(run_result["compile_output"], language="text")
        if run_result.get("stderr"):
            st.warning("Program error output (stderr)")
            st.code(run_result["stderr"], language="text")
        if run_result.get("stdout"):
            st.markdown("**Output (stdout)**")
            st.code(run_result["stdout"], language="text")
        elif not run_result.get("compile_output") and not run_result.get("stderr"):
            if run_status == "Accepted":
                st.info("The program finished without printing output.")
            else:
                st.error(f"The program did not finish successfully: {run_status}.")
        if run_result.get("message"):
            st.caption(run_result["message"])
        if run_result.get("time") is not None:
            st.caption(f"Runtime: {run_result['time']} s · Memory: {run_result.get('memory', 'n/a')} KB")

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


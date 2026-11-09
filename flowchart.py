import re
import textwrap

from graphviz import Digraph


CONTROL = re.compile(r"\b(if|elif|else|for|while|switch|case|try|catch|return|break|continue)\b")


def _short_label(source: str, width: int = 30, max_lines: int = 2) -> str:
    """Wrap a source line into a small, readable Graphviz label."""
    cleaned = re.sub(r"\s+", " ", source).strip()
    if len(cleaned) > width * max_lines:
        cleaned = cleaned[: width * max_lines - 1].rstrip() + "…"
    return "\\n".join(textwrap.wrap(cleaned, width=width, break_long_words=True, break_on_hyphens=False))


def generate_flowchart(code: str, language: str = "Python") -> Digraph:
    """Create a compact program outline, not a compiler control-flow graph."""
    graph = Digraph(format="svg")
    graph.attr(
        rankdir="TB",
        size="6,4!",
        ratio="compress",
        pad="0.10",
        nodesep="0.22",
        ranksep="0.28",
        bgcolor="transparent",
        fontname="Arial",
        fontsize="10",
    )
    graph.attr("node", shape="box", style="rounded,filled", fillcolor="#eef4ff",
               color="#c4cfe3", fontname="Arial", fontsize="9", margin="0.12,0.07")
    graph.attr("edge", color="#8a96b0", arrowsize="0.65", penwidth="1")
    graph.node("start", "START", shape="oval", fillcolor="#d7f5e5", width="0.9", height="0.35")

    previous = "start"
    count = 0
    max_steps = 8
    for line_number, raw in enumerate(code.splitlines(), 1):
        line = raw.strip()
        if not line or line in {"{", "}", "};"} or line.startswith(("#", "//", "/*", "*")):
            continue
        if CONTROL.search(line) or count < 4:
            node = f"step{count}"
            label = f"L{line_number}  ·  {_short_label(line)}"
            is_control = bool(CONTROL.search(line))
            graph.node(node, label, fillcolor="#e9ddff" if is_control else "#eef4ff")
            graph.edge(previous, node)
            previous = node
            count += 1
            if count >= max_steps:
                break

    if count == 0:
        graph.node("empty", "No code steps to show", fillcolor="#eef4ff")
        graph.edge(previous, "empty")
        previous = "empty"
    elif any(line.strip() for line in code.splitlines()[line_number:]):
        graph.node("more", "More steps omitted", fillcolor="#f3efff", fontsize="8")
        graph.edge(previous, "more", style="dashed")
        previous = "more"

    graph.node("end", "END", shape="oval", fillcolor="#ffe2df", width="0.9", height="0.35")
    graph.edge(previous, "end")
    return graph

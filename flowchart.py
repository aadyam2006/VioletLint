import re

from graphviz import Digraph


def generate_flowchart(code: str, language: str = "Python") -> Digraph:
    """Create a compact control-flow outline; this is not a compiler CFG."""
    graph = Digraph(format="svg")
    graph.attr(rankdir="TB", node_attr={"shape": "box", "style": "rounded,filled", "fillcolor": "#eef4ff"})
    graph.node("start", "Start", shape="oval", fillcolor="#d7f5e5")
    previous = "start"
    count = 0
    control = re.compile(r"\b(if|else|elif|for|while|switch|case|try|catch|return|break|continue)\b")
    for line_number, raw in enumerate(code.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", "//", "/*", "*")):
            continue
        if control.search(line) or (count < 6 and len(line) < 100):
            node = f"n{count}"
            label = f"L{line_number}: {line[:72]}"
            graph.node(node, label)
            graph.edge(previous, node)
            previous = node
            count += 1
        if count >= 14:
            break
    graph.node("end", "End", shape="oval", fillcolor="#ffe2df")
    graph.edge(previous, "end")
    return graph

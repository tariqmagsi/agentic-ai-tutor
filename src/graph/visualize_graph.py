from pathlib import Path
from typing import Optional


def visualize_langgraph_app(app, out_png: str = "agentic_graph.png") -> Optional[str]:
    """
    Visualize a compiled LangGraph app using LangGraph's built-in rendering helpers.

    Returns:
        Path to PNG file if PNG rendering is supported, else None.
    """
    g = app.get_graph()

    # 1) Print Mermaid diagram (built-in, if present)
    mermaid = None
    if hasattr(g, "draw_mermaid"):
        mermaid = g.draw_mermaid()
    elif hasattr(g, "to_mermaid"):
        mermaid = g.to_mermaid()

    if mermaid:
        print("\n=== Mermaid diagram (from LangGraph) ===\n")
        print(mermaid)

    # 2) Render PNG using built-in function if available
    # Most recent LangGraph versions expose draw_mermaid_png()
    png_bytes = None
    if hasattr(g, "draw_mermaid_png"):
        try:
            png_bytes = g.draw_mermaid_png()
        except TypeError:
            # Some versions require parameters; try defaults if needed
            png_bytes = g.draw_mermaid_png()

    # 3) Save PNG if we got bytes
    if png_bytes:
        out_path = Path(out_png)
        out_path.write_bytes(png_bytes)
        print(f"\nSaved graph PNG to: {out_path.resolve()}")
        return str(out_path.resolve())

    print("\nPNG rendering not available in this LangGraph version. "
          "Mermaid text printed above (if supported).")
    return None
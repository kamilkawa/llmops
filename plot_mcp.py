import base64
import io
import matplotlib
import matplotlib.pyplot as plt
from fastmcp import FastMCP

mcp = FastMCP("Visualization")


@mcp.tool(description="Create a line plot from given data and return it as a base64-encoded PNG.")
def line_plot(data, title=None, x_label=None, y_label=None, legend=False):
    fig, ax = plt.subplots()

    for i, series in enumerate(data):
        ax.plot(series, label="series_%d" % (i + 1))

    if title:
        ax.set_title(title)
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    if legend and len(data) > 1:
        ax.legend()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8003)

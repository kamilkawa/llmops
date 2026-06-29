from datetime import date, datetime
from fastmcp import FastMCP

mcp = FastMCP("Date and time")

@mcp.tool(description='Get current date in the format "Year-Month-Day" (YYYY-MM-DD).')
def get_current_date() -> str:
    return date.today().isoformat()


@mcp.tool(
    description=(
        "Get current date and time in ISO 8601 format (up to seconds), "
        "i.e., YYYY-MM-DDTHH:MM:SS"
    )
)
def get_current_datetime() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


if __name__ == "__main__":
    mcp.run(transport="streamable-http", port=8002)

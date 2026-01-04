import uvicorn
import nest_asyncio
from src.mcp.server.mcp_server import mcp

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "mcp_server:mcp.app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
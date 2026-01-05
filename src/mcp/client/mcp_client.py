import asyncio
from fastmcp import Client
from typing import Dict, Any
import logging
import json
from src.config.config import config

def server_url():
    # Use localhost for client connections instead of 0.0.0.0
    return f"http://localhost:{config.Server.PORT}{config.Server.SSE_PATH}"
        
async def main():
    # Connect to the MCP server
    client = Client(server_url())
    
    # Get system status
    async with client:
        status = await client.call_tool("get_system_status")
        print(status)
    
        # Ingest some documents (replace with your directory)
        # result = await client.call_tool("ingest_documents", {"directory_path": "./documents"})
        # print("Ingestion Result:", result)
        
        # Ask a question
        question = "What is machine learning and how does it differ from traditional programming?"
        response = await client.call_tool("ask_question", {"question": question})
        
        print("\n" + "="*50)
        print("QUESTION:", question)
        print("="*50)
        print("\nANSWER:")
        print(response.data)
        print("\n" + "-"*50)
        print("METADATA:", json.dumps(response.data, indent=2))
        
        # Get store stats
        stats = await client.call_tool("get_store_stats")
        print("\nVECTOR STORE STATS:", stats)

mcp_client=asyncio.run(main())
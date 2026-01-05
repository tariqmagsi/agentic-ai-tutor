import asyncio
from fastmcp import Client, FastMCP
from typing import Dict, Any
import logging
import json

async def main():
    # Connect to the MCP server
    client = Client("http://localhost:8000")
    
    # Get system status
    status = await client.call_tool("get_system_status")
    print("System Status:", status)
    
    # Ingest some documents (replace with your directory)
    # result = await client.call("ingest_documents", {"directory_path": "./documents"})
    # print("Ingestion Result:", result)
    
    # Ask a question
    question = "What is machine learning and how does it differ from traditional programming?"
    response = await client.call_tool_mcp("ask_question", {"question": question})
    
    print("\n" + "="*50)
    print("QUESTION:", question)
    print("="*50)
    print("\nANSWER:")
    print(response.get("answer", "No answer provided"))
    print("\n" + "-"*50)
    print("METADATA:", json.dumps(response.get("metadata", {}), indent=2))
    
    # Get store stats
    stats = await client.call("get_store_stats")
    print("\nVECTOR STORE STATS:", stats)

if __name__ == "__main__":
    asyncio.run(main())
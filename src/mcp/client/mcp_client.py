import asyncio
from fastmcp import Client
from typing import Dict, Any
import logging
import json
from src.config.config import config

def server_url():
    # Use localhost for client connections instead of 0.0.0.0
    return f"http://localhost:{config.Server.PORT}{config.Server.SSE_PATH}"

async def call_tool_safe(client: Client, tool: str, args: Dict[str, Any]):
    """Call MCP tool and safely extract response"""
    try:
        response = await client.call_tool(tool, args)

        if hasattr(response, "data"):
            return response.data
        return response

    except Exception as e:
        return {"error": str(e)}
    
def pretty_print_answer(data: Dict[str, Any]):
    """Nicely format agentic response"""
    if not data:
        print("No response")
        return

    if "error" in data:
        print("❌ Error:", data["error"])
        return

    print("\n🤖 ANSWER:\n")
    print(data.get("answer", ""))

    # Show metadata if exists
    # metadata = data.get("metadata", {})
    # if metadata:
    #     print("\n📊 METADATA:")
    #     print(json.dumps(metadata, indent=2))

    # # Show supporting docs (optional)
    # docs = data.get("supporting_documents", [])
    # if docs:
    #     print(f"\n📚 Supporting Docs ({len(docs)}):")
    #     for i, d in enumerate(docs[:3], 1):
    #         print(f"\n--- Doc {i} ---")
    #         print(d.get("content", "")[:200])


async def chat_loop():
    client = Client(server_url())

    async with client:
        print("\n✅ Connected to MCP server")
        print("Type your question or commands:")
        print("  /exit        -> quit")
        print("  /ingest PATH -> ingest documents")
        print("  /clear       -> clear vector store")
        print("")
        # transcript = await call_tool_safe(
        #             client,
        #             "ingest_youtube_video",
        #             {"video_id": "KywRgZpLb5w"}
        #         )
        # for snippet in transcript:
        #     print(snippet)
        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/exit", "/quit"]:
                print("👋 Exiting...")
                break

            # -------- INGEST --------
            if user_input.startswith("/ingest"):
                path = user_input.replace("/ingest", "").strip()

                if not path:
                    print("⚠️ Please provide a directory path")
                    continue

                result = await call_tool_safe(
                    client,
                    "ingest_documents",
                    {"directory_path": path}
                )

                print("\n📥 Ingestion Result:")
                print(result)
                continue

            # -------- CLEAR --------
            if user_input == "/clear":
                confirm = input("⚠️ Are you sure? (yes/no): ")
                if confirm.lower() == "yes":
                    result = await call_tool_safe(client, "clear_store", {})
                    print(result)
                continue

            if user_input == "/transcript":
                video_id = "KywRgZpLb5w"
                result = await call_tool_safe(
                    client,
                    "ingest_youtube_video",
                    {"video_id": video_id}
                )
                print("\n📥 YouTube Transcript Ingestion Result:")
                print(result)
                continue

            # -------- NORMAL QUESTION --------
            response = await call_tool_safe(
                client,
                "ask_question",
                {"question": user_input}
            )

            pretty_print_answer(response)

# async def main():
#     # Connect to the MCP server
#     client = Client(server_url())
    
#     # Get system status
#     async with client:
#         # Ingest some documents (replace with your directory)
#         # result = await client.call_tool("ingest_documents", {"directory_path": "./data"})
#         # print("Ingestion Result:", result)
        
#         # Ask a question
#         question = "What does stock level contains?"
#         response = await client.call_tool("ask_question", {"question": question})
        
#         print("\n" + "="*50)
#         print("QUESTION:", question)
#         print("="*50)
#         print("\nANSWER:")
#         print(response.data.get("answer"))
#         # print("\n" + "-"*50)
#         # print("METADATA:", json.dumps(response.data, indent=2)['answer'])
        
#         # Get store stats
#         # stats = await client.call_tool("get_store_stats")
#         # print("\nVECTOR STORE STATS:", stats)


mcp_client=asyncio.run(chat_loop())
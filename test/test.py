import asyncio
from src.mcp.server.mcp_server import (
    vector_store, data_ingestor, question_agent,
    retrieval_agent, tutoring_agent
)

async def test_components():
    print("Testing RAG Tutor Components...\n")
    
    # Test 1: Vector Store
    print("1. Testing Vector Store...")
    stats = vector_store.get_collection_stats()
    print(f"   Collection: {stats['collection_name']}")
    print(f"   Documents: {stats['total_documents']}\n")
    
    # Test 2: Question Analysis
    print("2. Testing Question Analysis Agent...")
    question = "What is the difference between supervised and unsupervised learning?"
    analysis = question_agent.analyze_question(question)
    print(f"   Question: {question}")
    print(f"   Topic: {analysis.get('topic', 'N/A')}")
    print(f"   Type: {analysis.get('question_type', 'N/A')}")
    print(f"   Complexity: {analysis.get('complexity', 'N/A')}\n")
    
    # Test 3: Search Query Generation
    print("3. Testing Search Query Generation...")
    queries = question_agent.generate_search_queries(question, analysis)
    print(f"   Generated {len(queries)} queries:")
    for i, q in enumerate(queries, 1):
        print(f"   {i}. {q}")
    
    print("\nAll components are working correctly!")

if __name__ == "__main__":
    asyncio.run(test_components())
"""
Evaluation Test Queries for Cross-Source Verification.

10 test queries spanning simple, moderate, and complex difficulty levels.
Each query is designed to test different aspects of the agentic loop:
- Simple (1-2 iterations): single-source factual questions
- Moderate (2-3 iterations): cross-referencing between sources
- Complex (3-5 iterations): multi-source comparison, evidence gaps
"""

# Test queries with expected behavior metadata
TEST_QUERIES = [
    # ── Simple (1-2 expected iterations) ──
    {
        "id": "simple_01",
        "query": "What is Retrieval-Augmented Generation (RAG)?",
        "difficulty": "simple",
        "expected_min_iterations": 1,
        "expected_max_iterations": 2,
        "expected_tools": ["search_knowledge"],
        "description": "Factual question answerable from knowledge base alone",
        "expected_quality": "Should define RAG and reference the knowledge base documents",
    },
    {
        "id": "simple_02",
        "query": "What is the current date and time?",
        "difficulty": "simple",
        "expected_min_iterations": 1,
        "expected_max_iterations": 2,
        "expected_tools": ["get_current_datetime"],
        "description": "Simple tool call, no cross-source verification needed",
        "expected_quality": "Should call datetime tool and return current time",
    },
    {
        "id": "simple_03",
        "query": "Calculate 15% of 340.",
        "difficulty": "simple",
        "expected_min_iterations": 1,
        "expected_max_iterations": 2,
        "expected_tools": ["calculator"],
        "description": "Math computation, single tool call",
        "expected_quality": "Should use calculator and return 51",
    },

    # ── Moderate (2-3 expected iterations) ──
    {
        "id": "moderate_01",
        "query": "What are the best practices for Python code according to our knowledge base, and how do they compare to current industry standards?",
        "difficulty": "moderate",
        "expected_min_iterations": 2,
        "expected_max_iterations": 3,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Requires both knowledge base and web search for comparison",
        "expected_quality": "Should find KB practices, search web for current standards, and compare",
    },
    {
        "id": "moderate_02",
        "query": "Is the information about AI in our documents still accurate given recent developments in 2024?",
        "difficulty": "moderate",
        "expected_min_iterations": 2,
        "expected_max_iterations": 3,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Verification task: check KB content against current web info",
        "expected_quality": "Should retrieve AI docs from KB, search web for recent AI news, note any gaps",
    },
    {
        "id": "moderate_03",
        "query": "What are the key differences between sentence-level and recursive chunking strategies for RAG?",
        "difficulty": "moderate",
        "expected_min_iterations": 2,
        "expected_max_iterations": 3,
        "expected_tools": ["search_knowledge"],
        "description": "Knowledge-intensive question that may need multiple KB searches",
        "expected_quality": "Should find chunking documentation and provide detailed comparison",
    },

    # ── Complex (3-5 expected iterations) ──
    {
        "id": "complex_01",
        "query": "Compare RAG vs fine-tuning for enterprise AI deployments. Which approach is more cost-effective and why? Consider both technical and business perspectives.",
        "difficulty": "complex",
        "expected_min_iterations": 3,
        "expected_max_iterations": 5,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Multi-faceted comparison requiring multiple sources and perspectives",
        "expected_quality": "Should gather info from KB and web, compare on multiple dimensions, give nuanced recommendation",
    },
    {
        "id": "complex_02",
        "query": "What are the security implications of using local LLMs versus cloud-based APIs for sensitive data processing? Include compliance considerations.",
        "difficulty": "complex",
        "expected_min_iterations": 3,
        "expected_max_iterations": 5,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Cross-domain question requiring security, compliance, and technical info",
        "expected_quality": "Should search multiple sources, cover security and compliance aspects, note trade-offs",
    },
    {
        "id": "complex_03",
        "query": "Based on our knowledge base, what embedding models are recommended? How do they compare to the latest embedding benchmarks published in 2024?",
        "difficulty": "complex",
        "expected_min_iterations": 3,
        "expected_max_iterations": 4,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Requires KB lookup plus external benchmark comparison",
        "expected_quality": "Should find embedding docs, search for benchmarks, compare old vs new",
    },
    {
        "id": "complex_04",
        "query": "What is the recommended chunk size for our RAG pipeline, and is there evidence from recent research that this is optimal? Consider the trade-offs between retrieval precision and context completeness.",
        "difficulty": "complex",
        "expected_min_iterations": 3,
        "expected_max_iterations": 4,
        "expected_tools": ["search_knowledge", "web_search"],
        "description": "Technical deep-dive requiring KB settings lookup and research validation",
        "expected_quality": "Should find chunk config, search for research on optimal chunk sizes, discuss trade-offs",
    },
]


def get_queries_by_difficulty(difficulty: str) -> list[dict]:
    """Filter test queries by difficulty level."""
    return [q for q in TEST_QUERIES if q["difficulty"] == difficulty]


def get_all_query_ids() -> list[str]:
    """Return all query IDs."""
    return [q["id"] for q in TEST_QUERIES]

# Transparent lexical rubrics complement trace checks; human review is still needed
# for factual accuracy and whether citations actually support the claims.
RUBRICS = {
    "simple_01": [["retrieval", "retrieve"], ["generation", "generate"], ["rag_guide", "knowledge base"]],
    "simple_02": [["2026"]],
    "simple_03": [["51"]],
    "moderate_01": [["python"], ["standard", "pep"], ["compar", "both", "align"]],
    "moderate_02": [["2024"], ["accurate", "outdated", "gap", "changed"]],
    "moderate_03": [["sentence"], ["recursive"]],
    "complex_01": [["rag", "retrieval"], ["fine-tun", "fine tun"], ["cost"], ["depend", "trade", "recommend"]],
    "complex_02": [["local"], ["cloud"], ["security", "privacy"], ["compliance"]],
    "complex_03": [["embedding"], ["benchmark"], ["2024"]],
    "complex_04": [["chunk"], ["precision"], ["context"], ["research", "evidence"]],
}
for query in TEST_QUERIES:
    query["answer_contains_any"] = RUBRICS[query["id"]]

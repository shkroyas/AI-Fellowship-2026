# Architecture Diagrams generator
# Run this to generate architecture diagrams using PlantUML/Mermaid

import os

def create_mermaid_diagram():
    diagram = """
    ```mermaid
    graph TD
        User([User]) -->|Web/Mobile| UI[Streamlit UI\nPort 8501]

        subgraph "Frontend Layer"
            UI
        end

        UI -->|REST API| ALB[API Gateway / Load Balancer]

        subgraph "Backend Layer (FastAPI Port 8000)"
            ALB --> RateLimit{Rate Limiter}
            RateLimit -- Allowed --> Router[API Router]
            RateLimit -- Denied --> Error429[429 Error]

            Router --> Cache{LRU Cache}
            Cache -- Hit --> Return[Return Response]
            Cache -- Miss --> RAG[RAG Pipeline]

            RAG --> Ingestion[Document Ingester]
            RAG --> Embed[Sentence-Transformers]
            Embed --> VDB[(ChromaDB)]
            VDB -.->|Context| Prompt[Prompt Builder]

            Router --> Prompt
            Prompt --> Fallback[Fallback Manager]

            Fallback -->|Primary| LLM1[Gemini API]
            Fallback -->|Secondary| LLM2[OpenAI API]
            Fallback -->|Tertiary| LLM3[Local vLLM]

            LLM1 -.-> Tools
            LLM2 -.-> Tools
            LLM3 -.-> Tools

            subgraph "Tools Registry"
                Tools[Tool Executor] --> Calc[Calculator]
                Tools --> Search[Web Search]
                Tools --> Time[Date/Time]
            End
        end

        classDef external fill:#f9f,stroke:#333,stroke-width:2px;
        class LLM1,LLM2 external;
    ```
    """
    with open("architecture/diagram.md", "w") as f:
        f.write("# AI Assistant Architecture\n\n")
        f.write("This diagram illustrates the complete production architecture with middleware, RAG, and tool calling.\n\n")
        f.write(diagram)

if __name__ == "__main__":
    print("Generating architecture diagram...")
    create_mermaid_diagram()
    print("Saved to architecture/diagram.md")

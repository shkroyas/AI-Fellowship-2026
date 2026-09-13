# Week 16 implementation architecture

```mermaid
flowchart TD
    User[User / Streamlit] --> API[POST /chat/agentic]
    API --> Init[Original question + optional initial RAG]
    Init --> Context[Bounded evidence + persistent failure notes]
    Context --> Check{Over compaction threshold?}
    Check -->|Yes| Summary[LLM summary or truncation fallback]
    Check -->|No| Decision[Single-agent model decision]
    Summary --> Decision
    Decision -->|Search / calculate / date| Validate[Validate name and arguments]
    Validate --> Duplicate{Identical successful call?}
    Duplicate -->|No| Tools[Tool registry]
    Duplicate -->|Yes| Evidence[Cached result + choose-next-action guidance]
    Tools --> KB[Knowledge retriever / ChromaDB]
    Tools --> Web[DDGS web search]
    Tools --> Utilities[Calculator / date-time]
    KB --> Evidence
    Web --> Evidence
    Utilities --> Evidence
    Validate -->|Invalid| Evidence
    Evidence --> Limit{Five decision iterations reached?}
    Limit -->|No| Context
    Limit -->|Yes| Incomplete[Incomplete verification response]
    Decision -->|answer| Answer[Answer with source references]
    Decision -->|ask_user| Clarify[Clarification response]
    Decision -->|Provider error| Fallback{Explicit fallback configured?}
    Fallback -->|Yes| Decision
    Fallback -->|No / fallback fails| Error[Error response]
    Answer --> Return[Response + trace + token totals]
    Clarify --> Return
    Error --> Return
    Incomplete --> Return
```

`AgenticLoop` makes at most five decision calls plus occasional compaction calls; an explicitly injected fallback gets one attempt per failed decision. The API initializes a fresh loop for each request. Clarification ends the request; the user resubmits a question with the missing information. There is no persistent conversation/task store.

The existing W15 `/chat` path and production middleware remain separate. This diagram does not imply that agentic requests use the single-pass response cache or fallback manager. The provider identifier `local_vllm` currently selects `LocalTransformersProvider` in the factory; it does not launch a vLLM server.

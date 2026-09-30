"""Document search. Chunks, embeddings (Gemini) and vector search (pgvector) live in the backend;
Agent Core only calls POST /documents/search through BackendClient and never touches the database."""

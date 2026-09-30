"""Document tools. Questions about content go through semantic search in the backend (Gemini
embeddings + pgvector), never by sending whole files to the LLM."""

from typing import Literal

from pydantic import Field

from app.backend.schemas import Document
from app.rag.schemas import RetrievedChunk
from app.schemas.tool import ToolDomain, ToolInput, ToolOutput, ToolRisk
from app.tools.common import ID, Listing, listing
from app.tools.registry import ToolContext, ToolDefinition

NO_RESULTS = "No relevant document content found."


class GetDocumentsIn(ToolInput):
    query: str | None = Field(default=None, max_length=200, description="Filter by file name")
    category: str | None = Field(default=None, max_length=100)
    status: Literal["ready", "processing", "failed"] | None = None


async def get_documents(ctx: ToolContext, args: GetDocumentsIn) -> Listing[Document]:
    page = await ctx.backend.list_documents(q=args.query, category=args.category, status=args.status, page_size=50)
    return listing(page.items, page.total)


class GetDocumentIn(ToolInput):
    document_id: str = ID


async def get_document(ctx: ToolContext, args: GetDocumentIn) -> Document:
    return await ctx.backend.get_document(args.document_id)


class SearchDocumentsIn(ToolInput):
    query: str = Field(min_length=2, max_length=500, description="What to look for in the user's uploaded documents")
    document_ids: list[str] | None = Field(default=None, max_length=20, description="Restrict to these documents")
    limit: int | None = Field(default=None, ge=1, le=10, description="How many passages (default: server setting)")


class SearchResult(ToolOutput):
    query: str
    chunks: list[RetrievedChunk]
    message: str | None = None  # "No relevant document content found." when nothing matched


async def search_documents(ctx: ToolContext, args: SearchDocumentsIn) -> SearchResult:
    # A real backend request; the backend scopes the search to this user's own documents.
    found = await ctx.backend.search_documents(args.query, top_k=args.limit, document_ids=args.document_ids)
    chunks = [
        RetrievedChunk(chunk_id=h.chunk_id, document_id=h.document_id, document_name=h.document_name,
                       page_number=h.page_number, chunk_index=h.chunk_index, text=h.content, score=h.similarity)
        for h in found.results
    ]
    return SearchResult(query=args.query, chunks=chunks,
                        message=None if chunks else (found.message or NO_RESULTS))


TOOLS = [
    ToolDefinition("get_documents", "List the user's uploaded documents (notes, study material, personal and career documents).",
                   ToolDomain.DOCUMENTS, ToolRisk.READ, GetDocumentsIn, Listing[Document], get_documents),
    ToolDefinition("get_document", "Get one document's metadata by ID.", ToolDomain.DOCUMENTS, ToolRisk.READ,
                   GetDocumentIn, Document, get_document),
    ToolDefinition("search_documents", "Semantic search over the user's uploaded documents. Returns the most relevant passages with their source (document name and page). Answer only from these passages and cite the source; if nothing relevant is found, say so.",
                   ToolDomain.DOCUMENTS, ToolRisk.READ, SearchDocumentsIn, SearchResult, search_documents),
]

"""Document processing pipeline: convert → chunk → embed → store."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.doc_processor.converter import DocumentConverter, ConvertedDocument
from src.core.doc_processor.chunker import Chunk, get_chunker


@dataclass
class PipelineResult:
    documents: list[ConvertedDocument]
    chunks: list[Chunk]
    total_files: int
    total_chunks: int
    errors: list[str] = field(default_factory=list)


class DocumentPipeline:
    """Orchestrates document conversion, chunking, and embedding."""

    def __init__(self, chunking_strategy: str = "semantic", chunking_kwargs: dict | None = None):
        self.converter = DocumentConverter()
        self.chunker = get_chunker(chunking_strategy, **(chunking_kwargs or {}))

    def process_file(self, file_path: str) -> list[Chunk]:
        doc = self.converter.convert_file(file_path)
        return self.chunker.chunk(doc.markdown, metadata=doc.metadata)

    def process_directory(self, dir_path: str) -> PipelineResult:
        docs = self.converter.convert_directory(dir_path)
        all_chunks: list[Chunk] = []
        errors: list[str] = []

        for doc in docs:
            try:
                chunks = self.chunker.chunk(doc.markdown, metadata=doc.metadata)
                all_chunks.extend(chunks)
            except Exception as e:
                errors.append(f"{doc.source_path}: {e}")

        return PipelineResult(
            documents=docs,
            chunks=all_chunks,
            total_files=len(docs),
            total_chunks=len(all_chunks),
            errors=errors,
        )

    def process_text(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        return self.chunker.chunk(text, metadata=metadata or {})

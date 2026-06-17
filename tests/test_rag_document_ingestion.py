import asyncio

import pytest

from backend_python.rag_ingestion import (
    IngestionError,
    build_ingestion_preview,
    clean_extracted_text,
    extract_text_from_upload,
    validate_upload_filename,
    validate_upload_size,
)


def test_validate_upload_filename_accepts_text_markdown_and_pdf() -> None:
    assert validate_upload_filename("role.md") == ".md"
    assert validate_upload_filename("notes.txt") == ".txt"
    assert validate_upload_filename("resume.pdf") == ".pdf"


def test_validate_upload_filename_rejects_unknown_type() -> None:
    with pytest.raises(IngestionError) as exc:
        validate_upload_filename("table.xlsx")
    assert "Unsupported file type" in str(exc.value)


def test_validate_upload_size_rejects_empty_content() -> None:
    with pytest.raises(IngestionError) as exc:
        validate_upload_size(b"")
    assert "empty" in str(exc.value).lower()


def test_clean_extracted_text_normalizes_blank_lines_and_spaces() -> None:
    raw = "  FastAPI   Depends\r\n\r\n\r\nRAG\tchunk  "
    assert clean_extracted_text(raw) == "FastAPI Depends\n\nRAG chunk"


def test_build_ingestion_preview_returns_text_and_chunk_stats() -> None:
    text = (
        "第一段内容介绍 FastAPI Depends 在后端项目里如何完成依赖注入和数据库会话管理。\n\n"
        "第二段内容介绍 RAG chunk metadata 如何记录文档来源、岗位标签、章节和权限边界。"
    )
    preview = build_ingestion_preview(text, title="测试文档")
    assert preview["title"] == "测试文档"
    assert preview["textLength"] > 0
    assert preview["chunkCount"] == 2
    assert preview["warnings"] == []


def test_build_ingestion_preview_warns_when_text_is_short() -> None:
    preview = build_ingestion_preview("短文本", title="短文档")
    assert preview["warnings"] == ["文本较短，可能无法形成高质量 RAG 召回。"]


def test_build_ingestion_preview_rejects_empty_text() -> None:
    with pytest.raises(IngestionError) as exc:
        build_ingestion_preview("   ", title="空文档")
    assert "empty text" in str(exc.value).lower()


def test_extract_text_from_txt_upload() -> None:
    text = asyncio.run(extract_text_from_upload(filename="sample.txt", content=b"hello rag"))
    assert text == "hello rag"

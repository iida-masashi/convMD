from unittest.mock import MagicMock, patch

from convmd.core.vector_db import ChromaManager, GeminiEmbeddingFunction, _chunk_text


def test_chunk_text_splits_on_size():
    text = "\n\n".join(["a" * 600, "b" * 600, "c" * 600])
    chunks = _chunk_text(text, max_chunk_size=1000)
    assert len(chunks) == 3
    assert chunks[0] == "a" * 600
    assert chunks[-1] == "c" * 600


def test_chunk_text_merges_small_paragraphs():
    text = "\n\n".join(["short a", "short b", "short c"])
    chunks = _chunk_text(text, max_chunk_size=1000)
    assert len(chunks) == 1
    assert chunks[0] == "short a\n\nshort b\n\nshort c"


def test_chunk_text_empty_string():
    assert _chunk_text("") == []


def test_embedding_function_no_client_returns_zero_vectors():
    with patch("convmd.core.vector_db.get_client", return_value=None):
        fn = GeminiEmbeddingFunction()
        result = [list(v) for v in fn(["hello", "world"])]
        assert result == [[0.0] * 3072, [0.0] * 3072]


def test_embedding_function_success():
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response = MagicMock()
    mock_response.embeddings = [mock_embedding]

    mock_client = MagicMock()
    mock_client.models.embed_content.return_value = mock_response

    with patch("convmd.core.vector_db.get_client", return_value=mock_client):
        fn = GeminiEmbeddingFunction()
        result = [list(v) for v in fn(["hello"])]
        assert result == [[0.1, 0.2, 0.3]]


def test_embedding_function_handles_exception():
    mock_client = MagicMock()
    mock_client.models.embed_content.side_effect = RuntimeError("boom")

    with patch("convmd.core.vector_db.get_client", return_value=mock_client):
        fn = GeminiEmbeddingFunction()
        result = [list(v) for v in fn(["hello"])]
        assert result == [[0.0] * 3072]


def _make_manager(tmp_path):
    with (
        patch("convmd.core.vector_db.chromadb.PersistentClient") as mock_persistent,
        patch("convmd.core.vector_db.GeminiEmbeddingFunction"),
    ):
        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_persistent.return_value = mock_client
        manager = ChromaManager(tmp_path)
        return manager, mock_collection


def test_upsert_document_skips_when_not_configured(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    with patch("convmd.core.vector_db.is_configured", return_value=False):
        manager.upsert_document(tmp_path / "a.md", "some text")
    mock_collection.add.assert_not_called()


def test_upsert_document_extracts_frontmatter_and_adds_chunks(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    text = '---\ntitle: "My Title"\nsource: "https://example.com"\n---\n\nbody content\n'
    with patch("convmd.core.vector_db.is_configured", return_value=True):
        manager.upsert_document(tmp_path / "a.md", text)

    mock_collection.add.assert_called_once()
    _, kwargs = mock_collection.add.call_args
    assert kwargs["metadatas"][0]["title"] == "My Title"
    assert kwargs["metadatas"][0]["original_url"] == "https://example.com"


def test_upsert_document_no_chunks_skips_add(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    with patch("convmd.core.vector_db.is_configured", return_value=True):
        manager.upsert_document(tmp_path / "a.md", "   \n\n  ")
    mock_collection.add.assert_not_called()


def test_search_not_configured_returns_empty(tmp_path):
    manager, _ = _make_manager(tmp_path)
    with patch("convmd.core.vector_db.is_configured", return_value=False):
        assert manager.search("query") == []


def test_search_empty_collection_returns_empty(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    mock_collection.count.return_value = 0
    with patch("convmd.core.vector_db.is_configured", return_value=True):
        assert manager.search("query") == []


def test_search_returns_formatted_results(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    mock_collection.count.return_value = 1
    mock_collection.query.return_value = {
        "documents": [["doc text"]],
        "metadatas": [[{"source": "a.md", "title": "A"}]],
        "distances": [[0.5]],
    }
    with patch("convmd.core.vector_db.is_configured", return_value=True):
        results = manager.search("query", limit=5)

    assert results == [{"document": "doc text", "metadata": {"source": "a.md", "title": "A"}, "distance": 0.5}]


def test_search_handles_query_exception(tmp_path):
    manager, mock_collection = _make_manager(tmp_path)
    mock_collection.count.return_value = 1
    mock_collection.query.side_effect = RuntimeError("boom")
    with patch("convmd.core.vector_db.is_configured", return_value=True):
        assert manager.search("query") == []

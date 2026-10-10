from app.chunker import chunk_text, Chunk


def test_short_text_is_single_chunk():
    chunks = chunk_text("hello world", max_words=50, overlap=10)
    assert chunks == [Chunk(ordinal=0, text="hello world", token_count=2)]


def test_long_text_splits_with_overlap():
    words = " ".join(str(i) for i in range(120))
    chunks = chunk_text(words, max_words=50, overlap=10)
    assert len(chunks) == 3                      # 0-49, 40-89, 80-119
    assert [c.ordinal for c in chunks] == [0, 1, 2]
    assert chunks[0].text.split()[-1] == "49"
    assert chunks[1].text.split()[0] == "40"     # 10-word overlap
    assert chunks[0].token_count == 50


def test_empty_text_yields_no_chunks():
    assert chunk_text("   ", max_words=50, overlap=10) == []

def chunk(text: str, max_words: int = 200, overlap: int = 30) -> list[str]:
    """Split a review into overlapping windows small enough to embed.

    bge-small truncates input at 512 tokens (~1.3 tokens per English word). Reviews have a
    median of 79 words but run up to ~1,300, so long ones would otherwise lose their tail.
    Fixed word windows rather than sentence splitting: reviews are informally punctuated,
    and ~90% fit in one chunk anyway.

    Contract (tests/test_chunk.py):
    - empty or whitespace-only text returns []
    - text of at most max_words words returns a single chunk
    - every chunk has at most max_words words
    - chunks cover every word, in order, and consecutive chunks overlap
    """
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start:start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks

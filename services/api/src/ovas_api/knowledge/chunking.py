"""Split text into overlapping, heading-aware chunks (plan: ~800-token windows, 100 overlap).

Words stand in for tokens (about 0.75 words per token), so the defaults are 600 and 75 words.
Each chunk starts with its Markdown heading path so a retrieved chunk keeps its context.
"""

import re

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def _sections(text: str) -> list[tuple[str, str]]:
    """(heading path, body) for each run of text under a heading."""
    path: list[str] = []
    body: list[str] = []
    out: list[tuple[str, str]] = []

    def close() -> None:
        content = "\n".join(body).strip()
        if content:
            out.append((" > ".join(path), content))
        body.clear()

    for line in text.splitlines():
        m = HEADING.match(line)
        if m:
            close()
            level = len(m.group(1))
            path[:] = path[: level - 1] + [m.group(2)]
        else:
            body.append(line)
    close()
    return out


def chunk_text(text: str, max_words: int = 600, overlap: int = 75) -> list[str]:
    if not 0 <= overlap < max_words:
        raise ValueError("overlap must be smaller than max_words")
    chunks: list[str] = []
    for heading, body in _sections(text):
        words = body.split()
        step = max_words - overlap
        for start in range(0, max(len(words) - overlap, 1), step):
            piece = " ".join(words[start : start + max_words])
            chunks.append(f"{heading}\n{piece}" if heading else piece)
    return chunks

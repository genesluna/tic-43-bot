"""Helper utilities for tests."""


class MockStreamingResponse:
    """Mock de StreamingResponse com suporte a context manager."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._index = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._chunks):
            raise StopIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk

    def close(self):
        pass


def create_mock_stream(chunks):
    """Factory para criar MockStreamingResponse."""
    return MockStreamingResponse(chunks)

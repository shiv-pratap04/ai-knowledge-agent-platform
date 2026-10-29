import psycopg2
import pytest

from app.services.document_store import (
    DatabaseError,
    get_document_for_processing,
    release_document_processing,
)


class FakeCursor:
    def __init__(
        self,
        *,
        lock_acquired=True,
        document=("uploaded_docs/test.pdf", "processing"),
        error=None,
    ):
        self.lock_acquired = lock_acquired
        self.document = document
        self.error = error
        self.last_query = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=None):
        self.last_query = query
        if self.error:
            raise self.error

    def fetchone(self):
        if "pg_try_advisory_lock" in self.last_query:
            return (self.lock_acquired,)
        return self.document


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_claimed_document_is_returned_and_connection_released_later(monkeypatch):
    connection = FakeConnection(FakeCursor())
    monkeypatch.setattr(
        "app.services.document_store.get_db_connection",
        lambda: connection,
    )

    document = get_document_for_processing(42)

    assert document["storage_path"] == "uploaded_docs/test.pdf"
    assert document["connection"] is connection
    assert connection.committed
    assert not connection.closed

    release_document_processing(document)
    assert connection.closed


@pytest.mark.parametrize(
    ("lock_acquired", "document"),
    [
        (False, ("uploaded_docs/test.pdf", "processing")),
        (True, None),
        (True, ("uploaded_docs/test.pdf", "ready")),
    ],
)
def test_unclaimed_document_closes_connection(
    monkeypatch,
    lock_acquired,
    document,
):
    connection = FakeConnection(
        FakeCursor(lock_acquired=lock_acquired, document=document)
    )
    monkeypatch.setattr(
        "app.services.document_store.get_db_connection",
        lambda: connection,
    )

    assert get_document_for_processing(42) is None
    assert connection.closed
    assert not connection.committed


def test_database_error_closes_connection(monkeypatch):
    connection = FakeConnection(FakeCursor(error=psycopg2.Error("query failed")))
    monkeypatch.setattr(
        "app.services.document_store.get_db_connection",
        lambda: connection,
    )

    with pytest.raises(DatabaseError, match="Failed to claim document"):
        get_document_for_processing(42)

    assert connection.closed

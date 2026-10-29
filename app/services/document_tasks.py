import logging
from pathlib import Path

from app.services.celery_app import celery_app
from app.services.document_store import (
    get_document_for_processing,
    mark_document_failed,
    mark_document_ready,
    release_document_processing,
    save_chunks_for_document,
)
from app.services.langchain_ingest import ingest_pdf

logger = logging.getLogger(__name__)


def _task_decorator(*args, **kwargs):
    def decorator(func):
        return func
    return decorator


if celery_app is not None:
    task_decorator = celery_app.task
else:
    task_decorator = _task_decorator


@task_decorator(bind=True, name="documents.process")
def process_document(self, document_id: int):
    """Parse, embed, and persist one document outside the API process."""
    document = get_document_for_processing(document_id)
    if document is None:
        logger.info("Skipping duplicate or missing document task: %s", document_id)
        return {"document_id": document_id, "status": "skipped"}

    try:
        chunks = ingest_pdf(Path(document["storage_path"]))
        stored = save_chunks_for_document(document_id, chunks)
        mark_document_ready(document_id, stored)
        logger.info("Document %s is ready with %s chunks", document_id, stored)
        return {"document_id": document_id, "status": "ready", "chunk_count": stored}
    except Exception as exc:
        logger.exception("Document ingestion failed for %s", document_id)
        mark_document_failed(document_id, str(exc))
        raise
    finally:
        release_document_processing(document)
-- Existing chunks contain 384-dimensional MiniLM vectors and cannot be mixed
-- with the 768-dimensional Google text-embedding-004 vectors.
DELETE FROM chunks;

ALTER TABLE chunks
    ALTER COLUMN embedding TYPE vector(768);
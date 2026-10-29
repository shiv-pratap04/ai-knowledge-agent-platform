DO $$ BEGIN
    CREATE TYPE ticket_category AS ENUM ('IT_SUPPORT', 'NETWORK', 'HARDWARE', 'SOFTWARE', 'ACCESS', 'ACCOUNT', 'OTHER');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE ticket_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE ticket_status AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ticket_number BIGSERIAL NOT NULL UNIQUE,
    ticket_id TEXT GENERATED ALWAYS AS ('TKT-' || ticket_number::text) STORED UNIQUE,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 3 AND 200),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 10 AND 5000),
    category ticket_category NOT NULL DEFAULT 'IT_SUPPORT',
    priority ticket_priority NOT NULL DEFAULT 'MEDIUM',
    status ticket_status NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS tickets_organization_id_idx ON tickets(organization_id);
CREATE INDEX IF NOT EXISTS tickets_created_by_idx ON tickets(created_by);
CREATE INDEX IF NOT EXISTS tickets_status_idx ON tickets(status);
CREATE INDEX IF NOT EXISTS tickets_created_at_idx ON tickets(created_at DESC);

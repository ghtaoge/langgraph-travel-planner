-- LangGraph Travel Planner — Database Schema
-- Run once on fresh PostgreSQL instance

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Conversations table (thread_id = conversation.id)
CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(200) NOT NULL DEFAULT '新对话',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL DEFAULT '',
  thinking_content TEXT,
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_status
  ON conversations(user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
  ON chat_messages(conversation_id, created_at);

-- User profile fields (idempotent for existing databases)
ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS theme VARCHAR(20) NOT NULL DEFAULT 'dark';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users(phone) WHERE phone IS NOT NULL AND phone <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email) WHERE email IS NOT NULL AND email <> '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS verification_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  target_type VARCHAR(10) NOT NULL,
  target VARCHAR(120) NOT NULL,
  purpose VARCHAR(30) NOT NULL,
  code VARCHAR(12) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  consumed_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_verification_codes_lookup
  ON verification_codes(target_type, target, purpose, created_at DESC);

-- Durable Trip aggregate. The JSONB snapshot is confirmed business state;
-- LangGraph checkpoints remain workflow execution state only.
CREATE TABLE IF NOT EXISTS trips (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  title VARCHAR(200) NOT NULL,
  destination VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL,
  current_revision INTEGER NOT NULL CHECK (current_revision >= 1),
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trip_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  base_revision INTEGER NOT NULL CHECK (base_revision >= 0),
  reason VARCHAR(500) NOT NULL,
  patch JSONB NOT NULL,
  snapshot JSONB NOT NULL,
  created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (trip_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_trips_user_updated
  ON trips(user_id, updated_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_trips_user_conversation_unique
  ON trips(user_id, conversation_id) WHERE conversation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trip_revisions_trip_revision
  ON trip_revisions(trip_id, revision DESC);

-- Cache both fresh and expired provider responses. Expired rows support
-- explicit stale-data fallback when an external service is unavailable.
CREATE TABLE IF NOT EXISTS provider_cache (
  cache_key VARCHAR(160) PRIMARY KEY,
  provider VARCHAR(40) NOT NULL,
  data_type VARCHAR(40) NOT NULL,
  payload JSONB NOT NULL,
  fetched_at TIMESTAMPTZ NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_provider_cache_expiry
  ON provider_cache(data_type, expires_at);

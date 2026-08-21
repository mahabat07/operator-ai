"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- enum types ---
    op.execute("""CREATE TYPE auth_provider AS ENUM ('password', 'google');""")
    op.execute("""CREATE TYPE automation_trigger AS ENUM ('task_overdue', 'deadline_approaching', 'waiting_for_overdue', 'meeting_finished', 'weekly_schedule');""")
    op.execute("""CREATE TYPE chat_role AS ENUM ('user', 'assistant', 'system');""")
    op.execute("""CREATE TYPE commitment_status AS ENUM ('open', 'completed', 'cancelled', 'overdue');""")
    op.execute("""CREATE TYPE inbox_source AS ENUM ('manual', 'email', 'meeting', 'slack');""")
    op.execute("""CREATE TYPE inbox_type AS ENUM ('idea', 'task', 'note', 'follow_up', 'reminder', 'message');""")
    op.execute("""CREATE TYPE inbox_status AS ENUM ('unprocessed', 'converted', 'dismissed');""")
    op.execute("""CREATE TYPE knowledge_source_type AS ENUM ('document', 'email', 'meeting_note', 'manual');""")
    op.execute("""CREATE TYPE memory_type AS ENUM ('preference', 'fact', 'decision', 'relationship', 'project_context', 'instruction', 'other');""")
    op.execute("""CREATE TYPE notification_type AS ENUM ('task_overdue', 'deadline_approaching', 'waiting_for_overdue', 'meeting_follow_up', 'weekly_review_ready', 'ai_insight', 'other');""")
    op.execute("""CREATE TYPE opportunity_status AS ENUM ('new', 'exploring', 'pursuing', 'closed', 'dismissed');""")
    op.execute("""CREATE TYPE project_status AS ENUM ('planning', 'active', 'paused', 'completed', 'cancelled');""")
    op.execute("""CREATE TYPE risk_severity AS ENUM ('low', 'medium', 'high', 'critical');""")
    op.execute("""CREATE TYPE risk_status AS ENUM ('open', 'mitigating', 'resolved', 'dismissed');""")
    op.execute("""CREATE TYPE waiting_for_status AS ENUM ('waiting', 'received', 'cancelled', 'overdue');""")
    op.execute("""CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'member');""")
    op.execute("""CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done', 'cancelled');""")
    op.execute("""CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');""")
    op.execute("""CREATE TYPE task_priority_source AS ENUM ('user', 'ai', 'default');""")

    # --- tables (dependency order: users/workspaces first, dependents after) ---
    op.execute("""CREATE TABLE users (
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255), 
	auth_provider auth_provider NOT NULL, 
	google_id VARCHAR(255), 
	avatar_url VARCHAR(500), 
	current_workspace_id UUID, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (google_id)
);""")
    op.execute("""CREATE TABLE workspaces (
	name VARCHAR(255) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);""")
    op.execute("""CREATE TABLE automations (
	workspace_id UUID NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	trigger automation_trigger NOT NULL, 
	action VARCHAR(50) NOT NULL, 
	config JSON, 
	is_active BOOLEAN NOT NULL, 
	last_run_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE calendar_events (
	workspace_id UUID NOT NULL, 
	external_id VARCHAR(255), 
	title VARCHAR(500) NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	attendees VARCHAR[], 
	location VARCHAR(500), 
	notes TEXT, 
	owner_id UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE chat_messages (
	workspace_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role chat_role NOT NULL, 
	content TEXT NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE commitments (
	workspace_id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	related_person VARCHAR(255), 
	deadline DATE, 
	status commitment_status NOT NULL, 
	source_inbox_item_id UUID, 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE inbox_items (
	workspace_id UUID NOT NULL, 
	raw_text TEXT NOT NULL, 
	source inbox_source NOT NULL, 
	type inbox_type, 
	ai_suggestion JSON, 
	status inbox_status NOT NULL, 
	converted_to_type VARCHAR(50), 
	converted_to_id UUID, 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE integration_accounts (
	workspace_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	provider VARCHAR(50) NOT NULL, 
	email VARCHAR(255), 
	access_token TEXT, 
	refresh_token TEXT, 
	token_expires_at TIMESTAMP WITH TIME ZONE, 
	scopes TEXT, 
	last_synced_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE knowledge_chunks (
	workspace_id UUID NOT NULL, 
	source_type knowledge_source_type NOT NULL, 
	source_id VARCHAR(255), 
	title VARCHAR(500) NOT NULL, 
	chunk_text TEXT NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	embedding VECTOR(1536), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);""")
    op.execute("""CREATE TABLE memory_entries (
	workspace_id UUID NOT NULL, 
	type memory_type NOT NULL, 
	content TEXT NOT NULL, 
	related_entity VARCHAR(255), 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE notifications (
	workspace_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	type notification_type NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	body TEXT, 
	related_entity_type VARCHAR(50), 
	related_entity_id UUID, 
	is_read BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE opportunities (
	workspace_id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	status opportunity_status NOT NULL, 
	recommended_action TEXT, 
	source_reference VARCHAR(500), 
	detected_by VARCHAR(20) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);""")
    op.execute("""CREATE TABLE projects (
	workspace_id UUID NOT NULL, 
	name VARCHAR(500) NOT NULL, 
	description TEXT, 
	status project_status NOT NULL, 
	owner_id UUID, 
	business_impact VARCHAR(20), 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(owner_id) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE risks (
	workspace_id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	severity risk_severity NOT NULL, 
	status risk_status NOT NULL, 
	recommended_action TEXT, 
	source_reference VARCHAR(500), 
	detected_by VARCHAR(20) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE
);""")
    op.execute("""CREATE TABLE waiting_for_items (
	workspace_id UUID NOT NULL, 
	title VARCHAR(500) NOT NULL, 
	related_person VARCHAR(255), 
	expected_by DATE, 
	status waiting_for_status NOT NULL, 
	source_inbox_item_id UUID, 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE workspace_members (
	workspace_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role workspace_role NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);""")
    op.execute("""CREATE TABLE meetings (
	workspace_id UUID NOT NULL, 
	calendar_event_id UUID, 
	title VARCHAR(500) NOT NULL, 
	prep_brief TEXT, 
	notes TEXT, 
	extracted_follow_ups VARCHAR[], 
	created_by UUID NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(calendar_event_id) REFERENCES calendar_events (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")
    op.execute("""CREATE TABLE tasks (
	workspace_id UUID NOT NULL, 
	project_id UUID, 
	title VARCHAR(500) NOT NULL, 
	description TEXT, 
	status task_status NOT NULL, 
	priority task_priority NOT NULL, 
	priority_source task_priority_source NOT NULL, 
	priority_score INTEGER, 
	priority_reason TEXT, 
	deadline DATE, 
	depends_on_task_ids UUID[], 
	source_inbox_item_id UUID, 
	assignee_id UUID, 
	created_by UUID NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE CASCADE, 
	FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE SET NULL, 
	FOREIGN KEY(assignee_id) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);""")

    # --- indexes ---
    op.execute("CREATE UNIQUE INDEX ix_users_email ON users (email);")
    op.execute("CREATE INDEX ix_automations_workspace_id ON automations (workspace_id);")
    op.execute("CREATE INDEX ix_calendar_events_workspace_id ON calendar_events (workspace_id);")
    op.execute("CREATE INDEX ix_chat_messages_workspace_id ON chat_messages (workspace_id);")
    op.execute("CREATE INDEX ix_commitments_workspace_id ON commitments (workspace_id);")
    op.execute("CREATE INDEX ix_inbox_items_workspace_id ON inbox_items (workspace_id);")
    op.execute("CREATE INDEX ix_integration_accounts_workspace_id ON integration_accounts (workspace_id);")
    op.execute("CREATE INDEX ix_knowledge_chunks_workspace_id ON knowledge_chunks (workspace_id);")
    op.execute("CREATE INDEX ix_memory_entries_workspace_id ON memory_entries (workspace_id);")
    op.execute("CREATE INDEX ix_notifications_workspace_id ON notifications (workspace_id);")
    op.execute("CREATE INDEX ix_opportunities_workspace_id ON opportunities (workspace_id);")
    op.execute("CREATE INDEX ix_projects_workspace_id ON projects (workspace_id);")
    op.execute("CREATE INDEX ix_risks_workspace_id ON risks (workspace_id);")
    op.execute("CREATE INDEX ix_waiting_for_items_workspace_id ON waiting_for_items (workspace_id);")
    op.execute("CREATE INDEX ix_workspace_members_user_id ON workspace_members (user_id);")
    op.execute("CREATE INDEX ix_workspace_members_workspace_id ON workspace_members (workspace_id);")
    op.execute("CREATE INDEX ix_meetings_workspace_id ON meetings (workspace_id);")
    op.execute("CREATE INDEX ix_tasks_workspace_id ON tasks (workspace_id);")


def downgrade() -> None:
    # --- indexes ---
    op.execute("DROP INDEX IF EXISTS ix_tasks_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_meetings_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_workspace_members_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_workspace_members_user_id")
    op.execute("DROP INDEX IF EXISTS ix_waiting_for_items_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_risks_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_projects_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_opportunities_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_notifications_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_memory_entries_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_integration_accounts_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_inbox_items_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_commitments_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_chat_messages_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_calendar_events_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_automations_workspace_id")
    op.execute("DROP INDEX IF EXISTS ix_users_email")

    # --- tables (reverse dependency order) ---
    op.execute("DROP TABLE IF EXISTS tasks CASCADE")
    op.execute("DROP TABLE IF EXISTS meetings CASCADE")
    op.execute("DROP TABLE IF EXISTS workspace_members CASCADE")
    op.execute("DROP TABLE IF EXISTS waiting_for_items CASCADE")
    op.execute("DROP TABLE IF EXISTS risks CASCADE")
    op.execute("DROP TABLE IF EXISTS projects CASCADE")
    op.execute("DROP TABLE IF EXISTS opportunities CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS memory_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks CASCADE")
    op.execute("DROP TABLE IF EXISTS integration_accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS inbox_items CASCADE")
    op.execute("DROP TABLE IF EXISTS commitments CASCADE")
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS calendar_events CASCADE")
    op.execute("DROP TABLE IF EXISTS automations CASCADE")
    op.execute("DROP TABLE IF EXISTS workspaces CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # --- enum types ---
    op.execute("DROP TYPE IF EXISTS task_priority_source")
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS workspace_role")
    op.execute("DROP TYPE IF EXISTS waiting_for_status")
    op.execute("DROP TYPE IF EXISTS risk_status")
    op.execute("DROP TYPE IF EXISTS risk_severity")
    op.execute("DROP TYPE IF EXISTS project_status")
    op.execute("DROP TYPE IF EXISTS opportunity_status")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS memory_type")
    op.execute("DROP TYPE IF EXISTS knowledge_source_type")
    op.execute("DROP TYPE IF EXISTS inbox_status")
    op.execute("DROP TYPE IF EXISTS inbox_type")
    op.execute("DROP TYPE IF EXISTS inbox_source")
    op.execute("DROP TYPE IF EXISTS commitment_status")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.execute("DROP TYPE IF EXISTS automation_trigger")
    op.execute("DROP TYPE IF EXISTS auth_provider")

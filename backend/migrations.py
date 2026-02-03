from sqlmodel import text
from database import engine
import logging

logger = logging.getLogger(__name__)

def run_migrations():
    """
    Run manual migrations to update the database schema.
    This is a simple alternative to Alembic for this MVP.
    """
    logger.info("Checking for pending database migrations...")
    
    with engine.connect() as conn:
        try:
            # Check if columns exist in usersettings table
            # We use a safe check that works on SQLite and Postgres
            try:
                # Attempt to select the columns. If they fail, they don't exist.
                conn.execute(text("SELECT reflection_time FROM usersettings LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding reflection_time column")
                conn.rollback() # Important! Clear the error state
                conn.execute(text("ALTER TABLE usersettings ADD COLUMN reflection_time VARCHAR DEFAULT '19:00'"))
                conn.commit()
            
            try:
                conn.execute(text("SELECT reflection_reminder_enabled FROM usersettings LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding reflection_reminder_enabled column")
                conn.rollback() 
                conn.execute(text("ALTER TABLE usersettings ADD COLUMN reflection_reminder_enabled BOOLEAN DEFAULT TRUE"))
                conn.commit()

            try:
                conn.execute(text("SELECT updated_at FROM usersettings LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding updated_at column")
                conn.rollback()
                # Create as NULLable first
                conn.execute(text("ALTER TABLE usersettings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()

            try:
                conn.execute(text("SELECT selected_calendars FROM usersettings LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding selected_calendars column")
                conn.rollback()
                conn.execute(text("ALTER TABLE usersettings ADD COLUMN selected_calendars TEXT DEFAULT NULL"))
                conn.commit()
                
            try:
                conn.execute(text("SELECT calendar_events FROM briefing LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding calendar_events column to briefing")
                conn.rollback()
                conn.execute(text("ALTER TABLE briefing ADD COLUMN calendar_events TEXT DEFAULT NULL"))
                conn.commit()

            try:
                conn.execute(text("SELECT type FROM briefing LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Adding type column to briefing")
                conn.rollback()
                conn.execute(text("ALTER TABLE briefing ADD COLUMN type VARCHAR DEFAULT 'daily'"))
                conn.commit()

            # Ensure Habit table exists (handled by SQLModel.create_all usually, but explicit check here doesn't hurt if we want manual control, 
            # though usually create_all is enough for NEW tables. Let's trust create_all for new tables unless I see issues).
            # Actually, let's verify main.py calls create_all.
            
            # If I need to manually create it:
            try:
                conn.execute(text("SELECT id FROM habit LIMIT 1"))
            except Exception:
                logger.info("Applying migration: Creating habit table")
                conn.rollback()
                # Create table manually to be safe if create_all isn't catching it or to avoid race conditions
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS habit (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        description VARCHAR,
                        preferred_time VARCHAR DEFAULT 'any',
                        duration_minutes INTEGER DEFAULT 30,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX IF NOT EXISTS ix_habit_user_id ON habit (user_id);
                """))
                conn.commit()

            logger.info("Migrations completed successfully.")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            conn.rollback()

"""Add voice settings columns to businesses table."""
import psycopg2

conn = psycopg2.connect(
    host="postgres",
    port=5432,
    dbname="ai_receptionist",
    user="ai_receptionist_user",
    password="secure_pg_password_2024",
)
conn.autocommit = True
cur = conn.cursor()

columns = [
    ("tts_provider", "VARCHAR(50) NOT NULL DEFAULT 'openai'"),
    ("elevenlabs_voice_id", "VARCHAR(255)"),
    ("elevenlabs_voice_name", "VARCHAR(255)"),
    ("elevenlabs_voice_preview_url", "TEXT"),
    ("custom_clone_voice_id", "VARCHAR(255)"),
    ("custom_clone_voice_name", "VARCHAR(255)"),
]

for col_name, col_type in columns:
    try:
        cur.execute(f"ALTER TABLE businesses ADD COLUMN {col_name} {col_type};")
        print(f"  ✅ Added column: {col_name}")
    except psycopg2.errors.DuplicateColumn:
        conn.rollback()
        conn.autocommit = True
        print(f"  ⏭  Column already exists: {col_name}")
    except Exception as e:
        conn.rollback()
        conn.autocommit = True
        print(f"  ❌ Error adding {col_name}: {e}")

cur.close()
conn.close()
print("\n✅ Voice columns migration complete")

INSERT INTO tenants (id, name, owner_user_id, plan, tts_provider)
VALUES ('innovation', 'Innovation', 10, 'starter', 'openai')
ON CONFLICT (id) DO UPDATE SET owner_user_id = EXCLUDED.owner_user_id;

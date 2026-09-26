# Render with Supabase PostgreSQL

Only a persistent database is needed for accounts and text conversation history.
New research does not require a Supabase Storage bucket.

1. Create a Supabase project and keep its database password private.
2. In Connect, choose the Session pooler connection string (port 5432).
   Replace the password placeholder, URL-encoding special characters, and add
   `?sslmode=require` if no query string is present.
3. In Render Environment, set `DATABASE_URL` to that connection string.
4. Set `COOKIE_SECURE=true` and `ALLOWED_ORIGINS` to the actual HTTPS site origin.
   Keep your AI provider settings unchanged.
5. Deploy and verify that a saved conversation remains readable after a restart.

FastAPI creates its tables and enables row-level security to prevent public Data
API access. Authentication uses the app's HTTP-only cookie, not Supabase Auth.

PDFs are discarded after extraction. Temporary passages and embeddings are
removed when a conversation closes or expires. Saved history retains question,
result, and conversation text only, and cannot be continued.

## Upgrading an existing installation

Existing research without an active workspace is converted to text history at
startup. Keep `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and
`SUPABASE_STORAGE_BUCKET` configured until legacy stored PDFs have been deleted.
These credentials stay on the server. Cleanup retries when legacy storage is
unavailable; new PDFs are never uploaded to that bucket.

Switching from SQLite to Supabase still starts a separate database; it does not
migrate old SQLite records automatically. An external database preserves text
history through redeployments, but server restarts can still interrupt active jobs.

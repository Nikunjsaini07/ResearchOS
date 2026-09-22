# Render Free with Supabase

Create a free Supabase project. Keep its database password private.

1. In Storage, create a **private** bucket named `papers` (Public bucket off).
2. In Connect, choose the **Session pooler** connection string (port 5432).
   Replace the password placeholder with your database password, URL-encoding
   special characters. Add `?sslmode=require` if no query string is present.
3. In Render Environment, set `DATABASE_URL` to that connection string.
   The app accepts `postgresql://` and selects its installed psycopg driver.
4. Set `SUPABASE_URL` to your project's HTTPS URL and
   `SUPABASE_SERVICE_ROLE_KEY` to the legacy `service_role` key from Supabase's
   API Keys settings. This key belongs only in Render, never the frontend or Git.
5. Set `SUPABASE_STORAGE_BUCKET=papers`. Keep your AI provider values unchanged.
6. Keep `COOKIE_SECURE=true` and `ALLOWED_ORIGINS` equal to your actual HTTPS site
   origin. `DATA_DIR=/app/data` can remain for temporary local files.
7. Save and deploy, then start a new question from the homepage.

Use the database owner connection supplied by Supabase. At startup the app creates
its tables and enables row-level security so public Data API clients cannot read
them. FastAPI continues to authorize each project and PDF request using the app's
existing sessions; the app does not use Supabase Auth.

This starts a new database. Existing SQLite research and PDFs are not migrated
automatically. Data already erased by Render cannot be recovered by this change.
Render Free can still sleep or restart, interrupting active research jobs; external
storage preserves saved data, but does not make the worker continuously available.

After setup, verify a PDF upload, PDF viewing, and access to the same project after
a redeployment in the same browser. Local request checks alone do not validate
your Supabase credentials, database permissions, or network connectivity.

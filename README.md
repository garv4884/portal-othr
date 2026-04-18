# portal-othr

## Storage Backend

This app now uses Supabase as its persistent storage backend (instead of Redis).

If Supabase is not configured, the app falls back to in-memory storage for local use.

## Supabase Setup (Deployment)

1. Create a Supabase project.
2. Run [supabase_setup.sql](supabase_setup.sql) in Supabase SQL Editor:

```sql
create table if not exists public.ot_store (
	key text primary key,
	value jsonb
);
```

3. Set Streamlit secrets:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_OR_ANON_KEY"
SUPABASE_TABLE = "ot_store"
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run:

```bash
streamlit run app.py
```

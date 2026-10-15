# PrepMate AI

Interview practice for placement season. You answer real interview questions,
typed or out loud, and get scored feedback on structure, clarity and pace.

| Part | Stack | Hosted on |
|---|---|---|
| `web/` | React 19, TypeScript, Vite, Tailwind | Vercel |
| `api/` | Python 3.13, FastAPI, psycopg | Render |
| `supabase/` | Postgres with row-level security, Supabase Auth | Supabase |

## How it fits together

1. The browser signs in with Supabase Auth (an email link, or Google).
2. Every API call carries the Supabase access token. The API checks its
   signature against the project's public keys and takes the user id only
   from the verified token.
3. The API connects to Postgres as `prepmate_api`, a role that owns nothing.
   For each request it switches to the signed-in user, and row-level security
   limits every query to that user's rows.
4. Tables live in the `app` schema, which Supabase's public Data API doesn't
   expose, so the browser can't query the database directly.

## Security choices

- Only asymmetric token signatures (ES256 or RS256) are accepted, so a forged
  HS256 token is rejected. Public keys are cached and refreshed at a limited rate.
- Row-level security is on for every table, and anything without a policy is
  denied. Users can read their own rows and edit three profile fields. Scores
  and usage counters can be written only by the API.
- CORS allows only listed origins, and production refuses wildcards and plain http.
- Both the API and the site send strict security headers. The site's CSP
  allows scripts, styles and fonts from its own origin only.
- Errors return a request id and a plain message, never internal details.
- CI runs lint, type checks, tests, a dependency audit and a secret scan on
  every push. Dependabot opens weekly update PRs.

## Local development

```bash
# API
cd api
cp .env.example .env        # then fill in the values
uv sync
uv run uvicorn app.asgi:app --reload

# Web
cd web
cp .env.example .env.local  # then fill in the values
npm install
npm run dev
```

### Tests

```bash
cd api && uv run pytest      # needs a local Postgres; see TEST_DATABASE_ADMIN_URL
cd web && npm test
```

The API tests apply the real migration files to a throwaway database, and use
`supabase/tests/local_supabase_stub.sql` to stand in for the parts of Supabase
the schema depends on.

## One-time setup on a new Supabase project

1. Apply the migrations in `supabase/migrations/` in order.
2. Give the API role a password. Do this by hand in the SQL editor, never in a
   migration file:
   ```sql
   alter role prepmate_api login password '<a long random password>';
   ```
   Then set the API's `DATABASE_URL` to the transaction pooler (port 6543), with
   the user `prepmate_api.<project-ref>`.
3. Under Auth > URL Configuration, set the Site URL to the web app's address and
   add `<web address>/auth/callback` to the redirect URLs.
4. Before real users arrive, set up custom SMTP under Auth > SMTP. Supabase's
   built-in email sender is for testing only and allows very few emails per hour.
5. To offer Google sign-in, enable the Google provider in Supabase and set
   `VITE_ENABLE_GOOGLE=true`.

## Before the first deploy

`web/vercel.json` lists the API and Supabase addresses the site may call
(`connect-src`). If the Render service gets a different name than
`prepmate-api`, update that line, or the browser will block the API calls.

# Local JSON API

Default base URL: `http://127.0.0.1:7865`. This is a private, single-user speech API. It does not implement chat completions.

GET `/` returns the HTML page with `<meta name="studio-token" content="...">`. Copy that token into `X-Studio-Token` for all POST requests. Use JSON request bodies with `Content-Type: application/json`. Refresh the token after a studio restart. Nonlocal Host/Origin values are rejected. Browser cross-origin access is not enabled.

| Method | Route | Result / JSON body |
| --- | --- | --- |
| GET | `/api/health` | App, PID, root, offline/busy status |
| GET | `/api/state` | Voices, feelings, creative readiness/presets, conversion targets, private history and storage |
| GET | `/api/jobs/{id}` | Job status/message; `result` when finished |
| GET | `/audio/{id}.wav` | Generated WAV from a known output directory |
| GET | `/api/openapi.json` | OpenAPI 3.1 description |
| POST | `/api/generate` | `{text, language, voice, feeling, expression, mode, description, seed}` |
| POST | `/api/convert` | `{audio, name, target}` |
| POST | `/api/voices` | `{audio, name}` |
| POST | `/api/storage` | `{directory: "absolute local path"}` |
| POST | `/api/storage/open` | `{}`; open the current folder in Windows Explorer |

Speech defaults: `feeling="neutral"`, `expression=0.7`, `mode="classic"`, `seed=42`. Set `voice` to a listed voice ID and `language` to `en` or `ta`. Creative mode requires its optional installation and English; `description` and creative tags guide delivery. Text is limited to 2,000 characters.

`audio` is base64-encoded **mono 24 kHz PCM WAV**, not a local path or a data URL. Conversion accepts 1–300 seconds; voice references accept 3–30 seconds and retain up to 15 seconds. For conversion the server checks the encoded size, samples, duration and silence. Use `studio_client.py` or the CLI to normalize local audio before submission. JSON request size is limited to 35 MiB.

Generation/conversion return HTTP 202 with `{id: "UUID"}`. Poll the job route; statuses are `queued`, `working`, `done`, `error`. Successful results include `saved_path`, `audio_url`, duration and metadata. No full audio payload is returned to an AI model. Retrieve the WAV locally if needed. State/paths are private; request history only when useful.

HTTP 400 means invalid input, 403 means the session token/origin/host is invalid, 404 means missing route/job/audio, 409 means another job is busy, and 500 means processing failed. Worker errors are reported in a job with `status="error"`. Do not blindly retry submissions after a network timeout: inspect status/history to avoid duplicating a job.

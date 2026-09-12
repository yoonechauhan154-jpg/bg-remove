# BG Remover Server Migration Plan

## Project Context
- **Current**: Static Netlify site (bg-remover-free.netlify.app) with fully client-side background removal using `@imgly/background-removal@1.4.5` + optional BiRefNet HQ mode.
- **Target**: Keep Netlify as frontend/SEO host. Route image processing to AWS EC2 backend running Lucida (egeorcun/lucida) via FastAPI/Docker.
- **Key Constraint**: Zero disruption to existing organic traffic, URLs, SEO pages, sitemap, robots.txt, canonicals, meta titles/descriptions.

## Architecture (Preserved + Additive)
- **Netlify (unchanged)**:
  - All existing ~60 HTML SEO pages, index.html, assets.
  - `_redirects`, `_headers`.
  - sitemap.xml, robots.txt, llms.txt.
  - No changes to page hierarchy, internal links, structured data.
- **AWS (new, isolated)**:
  - EC2 (Ubuntu) → Docker → FastAPI (Lucida official serving pattern).
  - CPU-first (benchmark before any GPU recommendation).
  - No S3, RDS, Lambda, Redis, K8s, ECS unless proven necessary later.
- **Request Flow**:
  Browser → `POST /api/remove` (relative, on Netlify) → Netlify `_redirects` 200 proxy → AWS backend (`/remove` or `/api/remove`) → Lucida → transparent PNG → Browser.
- **Fallback**:
  - `SERVER_PROCESSING` feature flag (env or localStorage toggle).
  - If server fails or flag off → seamless fallback to existing browser impl (no breakage).
- **Privacy/Security**:
  - No permanent storage of uploads/results.
  - Temp files deleted after processing (shutil, contextlib).
  - Validate: MIME types (image/jpeg|png|webp), size <=10MB (or 15MB buffer), dimensions (e.g. <4096px to protect memory).
  - Timeouts, rate limit (simple IP or token bucket in FastAPI), safe filenames, path traversal guards.
  - No secrets in frontend/git; use Netlify env vars or AWS SSM only for backend.
  - Logs: never log image bytes or full content.

## Implementation Phases (Additive, Rollback-Safe)
1. **Documentation & Checkpoint** (current):
   - Create MIGRATION_PLAN.md, BACKEND_SETUP.md, AWS_DEPLOYMENT.md, ROLLBACK.md, TEST_RESULTS.md.
   - Git checkpoint commit of current state (before edits).
2. **Backend**:
   - Clone/adapt official Lucida `serving/app.py` + Dockerfile.
   - Change/alias endpoint to support `POST /api/remove` (or keep /remove + Netlify rewrite).
   - Add strict validation, temp dir cleanup (tempfile + atexit or middleware).
   - Health: GET /health → {"status":"ok", "model":"lucida", "version":"..."}.
   - Error responses: 400 invalid file/type/size, 413 too large, 422 processing error, 504 timeout, 500 with generic msg.
   - CORS: allow Netlify origin(s).
3. **Netlify Integration**:
   - Update `_redirects` with proxy rule (use placeholder domain or later DNS; avoid raw EC2 IP in committed code — use Netlify env or build-time injection).
   - Optional: Netlify Function as thin proxy if direct redirect insufficient for headers/timeouts.
4. **Frontend Updates (Minimal, Feature-Flagged)**:
   - Add `const USE_SERVER = localStorage.getItem('USE_SERVER_BG') === 'true' || false;` toggle (dev only or hidden admin).
   - In `processFiles()`: if USE_SERVER try fetch('/api/remove', {method:'POST', body: formData}) else existing removeBackground().
   - On failure: auto-fallback + user message "Server busy, using local processing".
   - Keep MAX_FILES=20, allowedTypes, 10MB doc limit.
   - Update only privacy wording in affected pages (e.g. about.html, privacy-policy.html, how-ai-works.html, index.html FAQ) — change "never uploaded / processed locally only" → "processed securely on our servers with immediate deletion, no permanent storage".
5. **SEO Safety**:
   - No URL changes, no sitemap edits unless adding /api (but API not crawled).
   - Update only factual processing claims in content (additive paragraphs).
   - Preserve all canonical, og:, schema, internal links.
6. **AWS Deployment**:
   - EC2 t3.medium or c6i.large (CPU) first.
   - Docker build from Lucida Dockerfile (CPU torch).
   - systemd or docker-compose for auto-restart.
   - Nginx reverse proxy + HTTPS (Let's Encrypt) or ALB if needed.
   - Monitor: processing time, RAM/CPU per request, failure rate.
   - Benchmark: record 10-20 images (various types/sizes) on CPU; only then evaluate g4dn.xlarge or similar GPU + cost estimate.
7. **Testing Matrix** (per TEST_RESULTS.md):
   - Formats: JPG/JPEG, PNG, WebP.
   - Content: transparent objects, photos, logos, text, stickers, illustrations, products, hair/fur, glow/shadow, difficult edges.
   - Edge: oversized (>10MB or >4k px), invalid MIME, corrupt files, empty.
   - Bulk: 1, 5, 20 concurrent.
   - Mobile/desktop, slow network.
   - Metrics: latency (p50/p95), memory peak, CPU, success rate, output visual quality (side-by-side vs old).
8. **Rollback**:
   - Flip flag → instant browser-only.
   - DNS/EC2 stop → Netlify serves old behavior.
   - Git revert any frontend changes.
9. **Docs & Handoff**:
   - All .md files kept practical, with exact commands, exact instance types tried, exact costs.
   - Final verification: crawl sitemap, check live URLs, no 404s, SEO tools pass.

## Risks & Mitigations
- **SEO traffic loss**: Strictly additive + wording-only updates; full git history.
- **Performance regression**: CPU benchmark first; fallback always available.
- **Cost overrun**: CPU start; GPU only after measured numbers + user approval.
- **Model quality drop**: Lucida chosen because it excels on transparency/text/glow per its own benchmark; keep client HQ as option.
- **Secrets leak**: Zero frontend keys; backend uses env only, .dockerignore, no .env in git.

## Success Criteria
- Live site identical URLs/content/SEO.
- /api/remove works, returns valid transparent PNG for supported inputs.
- <5s avg processing on CPU for typical 2-5MB photo (target).
- Zero permanent image storage.
- One-command rollback.
- All required docs present and accurate.

## Next Immediate Actions
- Commit current state.
- Scaffold backend repo (separate or subdir? prefer simple: new /backend dir or standalone).
- Local Docker test of Lucida serving.
- Edit only privacy text first (low risk).

This plan prioritizes safety, reversibility, and preservation of existing value over speed of migration.

# Local MVP build notes

- This is a review-ready local patch package. No Git commit, push, merge or PR was created.
- The public GitHub skeleton branch was inspected through the repository connector. A direct `git clone` could not complete in this environment because outbound DNS/network access to `github.com` was unavailable. `apply_to_repo.ps1` applies this patch to the user's own clone without running Git commands.
- The original company ZIP and extracted data are not included. Keep the data pack under the ignored `data_private/vinayak-vch3-data/` path.
- Public fixtures and demo content are synthetic. The private pack was only inspected locally; its document contents were not sent to Sarvam and no real-data cache was placed in the package.
- Latest test run: `python -m pytest -q` — **32 passed**. Tests cover the Decimal comparison cases, unit resolution, API end-to-end synthetic upload flow, approval, Excel/PDF parser behaviour, recorded Sarvam chat and Document AI responses, retry/cache flow, error envelope and architecture boundaries.
- Sarvam REST details were checked against the official docs: V2 Chat Completions, `api-subscription-key`, `sarvam-105b`, and Document AI Parse/status/download-url. No live API call was made because no `SARVAM_API_KEY` was supplied.
- Scanned PDF/image OCR calls Sarvam Document AI first when configured; local Tesseract/Poppler is the fallback. OCR quality on the real scanned quotation remains unverified against a human-reviewed extraction.
- Deterministic parsing was exercised locally on the private pack. Its PDF/Excel heuristics are conservative; extracted values must be reviewed against source evidence. Missing values remain UNKNOWN.
- Docker could not be built because Docker is not installed in this environment. Render deployment, Windows installation and a live Sarvam request are not verified.
- `pip check` reports a pre-existing environment-level conflict: the environment has Pillow 12.3 while an unrelated installed `moviepy` package requires Pillow below 12. The project requirements pin Pillow below 12; this does not indicate an application test failure.
- Before any future commit, check the local IST time and inspect the staged file list. The hook blocks commits after 16:45 IST on 21 Nov 2026. No commits are being made as part of this build.

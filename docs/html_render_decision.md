Decision: Use external browser with rendered HTML files

Summary
- Chosen approach: Render HTML templates (Jinja2) and open them in the user's external web browser using `webbrowser.open()`.
- Rationale: avoids adding Qt WebEngine dependency, works reliably across platforms, and leverages the system's browser printing/printing-to-PDF features.

Why this approach
- Simpler to implement and maintain than embedding a web engine.
- No additional large binary dependencies required for the application UI.
- Leverages the user's default browser for familiar print/save workflows.
- Works well with PyInstaller packaging when templates and assets are bundled correctly.

Rendering & Serving
- Render templates using Jinja2 (preferred). Templates will live in a `templates/` folder in the repo (or copied from `html_forms/` and converted to Jinja placeholders).
- The renderer will write the rendered HTML to a temporary file (e.g., using `tempfile.NamedTemporaryFile(delete=False, suffix='.html')`) and then open that file with `webbrowser.open()`.
- Temporary files should be cleaned up later (on app exit, or via a background cleanup job). Consider providing a "Save" button/flow in the browser to persist filled forms if needed.

Assets (CSS / JS / Images)
- Prefer inlining critical CSS into the templates for portability.
- If static files are used, reference them via absolute `file://` paths when rendering so the browser can load them.
- When packaging (PyInstaller), ensure static assets are included in the bundle and that the renderer can resolve `templates/` and `static/` paths at runtime.

Security & Privacy
- Avoid serving content over HTTP unless running a short-lived local server is explicitly chosen and secured.
- Be careful with temporary file permissions; do not write sensitive data to world-readable locations if OS permissions are a concern.
- If records contain PII, consider deleting temp files as soon as the user finishes (or on application exit) and document retention policy.

Fallbacks
- If Jinja2 is not available, the renderer will fall back to a simple string-substitution strategy (best-effort), but adding `jinja2` to `requirements.txt` is recommended.

Next steps (high level)
1. Inventory and standardize HTML templates in `html_forms/` and convert them to Jinja2 templates in `templates/`.
2. Create a `html_field_map.py` to map DB keys to template placeholders.
3. Implement `html_renderer.py` to render and write temp files, and return the temp file path.
4. Update `verify.py`'s `open_auto_form()` to call the renderer and `webbrowser.open()` the returned path (do this change after testing the renderer).
5. Add tests and update packaging instructions to include templates/static assets.

Document owner
- Created by: developer (as requested)
- Date: 2025-12-09

Notes
- This document records the decision only; implementation patches will be prepared separately and applied after review.

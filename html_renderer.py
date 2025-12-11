"""HTML renderer scaffold for rvs-app

Provides a small helper to render record dictionaries into HTML and return
a temporary HTML file path that can be opened with `webbrowser.open()`.

This is a scaffold: it prefers Jinja2 if available and falls back to a
simple templating approach if not. The implementation intentionally avoids
changing existing app code (e.g., `verify.py`).

TODO:
- Convert `html_forms/` templates into `templates/` with Jinja placeholders.
- Wire `render_html_form()` into `verify.py.open_auto_form()` after tests.
- Add unit tests for rendering and temp-file cleanup.
"""

from __future__ import annotations
import os
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    _HAS_JINJA = True
except Exception:
    _HAS_JINJA = False

# Import the field mapping helper to build template contexts
try:
    from html_field_map import build_template_context
except Exception:
    # If the mapping module is missing, provide a fallback that returns
    # the original record so rendering can still proceed (best-effort).
    def build_template_context(record, form_type):
        return {} if record is None else record


def _default_templates_dir() -> Path:
    # Prefer a `templates/` directory next to the project root; fallback to `html_forms/`.
    base = Path(__file__).resolve().parent
    candidates = [base / 'templates', base / 'html_forms', Path('templates'), Path('html_forms')]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # If none exist, return the first candidate (templates) so callers can create it.
    return base / 'templates'


def render_html_form(record_dict: dict, form_type: str, templates_dir: Optional[str] = None, use_tempfile: bool = True, current_user: str = '', today_date: str = '') -> str:
    """Render a record into HTML and return a file path.

    Parameters
    - record_dict: dictionary with database fields (strings) to substitute into template
    - form_type: one of 'Birth', 'Death', 'Marriage' (used to choose template)
    - templates_dir: optional path to templates; defaults to `templates/` or `html_forms/`
    - use_tempfile: if True, writes rendered HTML to a temporary file and returns its path
    - current_user: username to populate in 'verified_by' field (optional)
    - today_date: ISO date string (YYYY-MM-DD) for 'certificate_date' and 'date_paid' (optional)

    Returns: path to the rendered HTML file (string). If `use_tempfile` is False,
    returns the raw HTML as a string (caller must handle it).

    Notes
    - This function intentionally does not open the browser; caller should call
      `webbrowser.open(file_path)` to display the result.
    """
    templates_path = Path(templates_dir) if templates_dir else _default_templates_dir()
    # Map logical form types to the actual template filenames in `templates/`.
    form_map = {
        'birth': 'form1a.html',
        'death': 'form2a.html',
        'marriage': 'form3a.html'
    }
    template_name = form_map.get(form_type.strip().lower(), f"{form_type.lower()}.html")

    # Build a template context using our field mapping helper so templates
    # receive variables with the names used in `templates/*.html`.
    try:
        context = build_template_context(record_dict or {}, form_type, current_user=current_user, today_date=today_date)
    except Exception:
        context = {} if record_dict is None else record_dict
    
    # Add absolute paths for logo images so they can be found when HTML is opened as file://
    # Resolve the project root directory (parent of this script)
    project_root = Path(__file__).resolve().parent
    logos_dir = project_root / 'logos'
    
    # Add image paths to context as file:// URIs so they work in the browser
    if logos_dir.exists():
        context['city_logo_path'] = (logos_dir / 'city-logo.png').as_uri()
        context['occr_logo_path'] = (logos_dir / 'occr-logo.png').as_uri()
    else:
        # Fallback to relative paths if logos dir not found
        context['city_logo_path'] = '../logos/city-logo.png'
        context['occr_logo_path'] = '../logos/occr-logo.png'

    # If Jinja2 is available and template exists, use it
    if _HAS_JINJA and (templates_path / template_name).exists():
        env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template_name)
        rendered = template.render(**context)
    else:
        # Fallback: attempt to load raw template and perform simple replacement
        tpl_path = templates_path / template_name
        if tpl_path.exists():
            raw = tpl_path.read_text(encoding='utf-8')
            # Simple placeholder format: {{ key }} or {key}
            # First try Jinja-style removal of braces for naive replace
            rendered = raw
            for k, v in context.items():
                placeholder_jinja = f"{{{{ {k} }}}}"
                placeholder_curly = f"{{{k}}}"
                rendered = rendered.replace(placeholder_jinja, str(v or ''))
                rendered = rendered.replace(placeholder_curly, str(v or ''))
        else:
            # No template found — create a minimal HTML to show key-values
            items = [f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in context.items()]
            rendered = f"<html><head><meta charset=\"utf-8\"><title>{form_type} Form</title></head>\n"
            rendered += "<body><h1>{}</h1><table>{}</table></body></html>".format(form_type, '\n'.join(items))

    if not use_tempfile:
        return rendered

    # Write to a temp file and return the path
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', prefix='rvs_form_')
    try:
        tmp.write(rendered.encode('utf-8'))
        tmp.flush()
        tmp_path = tmp.name
    finally:
        tmp.close()

    # On Windows, webbrowser.open can accept file path; caller can use Path(tmp_path).as_uri() as well
    return tmp_path


def open_rendered_form_in_browser(html_path: str) -> None:
    """Open the given HTML file path in the default external browser."""
    try:
        # Prefer file:// URI
        p = Path(html_path).resolve()
        webbrowser.open(p.as_uri())
    except Exception:
        # Fallback to opening the path directly
        webbrowser.open(html_path)


def cleanup_temp_file(path: str) -> None:
    """Attempt to delete a temporary HTML file. Ignore errors."""
    try:
        os.remove(path)
    except Exception:
        pass


if __name__ == '__main__':
    # Quick interactive test scaffold
    sample = {'name': 'Juan Dela Cruz', 'date_of_birth': '1990-01-01', 'reg_no': '12345'}
    path = render_html_form(sample, 'Birth')
    print('Rendered to:', path)
    open_rendered_form_in_browser(path)

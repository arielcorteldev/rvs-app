"""Map database record keys to Jinja2 template variable names.

This module provides simple mapping dictionaries for Birth, Death and Marriage
records and a helper `build_template_context(record_dict, form_type)` which
returns a template-ready context (dict) with all required template variables
present (missing values default to empty strings).

Usage:
    from html_field_map import build_template_context
    context = build_template_context(record_dict, 'Birth')
    # then pass `context` into Jinja2 template.render(**context)

Notes:
- The function assumes `record_dict` already has dates formatted as strings
  (the existing `open_auto_form()` in `verify.py` formats dates to ISO strings).
- Template variable names are chosen to match the `templates/*.html` files in
  the repo. If you change template variable names, update the mappings here.
"""

from typing import Dict, Any

# Mapping from internal DB keys (as produced by verify.open_auto_form)
# to template variable names used in templates/form*.html
BIRTH_MAP = {
    'name': 'name',
    'date_of_birth': 'date_of_birth',
    'sex': 'sex',
    'page_no': 'page_no',
    'book_no': 'book_no',
    'reg_no': 'reg_no',
    'date_of_reg': 'date_of_reg',
    'place_of_birth': 'place_of_birth',
    'name_of_mother': 'name_of_mother',
    'nationality_mother': 'nationality_mother',
    'name_of_father': 'name_of_father',
    'nationality_father': 'nationality_father',
    'parents_marriage_date': 'parents_marriage_date',
    'parents_marriage_place': 'parents_marriage_place',
    'attendant': 'attendant',
}

DEATH_MAP = {
    'name': 'name',
    'date_of_death': 'date_of_death',
    'sex': 'sex',
    'page_no': 'page_no',
    'book_no': 'book_no',
    'reg_no': 'reg_no',
    'date_of_reg': 'date_of_reg',
    'age': 'age',
    'civil_status': 'civil_status',
    'nationality': 'nationality',
    'place_of_death': 'place_of_death',
    'cause_of_death': 'cause_of_death',
}

MARRIAGE_MAP = {
    'husband_name': 'husband_name',
    'wife_name': 'wife_name',
    'date_of_marriage': 'date_of_marriage',
    'page_no': 'page_no',
    'book_no': 'book_no',
    'reg_no': 'reg_no',
    'husband_age': 'husband_age',
    'wife_age': 'wife_age',
    'husb_nationality': 'husb_nationality',
    'wife_nationality': 'wife_nationality',
    'husb_civil_status': 'husb_civil_status',
    'wife_civil_status': 'wife_civil_status',
    'husb_mother': 'husb_mother',
    'wife_mother': 'wife_mother',
    'husb_father': 'husb_father',
    'wife_father': 'wife_father',
    'date_of_reg': 'date_of_reg',
    'place_of_marriage': 'place_of_marriage',
}

# Default template fields that are present in the templates but are not
# provided by the DB record. These will be populated with empty strings
# unless overridden by the caller (e.g., certificate_date, issued_to, etc.).
DEFAULT_TEMPLATE_FIELDS = [
    'certificate_date',
    'issued_to',
    'remarks',
    'verified_by',
    'amount_paid',
    'or_number',
    'date_paid',
    'for_as',
    'in_charge',
    'designation',
    'order_details',
]


def _format_date_to_long(date_str: str) -> str:
    """Convert ISO date string (YYYY-MM-DD) to long format (January 1, 2025).
    
    Parameters
    - date_str: ISO format date string (YYYY-MM-DD) or empty string
    
    Returns formatted date string or empty string if input is empty/invalid.
    """
    if not date_str or not isinstance(date_str, str):
        return ''
    
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str.strip(), '%Y-%m-%d')
        # Format as "January 1, 2025"
        return dt.strftime('%B %d, %Y')
    except (ValueError, AttributeError):
        # If parsing fails, return as-is
        return str(date_str) if date_str else ''


def build_template_context(record: Dict[str, Any], form_type: str, current_user: str = '', today_date: str = '') -> Dict[str, Any]:
    """Build a template context for the given record and form type.

    Parameters
    - record: dictionary returned from DB queries (values already converted
      to strings where necessary by `verify.open_auto_form()`).
    - form_type: one of 'Birth', 'Death', 'Marriage' (case-insensitive).
    - current_user: username to populate in 'verified_by' field (optional).
    - today_date: ISO date string (YYYY-MM-DD) for 'certificate_date' and 'date_paid' (optional).

    Returns a dictionary suitable for `template.render(**context)`.
    """
    if not record:
        record = {}

    ft = form_type.strip().lower()
    if ft == 'birth':
        mapping = BIRTH_MAP
    elif ft == 'death':
        mapping = DEATH_MAP
    elif ft == 'marriage':
        mapping = MARRIAGE_MAP
    else:
        raise ValueError(f"Unknown form_type: {form_type}")

    context: Dict[str, Any] = {}

    # Map DB keys to template variable names, formatting dates as we go
    for src_key, tpl_key in mapping.items():
        value = record.get(src_key)
        # Check if this is a date field and format it
        if src_key in ['date_of_birth', 'date_of_death', 'date_of_marriage', 'date_of_reg', 'parents_marriage_date']:
            context[tpl_key] = _format_date_to_long(value) if value else ''
        else:
            # Normalize None to empty string
            context[tpl_key] = '' if value is None else value

    # Add default template keys
    for key in DEFAULT_TEMPLATE_FIELDS:
        # do not override if already provided
        if key not in context:
            if key == 'verified_by' and current_user:
                context[key] = current_user
            elif key in ['certificate_date', 'date_paid'] and today_date:
                context[key] = _format_date_to_long(today_date)
            else:
                context[key] = ''

    return context


# Expose mapping dicts for reference
__all__ = [
    'BIRTH_MAP', 'DEATH_MAP', 'MARRIAGE_MAP', 'build_template_context'
]

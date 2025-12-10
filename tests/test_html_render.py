import os
from html_renderer import render_html_form


def test_render_birth_form_contains_values():
    record = {
        'name': 'Juan Dela Cruz',
        'date_of_birth': '1990-01-01',
        'reg_no': 'B-12345',
    }

    html_path = render_html_form(record, 'Birth')
    try:
        assert os.path.exists(html_path), f"Rendered file not found: {html_path}"
        content = open(html_path, 'r', encoding='utf-8').read()
        assert 'Juan Dela Cruz' in content
        # Date is now formatted as long format (e.g., "January 01, 1990")
        assert 'January 01, 1990' in content
        assert 'B-12345' in content
    finally:
        try:
            os.remove(html_path)
        except Exception:
            pass


def test_render_death_form_contains_values():
    record = {
        'name': 'Maria Santos',
        'date_of_death': '2020-12-31',
        'cause_of_death': 'Natural causes',
    }

    html_path = render_html_form(record, 'Death')
    try:
        assert os.path.exists(html_path), f"Rendered file not found: {html_path}"
        content = open(html_path, 'r', encoding='utf-8').read()
        assert 'Maria Santos' in content
        # Date is now formatted as long format (e.g., "December 31, 2020")
        assert 'December 31, 2020' in content
        assert 'Natural causes' in content
    finally:
        try:
            os.remove(html_path)
        except Exception:
            pass


def test_render_marriage_form_contains_values():
    record = {
        'husband_name': 'Pedro',
        'wife_name': 'Ana',
        'date_of_marriage': '2015-06-15',
    }

    html_path = render_html_form(record, 'Marriage')
    try:
        assert os.path.exists(html_path), f"Rendered file not found: {html_path}"
        content = open(html_path, 'r', encoding='utf-8').read()
        assert 'Pedro' in content
        assert 'Ana' in content
        # Date is now formatted as long format (e.g., "June 15, 2015")
        assert 'June 15, 2015' in content
    finally:
        try:
            os.remove(html_path)
        except Exception:
            pass

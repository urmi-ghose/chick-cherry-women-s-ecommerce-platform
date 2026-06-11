import json
import os

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'site_settings.json')

DEFAULTS = {
    'site_name': 'ChicCherry',
    'header_email': 'ChicCherry@gmail.com',
    'header_phone': '+8801701020304',
    'banners': [],
    'footer_email': 'ChicCherry@gmail.com',
    'footer_phone': '+8801701020304',
    'footer_address': 'Sylhet, Bangladesh',
    'footer_copy': '© 2025 ChicCherry',
}


def get_site_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Fill missing keys with defaults
        for k, v in DEFAULTS.items():
            data.setdefault(k, v)
        return data
    except Exception:
        return dict(DEFAULTS)


def save_site_settings(data):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

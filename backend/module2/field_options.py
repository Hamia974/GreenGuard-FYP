"""Loader for docs/module2_field_options.json.

REST_API_SPEC.md section 8A is explicit: "The full set of valid categorical
values is defined in docs/module2_field_options.json -- the frontend and
backend must both read from that file rather than hardcoding a competing
list." This module reads that file directly (rather than duplicating its
contents into Python constants) so the two can never drift out of sync.
"""

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

FIELD_OPTIONS_PATH = Path(settings.BASE_DIR).parent / "docs" / "module2_field_options.json"


@lru_cache(maxsize=1)
def get_field_options() -> dict:
    with open(FIELD_OPTIONS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def categorical_choices(field_name: str) -> list:
    return get_field_options()["categorical_fields"][field_name]


def symptom_keys() -> list:
    return get_field_options()["symptom_fields"]["keys"]


def crop_model_support() -> dict:
    return get_field_options()["crop_model_support"]


def is_crop_supported(crop: str) -> bool:
    return crop in crop_model_support()["trained_and_supported"]

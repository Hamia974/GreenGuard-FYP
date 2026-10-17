from rest_framework import serializers

from .field_options import categorical_choices, symptom_keys

# Human-readable labels for the documented invalid-choice error wording, e.g.
# REST_API_SPEC.md's example: '"maize " is not a valid crop value.'
_CATEGORICAL_LABELS = {
    "crop": "crop",
    "growth_stage": "growth stage",
    "soil_type": "soil type",
    "last_fertilizer_type": "fertilizer type",
    "days_since_fertilizer": "days since fertilizer",
    "irrigation_source": "irrigation source",
    "irrigation_adequacy": "irrigation adequacy",
}


def _choice_field(field_name: str) -> serializers.ChoiceField:
    label = _CATEGORICAL_LABELS[field_name]
    return serializers.ChoiceField(
        choices=categorical_choices(field_name),
        error_messages={"invalid_choice": f'"{{input}}" is not a valid {label} value.'},
    )


class SymptomsField(serializers.DictField):
    """Validates the `symptoms` object per module2_field_options.json's
    symptom_fields.keys and mutually_exclusive_rule.
    """

    child = serializers.BooleanField()

    def to_internal_value(self, data):
        value = super().to_internal_value(data)

        expected = set(symptom_keys())
        missing = expected - value.keys()
        extra = value.keys() - expected
        if missing or extra:
            problems = []
            if missing:
                problems.append(f"missing keys: {sorted(missing)}")
            if extra:
                problems.append(f"unexpected keys: {sorted(extra)}")
            raise serializers.ValidationError(
                f"symptoms must include exactly the documented keys ({'; '.join(problems)})."
            )

        none_visible = value.get("none_visible", False)
        other_selected = any(v for k, v in value.items() if k != "none_visible" and v)
        if none_visible and other_selected:
            raise serializers.ValidationError(
                '"none_visible" must be false when any other symptom is true, and vice versa.'
            )

        return value


class Module2RequestSerializer(serializers.Serializer):
    """Validates POST /api/v1/module2/analyze/ per REST_API_SPEC.md section 8A."""

    farm_id = serializers.UUIDField()
    crop = _choice_field("crop")
    growth_stage = _choice_field("growth_stage")
    soil_type = _choice_field("soil_type")
    last_fertilizer_type = _choice_field("last_fertilizer_type")
    days_since_fertilizer = _choice_field("days_since_fertilizer")
    irrigation_source = _choice_field("irrigation_source")
    irrigation_adequacy = _choice_field("irrigation_adequacy")
    symptoms = SymptomsField()
    # Required as of the Stress Module's v1.1.0 delivery (2026-09-10): a soil
    # meter ships with the deployment, so these three readings are always
    # available. The Stress Module's own /predict rejects a request missing
    # any of them with HTTP 422 and never defaults a missing value -- this
    # serializer enforces the same rule before Django ever calls it, per
    # REST_API_SPEC.md's updated Module 2 request contract.
    ph_value = serializers.FloatField(min_value=0, max_value=14)
    soil_moisture_pct = serializers.FloatField(min_value=0, max_value=100)
    light_intensity_lux = serializers.FloatField(min_value=0)

    def validate(self, attrs):
        last_fertilizer = attrs.get("last_fertilizer_type")
        days_since = attrs.get("days_since_fertilizer")

        if last_fertilizer == "No_Fertilizer" and days_since != "not_applicable":
            raise serializers.ValidationError(
                {
                    "days_since_fertilizer": [
                        'days_since_fertilizer must be "not_applicable" when '
                        'last_fertilizer_type is "No_Fertilizer".'
                    ]
                }
            )

        if last_fertilizer != "No_Fertilizer" and days_since == "not_applicable":
            raise serializers.ValidationError(
                {
                    "days_since_fertilizer": [
                        'days_since_fertilizer must not be "not_applicable" when '
                        'last_fertilizer_type is not "No_Fertilizer".'
                    ]
                }
            )

        return attrs

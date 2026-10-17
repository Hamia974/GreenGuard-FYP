from rest_framework import serializers

from .validators import validate_disease_check_image


class DiseaseCheckRequestSerializer(serializers.Serializer):
    """Validates POST /api/v1/module1/analyze/.

    Only format-level validation happens here: image presence/size, and
    farm_id being a well-formed UUID (existence/ownership is resolved by the
    view, returning 404, not this serializer's 422 -- the same split used by
    predictions.views._get_owned_farm and module2.views._get_owned_farm).

    `crop` is optional and free-text, normalized to lowercase/stripped only
    -- not validated against a fixed choice list here. Per
    ai/API_CONTRACT.md, the live Disease Module itself is case-insensitive,
    accepts synonyms (e.g. "corn" -> maize), and is the sole source of truth
    for which crop values are valid (rejecting anything else with its own
    422 INVALID_CROP). Duplicating that list here would risk it drifting out
    of sync with the module's own supported set.
    """

    image = serializers.ImageField(validators=[validate_disease_check_image])
    farm_id = serializers.UUIDField()
    crop = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate_crop(self, value):
        value = value.strip().lower()
        return value or None

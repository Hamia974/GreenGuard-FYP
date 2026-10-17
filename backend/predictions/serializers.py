from rest_framework import serializers

from .validators import validate_plant_image


class PredictionAnalyzeRequestSerializer(serializers.Serializer):
    """Validates POST /api/v1/predictions/analyze/ per REST_API_SPEC.md's
    "Analyze Plant" / "Request Parameters" section.

    Only format-level validation happens here: image format/size/resolution
    (via the existing validate_plant_image) and farm_id being a well-formed
    UUID. Farm existence and ownership -- which return a 404 per
    REST_API_SPEC.md's Error Responses, not the 422 this serializer's own
    validation failures produce -- are resolved by the view, per the same
    split already established by module2.views._get_owned_farm. This
    serializer does not query the database, call any AI service, or create
    a Prediction record.

    `crop` is optional and forwarded to Module 1 (Disease Detection) as-is,
    normalized exactly like module1.serializers.DiseaseCheckRequestSerializer
    -- the live Disease Module is the sole judge of which crop values are
    valid (ai/API_CONTRACT.md), so no choice list is duplicated here.
    """

    image = serializers.ImageField(validators=[validate_plant_image])
    farm_id = serializers.UUIDField()
    crop = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate_crop(self, value):
        value = value.strip().lower()
        return value or None


class PredictionAnalyzeResponseSerializer(serializers.Serializer):
    """Shapes the POST /api/v1/predictions/analyze/ success response per
    REST_API_SPEC.md's "Standard Success Response" envelope.

    `data` is the saved analysis record (PredictionSerializer's shape),
    whose `prediction_report` holds the three module results verbatim. It
    is an opaque DictField here: only the outer envelope belongs to Django.
    """

    success = serializers.BooleanField()
    message = serializers.CharField()
    data = serializers.DictField()


class PredictionSerializer(serializers.Serializer):
    """Shapes a Prediction row for GET /api/v1/predictions/ and
    GET /api/v1/predictions/{id}/ per REST_API_SPEC.md section 3.

    Used for both the list and detail endpoints -- the spec gives no
    separate summary shape for the list endpoint (unlike Section 6's
    /api/v1/history/, which is a distinct, not-yet-built Phase 7 endpoint),
    so this exposes the full stored record for either, mirroring farms'
    FarmSerializer being reused for both its list and detail views.
    """

    prediction_id = serializers.SerializerMethodField()
    farm_id = serializers.SerializerMethodField()
    uploaded_image = serializers.SerializerMethodField()
    # Legacy Fusion-era columns: always null for analyses created under the
    # current architecture (see Prediction's docstring). Kept in the shape so
    # older rows remain readable and no documented field silently vanishes.
    final_diagnosis = serializers.CharField(read_only=True, allow_null=True)
    confidence_score = serializers.FloatField(read_only=True, allow_null=True)
    prediction_report = serializers.DictField(read_only=True)
    recommendation_summary = serializers.CharField(read_only=True, allow_null=True)
    prediction_status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def get_prediction_id(self, prediction):
        return str(prediction.id)

    def get_farm_id(self, prediction):
        return str(prediction.farm_id)

    def get_uploaded_image(self, prediction):
        if not prediction.uploaded_image:
            return None
        request = self.context.get("request")
        url = prediction.uploaded_image.url
        return request.build_absolute_uri(url) if request else url

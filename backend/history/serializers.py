from rest_framework import serializers

from predictions.serializers import PredictionSerializer

# GET /api/v1/history/{prediction_id}/ per REST_API_SPEC.md section 6 ("Get
# Prediction Details": returns the exact analysis stored during Quick Scan --
# the module1/module2/module3 results in prediction_report). No second table/model or
# second serializer is introduced for this -- Phase 7 reuses the exact same
# Prediction row and serializer Phase 6 already built and tested, just
# re-exported under this name so history.views doesn't need to import
# predictions.serializers directly.
HistoryDetailSerializer = PredictionSerializer

# REST_API_SPEC.md section 6 documents ``page``/``limit`` as inputs and
# requires pagination "when records exceed one page" but specifies no
# default page size and no maximum. 20 matches the project's existing
# global DRF PAGE_SIZE (config/settings.py REST_FRAMEWORK), and 100 is a
# conservative cap to prevent abusive requests, per explicit product
# decision to pick "a sensible project-consistent maximum" rather than
# leave limit unbounded.
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# `page` has no natural upper bound from the spec, but pagination.paginate()
# turns it into a SQL OFFSET via (page - 1) * limit. Without a cap, DRF's
# IntegerField still accepts arbitrarily large integers (up to a 1000-digit
# string) and Django would hand the database an enormous OFFSET, which some
# backends reject with an uncontrolled 500 rather than a clean validation
# error. 100_000 pages (~10,000,000 offset at MAX_LIMIT) is far beyond any
# realistic history size while keeping the failure mode a 422, not a 500.
MAX_PAGE = 100_000


class HistoryQuerySerializer(serializers.Serializer):
    """Validates GET /api/v1/history/ query parameters per REST_API_SPEC.md
    section 6 ("Get Prediction History" / "Query Parameters": page, limit,
    search, sort, from_date, to_date).

    Invalid values (non-integer/non-positive page or limit, limit above
    MAX_LIMIT, an unsupported sort value, an unparsable date, or
    from_date > to_date) fail validation here and the view returns the
    project's standard 422 "Validation failed." envelope, per explicit
    product decision to validate rather than silently clamp or ignore bad
    input. Only ``newest``/``sort=oldest`` are implemented for ``sort`` --
    REST_API_SPEC.md section 6 documents no other values, so the extra
    "Highest Confidence / Lowest Confidence / Alphabetical" options listed
    in UI_SPECIFICATION.md section 13.5 are deliberately not implemented
    here (no backend contract for them).
    """

    page = serializers.IntegerField(
        min_value=1, max_value=MAX_PAGE, required=False, default=1
    )
    limit = serializers.IntegerField(
        min_value=1, max_value=MAX_LIMIT, required=False, default=DEFAULT_LIMIT
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    sort = serializers.ChoiceField(
        choices=["newest", "oldest"], required=False, default="newest"
    )
    from_date = serializers.DateField(required=False, allow_null=True, default=None)
    to_date = serializers.DateField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                {"from_date": ["from_date must not be after to_date."]}
            )
        return attrs


class HistoryListItemSerializer(serializers.Serializer):
    """Shapes one row of GET /api/v1/history/'s ``data`` array, per
    REST_API_SPEC.md section 6's documented list example: {prediction_id,
    diagnosis, confidence, recommended_crop, created_at}.

    This is a distinct, narrower contract from predictions.PredictionSerializer
    (Phase 6's GET /api/v1/predictions/ list). ``diagnosis``/``confidence``
    are Module 1's (Disease Detection) own ``prediction.display_name`` /
    ``prediction.confidence``, read verbatim from the stored report -- both
    null when Module 1 returned ``status: "uncertain"`` (the full ``top3``
    stays available on the detail endpoint). There is no combined/fused
    diagnosis any more, so nothing is derived here.

    ``recommended_crop`` is a documented field with no backing data source:
    the Prediction model has no crop-recommendation column, and Module 2's
    questionnaire output (a separate, unrelated feature -- see
    module2.models.Module2Analysis) is never used to fabricate one. Per
    explicit product decision, this field is preserved in the response
    contract and always returns ``null`` rather than being silently dropped
    or invented. This is a known specification/data-model mismatch: section
    6's example implies a source for "recommended crop" that does not exist
    anywhere in the current Prediction pipeline.
    """

    prediction_id = serializers.SerializerMethodField()
    diagnosis = serializers.CharField(
        source="disease_result_name", read_only=True, allow_null=True
    )
    confidence = serializers.FloatField(
        source="disease_result_confidence", read_only=True, allow_null=True
    )
    recommended_crop = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_prediction_id(self, prediction):
        return str(prediction.id)

    def get_recommended_crop(self, prediction):
        return None

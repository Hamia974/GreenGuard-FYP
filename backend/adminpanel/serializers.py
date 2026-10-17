from rest_framework import serializers

# Same pagination bounds as history/serializers.py (page-size precedent for
# this project); kept as a local copy rather than a cross-app import for the
# same isolation reason as adminpanel.pagination.
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MAX_PAGE = 100_000


class UserListQuerySerializer(serializers.Serializer):
    """Validates GET /api/v1/admin/users/ query params per REST_API_SPEC.md
    section 8 ("Supports: Search, Pagination, Sorting, Status Filtering").
    """

    page = serializers.IntegerField(min_value=1, max_value=MAX_PAGE, required=False, default=1)
    limit = serializers.IntegerField(
        min_value=1, max_value=MAX_LIMIT, required=False, default=DEFAULT_LIMIT
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=["Active", "Inactive"], required=False, allow_null=True, default=None
    )
    sort = serializers.ChoiceField(
        choices=["newest", "oldest", "name"], required=False, default="newest"
    )


class PredictionListQuerySerializer(serializers.Serializer):
    """Validates GET /api/v1/admin/predictions/ query params per
    REST_API_SPEC.md section 8 ("Supports: Search, Pagination, Filtering,
    Sorting"). `status` filters on Prediction.prediction_status -- the only
    naturally filterable field the model has -- even though it is not part
    of the documented response shape (filtering vs. exposing are separate
    concerns; see PredictionListItemSerializer below).
    """

    page = serializers.IntegerField(min_value=1, max_value=MAX_PAGE, required=False, default=1)
    limit = serializers.IntegerField(
        min_value=1, max_value=MAX_LIMIT, required=False, default=DEFAULT_LIMIT
    )
    search = serializers.CharField(required=False, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=["pending", "processing", "completed", "failed"],
        required=False,
        allow_null=True,
        default=None,
    )
    sort = serializers.ChoiceField(
        choices=["newest", "oldest"], required=False, default="newest"
    )


class UserStatusUpdateSerializer(serializers.Serializer):
    """Validates PUT /api/v1/admin/users/{user_id}/status/ per
    REST_API_SPEC.md section 8 ("Activate / Deactivate User").
    """

    status = serializers.ChoiceField(choices=["Active", "Inactive"])


class AdminUserListItemSerializer(serializers.Serializer):
    """Shapes one row of GET /api/v1/admin/users/'s `data` array per
    REST_API_SPEC.md section 8's documented example: user_id, full_name,
    email, status, role.
    """

    user_id = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    status = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    def get_user_id(self, user):
        return str(user.id)

    def get_status(self, user):
        return "Active" if user.is_active else "Inactive"

    def get_role(self, user):
        return user.role.capitalize()


class AdminUserDetailSerializer(serializers.Serializer):
    """Shapes GET /api/v1/admin/users/{user_id}/ per REST_API_SPEC.md
    section 8's documented "Includes" bullets (no JSON example is given for
    this endpoint, unlike the list): Profile Information, Prediction Count,
    Registration Date, Account Status. Field names otherwise mirror the
    existing users.ProfileSerializer / AdminUserListItemSerializer for
    consistency across the codebase.
    """

    user_id = serializers.SerializerMethodField()
    full_name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    role = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    prediction_count = serializers.SerializerMethodField()
    registration_date = serializers.DateTimeField(source="created_at", read_only=True)

    def get_user_id(self, user):
        return str(user.id)

    def get_role(self, user):
        return user.role.capitalize()

    def get_status(self, user):
        return "Active" if user.is_active else "Inactive"

    def get_profile_image(self, user):
        if not user.profile_image:
            return None
        request = self.context.get("request")
        url = user.profile_image.url
        return request.build_absolute_uri(url) if request else url

    def get_prediction_count(self, user):
        return user.predictions.count()


class AdminPredictionListItemSerializer(serializers.Serializer):
    """Shapes one row of GET /api/v1/admin/predictions/'s `data` array per
    REST_API_SPEC.md section 8's documented example: prediction_id, user
    (the owner's full name string), diagnosis, confidence, created_at.
    `diagnosis`/`confidence` are Module 1's own result, read verbatim (null
    when Module 1 was uncertain) -- see Prediction.disease_result_name.
    """

    prediction_id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    diagnosis = serializers.CharField(
        source="disease_result_name", read_only=True, allow_null=True
    )
    confidence = serializers.FloatField(
        source="disease_result_confidence", read_only=True, allow_null=True
    )
    created_at = serializers.DateTimeField(read_only=True)

    def get_prediction_id(self, prediction):
        return str(prediction.id)

    def get_user(self, prediction):
        return prediction.user.full_name

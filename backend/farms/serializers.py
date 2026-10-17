from rest_framework import serializers

from .models import Farm


class FarmSerializer(serializers.ModelSerializer):
    """Shapes farm objects in API responses per REST_API_SPEC.md section 2."""

    farm_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = Farm
        fields = [
            "farm_id",
            "farm_name",
            "address",
            "latitude",
            "longitude",
            "created_at",
            "updated_at",
        ]


class FarmWriteSerializer(serializers.ModelSerializer):
    """Validates POST/PUT /api/v1/farms/ per REST_API_SPEC.md section 2."""

    class Meta:
        model = Farm
        fields = ["farm_name", "address", "latitude", "longitude"]

    def validate_latitude(self, value):
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value

    def validate_longitude(self, value):
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value


class FarmGeocodeSerializer(serializers.Serializer):
    """Validates POST /api/v1/farms/geocode/ per REST_API_SPEC.md section 2."""

    address = serializers.CharField(max_length=500, trim_whitespace=True)
    language = serializers.ChoiceField(choices=["en", "ur"], required=False, default="en")

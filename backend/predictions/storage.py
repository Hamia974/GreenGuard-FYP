import uuid
from pathlib import Path

from django.utils import timezone


def generate_prediction_image_filename(instance, filename):
    """Generate a unique storage path for an uploaded plant image.

    Follows REST_API_SPEC.md's File Naming convention
    (e.g. leaf_20260731_103015.jpg), with a short uuid suffix appended so
    two uploads landing in the same second never collide.
    """
    extension = Path(filename).suffix.lower()
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    unique_suffix = uuid.uuid4().hex[:8]
    return f"uploads/leaf_{timestamp}_{unique_suffix}{extension}"

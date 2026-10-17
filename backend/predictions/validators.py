from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

# Formats, size limit, and minimum resolution per REST_API_SPEC.md's
# "Image Upload" and "File Upload Rules" validation sections.
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png"}
ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
MIN_IMAGE_WIDTH = 224
MIN_IMAGE_HEIGHT = 224


def validate_image_format(uploaded_file):
    """Rejects any file whose extension isn't JPG, JPEG, or PNG."""
    name = getattr(uploaded_file, "name", "") or ""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Unsupported image format. Use JPG, JPEG, or PNG.")


def validate_image_content_type(uploaded_file):
    """Rejects a declared MIME type outside JPEG/PNG, per
    GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md section 30.8's "MIME Type
    Validation" check -- distinct from validate_image_format's
    extension-only check. Skipped when the upload source doesn't report a
    content type at all (e.g. some non-browser clients), since
    validate_image_resolution's Pillow-based decode below still rejects
    anything that isn't a real image regardless.
    """
    content_type = getattr(uploaded_file, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValidationError("Unsupported image format. Use JPG, JPEG, or PNG.")


def validate_image_size(uploaded_file):
    """Rejects files larger than the 10 MB limit."""
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image size must not exceed 10 MB.")


def validate_image_resolution(uploaded_file):
    """Rejects corrupted files and images smaller than 224x224 pixels."""
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError):
        raise ValidationError("The uploaded file is not a valid image.")
    finally:
        uploaded_file.seek(0)

    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValidationError(
            f"Image resolution must be at least "
            f"{MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT} pixels."
        )


def validate_plant_image(uploaded_file):
    """Runs every image upload validation rule for
    POST /api/v1/predictions/analyze/, per REST_API_SPEC.md's upload rules
    and GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md section 30.8 (File Upload
    Security).
    """
    validate_image_format(uploaded_file)
    validate_image_content_type(uploaded_file)
    validate_image_size(uploaded_file)
    validate_image_resolution(uploaded_file)

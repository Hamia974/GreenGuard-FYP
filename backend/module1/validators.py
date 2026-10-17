from django.core.exceptions import ValidationError

# Per ai/API_CONTRACT.md's "POST /v1/predict" table: "image ... max 10 MB ·
# min 100 px per side · max 50 M pixels" and "Anything Pillow can decode ...
# There is no format allow-list: a file is accepted if it decodes and
# rejected with INVALID_IMAGE if it does not." Format/resolution/decodability
# are deliberately NOT re-validated here -- duplicating that logic would risk
# drifting from the live service's own rules (which accept far more formats
# than predictions/validators.py's JPG/PNG-only rule for Quick Scan). Only a fast, obvious size pre-check happens locally; everything
# else is left to the live service, whose documented error codes
# (module1/views.py's ERROR_RESPONSE_MAP) are translated into the farmer-
# facing response.
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024


def validate_disease_check_image(uploaded_file):
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image size must not exceed 10 MB.")

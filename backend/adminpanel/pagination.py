def paginate(queryset, *, page, limit):
    """Slice an already-filtered/ordered queryset for one page.

    Local copy of history.pagination.paginate's exact behavior, kept
    separate rather than imported cross-app -- same isolation precedent
    history.views already established for predictions.views's lookup
    helpers (reuse the model, not another app's view-layer internals).

    REST_API_SPEC.md section 8 documents "Pagination" as supported for the
    admin users/predictions lists but gives bare-array response examples
    with no pagination metadata (no total/total_pages/has_next), so this
    stays a plain offset/limit slice rather than DRF's PageNumberPagination,
    matching every other paginated endpoint in this project.
    """
    offset = (page - 1) * limit
    return queryset[offset : offset + limit]

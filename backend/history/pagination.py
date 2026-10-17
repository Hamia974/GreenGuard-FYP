def paginate(queryset, *, page, limit):
    """Slice an already-filtered/ordered queryset for one page.

    REST_API_SPEC.md section 6 documents ``page``/``limit`` as request
    inputs and requires pagination "when records exceed one page," but its
    response example is a bare ``data`` array with no pagination metadata
    (no total/total_pages/has_next). Per explicit product decision, the
    response stays minimal -- {success, message, data} -- rather than
    inventing a metadata contract the spec doesn't define, so this is a
    plain offset/limit slice rather than DRF's PageNumberPagination (which
    would also wrap ``data`` in its own envelope shape).
    """
    offset = (page - 1) * limit
    return queryset[offset : offset + limit]

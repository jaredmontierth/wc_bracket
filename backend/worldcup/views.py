from django.conf import settings
from django.http import HttpResponse


def frontend_app(request):
    index_file = settings.FRONTEND_DIST_DIR / "index.html"
    if not index_file.exists():
        return HttpResponse(
            "Frontend build not found. Run `npm run build --prefix frontend` first.",
            status=503,
            content_type="text/plain",
        )

    return HttpResponse(index_file.read_text(), content_type="text/html")

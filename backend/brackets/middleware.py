from django.http import JsonResponse


class DevCorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "http://localhost:5173"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    def process_exception(self, request, exception):
        if request.path.startswith("/api/"):
            return JsonResponse(
                {"error": f"{exception.__class__.__name__}: {exception}"},
                status=500,
            )
        return None

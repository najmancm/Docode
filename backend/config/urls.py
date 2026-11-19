
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def home(request):
    return JsonResponse({
        "message": "Welcome to DOCODE API!",
        "status": "success",
        "project": "DOCODE"
    })


urlpatterns = [
    path('admin/', admin.site.urls),

    # Main API
    path('api/', home),

    # Document upload API
    path('api/documents/', include('documents.urls')),

    # PDF extraction API
    path('api/extractor/', include('extractor.urls')),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

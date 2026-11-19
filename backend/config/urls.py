
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
    path('api/', home),
    path('api/documents/', include('documents.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

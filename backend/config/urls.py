from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static


def home(request):
    return JsonResponse({
        'message': 'TELESOM ACADEMY API',
        'status': 'success',
        'project': 'TELESOM ACADEMY',
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', home),
    path('api/auth/', include('accounts.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/extractor/', include('extractor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

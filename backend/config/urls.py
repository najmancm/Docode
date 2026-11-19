
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse


def home(request):
    return JsonResponse({
        "message": "Welcome to DOCODE API!",
        "status": "success",
        "project": "DOCODE"
    })


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', home),
]

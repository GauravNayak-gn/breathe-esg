from django.contrib import admin
from django.urls import path, include
from emissions.views import DashboardSummaryView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/ingest/', include('ingestion.urls')),
    path('api/emissions/', include('emissions.urls')),
    path('api/dashboard/', DashboardSummaryView.as_view(), name='dashboard'),
    path('api/auth/', include('accounts.urls')),
]
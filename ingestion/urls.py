from django.urls import path
from . import views

urlpatterns = [
    path('sap/', views.SAPUploadView.as_view(), name='ingest-sap'),
    path('utility/', views.UtilityUploadView.as_view(), name='ingest-utility'),
    path('travel/', views.TravelUploadView.as_view(), name='ingest-travel'),
    path('', views.IngestionListView.as_view(), name='ingestion-list'),
]
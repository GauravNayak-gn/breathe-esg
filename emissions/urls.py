from django.urls import path
from . import views

urlpatterns = [
    path('', views.EmissionListView.as_view(), name='emission-list'),
    path('<uuid:pk>/', views.EmissionDetailView.as_view(), name='emission-detail'),
    path('<uuid:pk>/approve/', views.EmissionApproveView.as_view(), name='emission-approve'),
    path('<uuid:pk>/reject/', views.EmissionRejectView.as_view(), name='emission-reject'),
    path('<uuid:pk>/lock/', views.EmissionLockView.as_view(), name='emission-lock'),
]
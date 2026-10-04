from django.urls import path

from . import views

urlpatterns = [
    path("admin/imports", views.ImportBatchListView.as_view(), name="import-batch-list"),
    path("admin/imports/batches/<int:pk>", views.ImportBatchDetailView.as_view(), name="import-batch-detail"),
    path("admin/imports/<slug:entity>", views.ImportUploadView.as_view(), name="import-upload"),
]

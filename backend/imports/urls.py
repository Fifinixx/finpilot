from django.urls import path

from . import views

urlpatterns = [
    path("", views.ImportBatchListView.as_view(), name="import-batch-list"),
    path("batches/<int:pk>", views.ImportBatchDetailView.as_view(), name="import-batch-detail"),
    path("<slug:entity>", views.ImportUploadView.as_view(), name="import-upload"),
]

from django.urls import path

from . import views

urlpatterns = [
    path("customers", views.CustomerListView.as_view(), name="customer-list"),
    path("customers/<str:pk>", views.CustomerDetailView.as_view(), name="customer-detail"),
    path("customers/<str:pk>/portfolio", views.CustomerPortfolioView.as_view(), name="customer-portfolio"),
    path("customers/<str:pk>/goals", views.CustomerGoalsView.as_view(), name="customer-goals"),
    path("goals/<str:goal_id>", views.GoalDetailView.as_view(), name="goal-detail"),
    path("customers/<str:pk>/transactions", views.CustomerTransactionsView.as_view(), name="customer-transactions"),
]

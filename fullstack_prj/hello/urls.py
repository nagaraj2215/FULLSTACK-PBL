from django.urls import path
from . import views

account_routes = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('register-success/', views.register_success, name='register_success'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
]

physical_health_routes = [
    path('physical/', views.physical_health, name='physical_health'),
    path('physical-tracker/', views.physical_health_tracker, name='physical_health_tracker'),
    path('physical/reset/', views.reset_physical_history, name='reset_physical_history'),
]

mental_health_routes = [
    path('mental/', views.mental_health, name='mental_health'),
    path('mental/reset/', views.reset_mental_history, name='reset_mental_history'),
]

suggestion_routes = [
    path('suggest-exercise/', views.suggest_exercise, name='suggest_exercise'),
    path('suggest-diet/', views.suggest_diet, name='suggest_diet'),
    path('sleep-improvement/', views.sleep_improvement, name='sleep_improvement'),
    path('stress-management/', views.stress_management, name='stress_management'),
]

urlpatterns = account_routes + physical_health_routes + mental_health_routes + suggestion_routes


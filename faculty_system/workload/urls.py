from django.urls import path
from . import views

urlpatterns = [
    # ⭐ Login System
    path('login/', views.faculty_login, name='login'),
    path('signup/', views.faculty_signup, name='signup'),
    path('logout/', views.faculty_logout, name='logout'),

    # ⭐ Dashboard
    # Use `home` wrapper to enforce redirect to login when unauthenticated
    path('', views.home, name='dashboard'),

    # ⭐ PDF Download (Login Required)
    path('download-pdf/', views.download_timetable_pdf, name='download_pdf'),
]
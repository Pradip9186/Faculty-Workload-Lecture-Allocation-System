from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from workload import views as workload_views

urlpatterns = [
    path('admin/logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='admin_logout'),
    path('admin/', admin.site.urls),

    # Root path: enforce authentication via `home` wrapper
    path('', workload_views.home, name='root'),

    # App routes (login, signup, logout, etc.)
    path('', include('workload.urls')),
]
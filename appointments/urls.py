from django.urls import path

from . import views

app_name = 'appointments'
urlpatterns = [
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('patient_home/', views.patient_home, name='patient_home'),
    path('doctor_home/', views.doctor_home, name='doctor_home'),
    path('add_visit/', views.add_visit, name='add_visit'),
]
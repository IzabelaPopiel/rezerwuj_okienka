from django.urls import path

from . import views

app_name = 'appointments'
urlpatterns = [
    path('login/', views.login, name='login'),
    path('register/', views.register, name='register'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout, name='logout'),
    path('add_visit/', views.add_visit, name='add_visit'),
    path('delete/<str:date_time>/', views.remove_visit, name='remove_visit'),
    path('add_doctor/', views.add_doctor, name='add_doctor'),
    path('home/alerts/', views.patient_alerts, name='patient_alerts'),
    path('home/search_visit', views.search_visit, name='search_visit'),
    path('home/search_visit/book/<str:visit_id>/', views.book_visit, name='book_visit'),
    path('home/alerts/delete/<str:specialty>/<str:city>/', views.remove_alert, name='remove_alert'),
    path('home/slots/delete/<str:visit_id>/', views.remove_slot, name='remove_slot'),
    path('home/slots/accept/<str:visit_id>/', views.accept_slot, name='accept_slot'),
]
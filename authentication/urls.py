from django.urls import path
from authentication import views


app_name = 'authentication'
urlpatterns = [
    path('', views.login),
    path('login/', views.login),
    path('register/', views.register)
]
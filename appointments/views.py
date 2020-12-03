from django.shortcuts import render, redirect


# Create your views here.
from appointments.forms import PatientForm


def register(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/appointments/login/')
        else:
            print(form.errors)
    return render(request, 'register.html')


def login(request):
    return render(request, 'login.html')
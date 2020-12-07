from django.shortcuts import render, redirect

# Create your views here.
from appointments.forms import PatientForm, LoginForm, VisitForm


def register(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/appointments/patient_home/')
        else:
            print(form.errors)
    else:
        form = PatientForm()
    return render(request, 'register.html', {'form': form})


def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            if form.data['user_type'] == 'patient':
                return redirect('/appointments/patient_home/')
            else:
                return redirect('/appointments/doctor_home/')
        else:
            print(form.errors)
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def patient_home(request):
    return render(request, 'patient_home.html')


def doctor_home(request):
    return render(request, 'doctor_home.html')


def add_visit(request):
    if request.method == 'POST':
        form = VisitForm(request.POST)
        # print(form.clean_date())

        if form.is_valid():
            form.save()
            return redirect('/appointments/doctor_home/')
        else:
            print(form.errors)
    else:
        form = VisitForm()
    return render(request, 'add_visit.html', {'form': form})

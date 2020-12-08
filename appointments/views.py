from django.shortcuts import render, redirect

# Create your views here.
from appointments.forms import PatientForm, LoginForm


def register(request):
    if is_already_logged(request):
        return render(request, redirect_template(request))
    elif request.method == 'POST':
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
    if is_already_logged(request):
        return render(request, redirect_template(request))
    elif request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            request.session['email'] = form.data['email']
            request.session['user_type'] = form.data['user_type']
            if form.data['user_type'] == 'patient':
                return redirect('/appointments/patient_home/')
            else:
                return redirect('/appointments/doctor_home/')
        else:
            print(form.errors)
    else:
        print('anyway')
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout(request):
    print('logout')
    if request.method == 'GET':
        request.session.flush()
    form = LoginForm()
    return render(request, 'login.html', {'form': form})


def patient_home(request):
    return render(request, 'patient_home.html')


def doctor_home(request):
    return render(request, 'doctor_home.html')


def is_already_logged(request):
    if request.session.get('email') and request.session.get('user_type'):
        return True
    return False


def redirect_template(request):
        if request.session.get('user_type') == 'patient':
            return 'patient_home.html'
        elif request.session.get('user_type') == 'doctor':
            return 'doctor_home.html'

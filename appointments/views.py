from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from appointments.forms import PatientForm, LoginForm, AddressForm, DoctorForm, VisitForm


def register(request):
    if is_already_logged(request):
        return render(request, redirect_template(request))
    elif request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/appointments/home/')
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
            return redirect('/appointments/home/')
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


def home(request):
    if is_already_logged(request):
        return render(request, redirect_template(request))
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form})


def is_already_logged(request):
    if request.session.get('email') and request.session.get('user_type'):
        return True
    return False


def redirect_template(request):
    if request.session.get('user_type') == 'patient':
        return 'patient_home.html'
    elif request.session.get('user_type') == 'doctor':
        return 'doctor_home.html'


def add_visit(request):
    # doctor id must be changed (session)
    doctor = "anna.nowak@mail.com"

    if request.method == 'POST':
        address_form = AddressForm(request.POST)
        visit_form = VisitForm(request.POST)

        if address_form.is_valid() and visit_form.is_valid():
            adress = address_form.save()

            address_name = adress.all().values().values_list()[0][1]

            visit_form.cleaned_data['address'] = address_name
            visit_form.cleaned_data['doctor'] = doctor
            visit_form.save()

            return redirect('/appointments/doctor_home/')
        else:
            print(address_form.errors, visit_form.errors)
    else:
        address_form = AddressForm()
        visit_form = VisitForm()
    return render(request, 'add_visit.html', {'address_form': address_form, 'visit_form': visit_form})


@login_required(login_url='/admin/login/')
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
        else:
            print(form.errors)
    else:
        form = DoctorForm()

    return render(request, 'add_doctor.html', {'form': form})

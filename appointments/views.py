from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from appointments.forms import PatientForm, LoginForm, AddressForm, DoctorForm, VisitForm
from appointments.models import Visit, Address, Patient


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
        template_name, context = redirect_template(request)
        return render(request, template_name, context=context)
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form})


def is_already_logged(request):
    if request.session.get('email') and request.session.get('user_type'):
        return True
    return False


def redirect_template(request):
    if request.session.get('user_type') == 'patient':
        context = {}
        template_name = 'patient_home.html'
    elif request.session.get('user_type') == 'doctor':
        visits = get_visits_for_doctor(request.session.get('email'))
        context = {'visits': visits}
        template_name = 'doctor_home.html'
    return template_name, context


def add_visit(request):
    doctor_mail = request.session.get('email')

    if request.method == 'POST':
        address_form = AddressForm(request.POST)
        visit_form = VisitForm(request.POST)

        if address_form.is_valid() and visit_form.is_valid():
            address = address_form.save()

            address_name = address.all().values().values_list()[0][1]

            visit_form.cleaned_data['address'] = address_name
            visit_form.cleaned_data['doctor'] = doctor_mail
            visit_form.save()

            return redirect('/appointments/home/')
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
            messages.success(request,
                             'Lekarz ' + form.data['first_name'] + ' ' + form.data['last_name'] + ' dodany prawidłowo')
        else:
            print(form.errors)
    else:
        form = DoctorForm()

    return render(request, 'add_doctor.html', {'form': form})


def get_visits_for_doctor(doctor_email):
    doctor_visits = Visit.objects.filter(doctor=doctor_email)
    list_v = list(doctor_visits.all().values().values_list())
    visits = []
    for v in list_v:

        if v[4] is not None:
            patient = Patient.objects.filter(email=v[4])
            patient_values = list(patient.all().values().values_list())
            first_name_patient = patient_values[0][1]
            last_name_patient = patient_values[0][2]
        else:
            first_name_patient = "---"
            last_name_patient = "---"

        clinic_name = v[3]
        address = Address.objects.filter(name=clinic_name).all().values().values_list()
        address_street = f"ul. %s" % (address[0][2])
        address_city = f"%s %s" % (address[0][4], address[0][3])
        time = v[1].time().strftime("%H:%M")
        date = v[1].date().strftime("%d/%m/%Y")

        visit = {'first_name_patient': first_name_patient, 'last_name_patient': last_name_patient,
                 'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_city,
                 'time': time, 'date': date }
        visits.append(visit)

    return visits

from bson import json_util
from django.contrib.auth.decorators import login_required
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.shortcuts import render, redirect
from appointments.forms import PatientForm, LoginForm, AddressForm, Doctor, DoctorForm, VisitForm, MedicalSpecialtyForm, \
    AlertForm
from appointments.models import Visit, Address, Patient, MedicalSpecialty, Alert
from django.contrib import messages
import json


def register(request):
    if is_already_logged(request):
        return render(request, redirect_template(request))
    elif request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.cleaned_data['slots'] = {'slots': []}
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
        context = {'home_page': 'active'}
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
            visit_pk = visit_form.save()

            if visit_pk:
                set_slots_for_patients(visit_pk, doctor_mail, address)
                messages.success(request, "Utworzono wizytę")
            else:
                messages.info(request, "Wizyta o podanych parametrach została już wcześniej utworzona")

            return redirect('/appointments/home/')
        else:
            print(address_form.errors, visit_form.errors)
    else:
        address_form = AddressForm()
        visit_form = VisitForm()
    return render(request, 'add_visit.html', {'address_form': address_form, 'visit_form': visit_form})


def set_slots_for_patients(visit_pk, doctor_email, address):
    doctor = Doctor.objects.get(email=doctor_email)
    specialty = doctor.medical_Specialty

    city = address.all().values().values_list()[0][3]

    alerts = Alert.objects.filter(specialty=specialty, city=city).values().values_list()
    patients_emails = []

    for a in alerts:
        p_email = a[3]
        patients_emails.append(p_email)

        patient = Patient.objects.filter(email=p_email)
        slots_json = patient.values().values_list()[0][6]
        slots = slots_json['slots']
        slots_list = list(slots)
        slots_list.append(visit_pk)
        d = {"slots": slots_list}
        patient.update(slots=parse_json(d))

    # here will be send emails


def remove_visit(request, date_time):
    doctor_mail = request.session.get('email')
    visit = Visit.objects.filter(doctor=doctor_mail, date=date_time)

    if request.method == 'POST':
        visit.delete()
        return redirect('/appointments/home/')
    else:

        return render(request, 'doctor_home.html')


def search_visit(request):
    medical_specialty_list = MedicalSpecialty.objects.all().values().values_list()
    select = ["Wybierz..."]
    for m_specialty in medical_specialty_list:
        select.append(m_specialty[1])
    visits = get_free_visits()
    # return render(request,'search_visit.html')
    context = {'visits': visits,'specialties': select}
    template_name = 'search_visit.html'
    return render(request, template_name, context)
    # return template_name, context
    # return render(request, 'search_visit.html')


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
        date_time = v[1].date().strftime("%Y-%m-%d") + " " + time

        visit = {'first_name_patient': first_name_patient, 'last_name_patient': last_name_patient,
                 'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_city,
                 'time': time, 'date': date, 'dateTime': date_time}
        visits.append(visit)

    return visits


def patient_alerts(request):
    medical_specialties_form = MedicalSpecialtyForm()
    alert_form = AlertForm()
    patient_mail = request.session.get('email')
    if request.method == 'POST':
        alert_form = AlertForm(request.POST)
        if alert_form.is_valid():
            specialty = alert_form.data['specialty']
            city = alert_form.data['city']
            patient = request.session.get('email')
            alert_form.cleaned_data['patient'] = patient
            result = alert_form.save()
            if result:
                messages.success(request, "Pomyślnie ustawiono alert dla specjalizacji: %s oraz miasta: %s"
                                 % (specialty, city))

        else:
            print(alert_form.errors)

    list_patient_alerts = Alert.objects.filter(patient=patient_mail)
    list_alerts = list(list_patient_alerts.all().values().values_list())
    alerts = []
    i = 0
    for a in list_alerts:
        i += 1
        alert = {'number': i, 'specialty': a[1], 'city': a[2]}
        alerts.append(alert)

    page = request.GET.get('page', 1)
    paginator = Paginator(alerts, 3)

    try:
        contacts = paginator.page(page)
    except PageNotAnInteger:
        contacts = paginator.page(1)
    except EmptyPage:
        contacts = paginator.page(paginator.num_pages)

    cards_text = []
    cards_text.append({'specialty': 'Ortopedia', 'doctor': 'Anna Nowak', 'datatime': '25.01.2021 godz. 10:00',
                       'address': 'ul. Kwiatowa 12, Wrocław'})
    cards_text.append({'specialty': 'Ortopedia', 'doctor': 'Jan Kowalski', 'datatime': '27.01.2021 godz. 13:25',
                       'address': 'ul. Zdrowa 81a, Wrocław'})

    context = {'alert_page': 'active', 'alert_form': alert_form,
               'medical_specialties_form': medical_specialties_form,
               'patient_alerts': contacts, 'cards': cards_text, }

    return render(request, 'patient_alerts.html', context=context)


def remove_alert(request, specialty, city):
    patient_mail = request.session.get('email')

    visit = Alert.objects.filter(patient=patient_mail, specialty=specialty, city=city)

    if request.method == 'POST':
        if visit.delete():
            messages.success(request, "Pomyślnie usunięto alert dla specjalizacji: %s oraz miasta: %s"
                             % (specialty, city))

        return redirect('/appointments/home/alerts/')
    else:

        return render(request, 'patient_alerts.html')


def search_visit(request):
    medical_specialty_list = MedicalSpecialty.objects.all().values().values_list()
    select = ["Wybierz..."]
    for m_specialty in medical_specialty_list:
        select.append(m_specialty[1])
    visits = get_free_visits()
    context = {'search_visit_page': 'active', 'visits': visits,'specialties': select}
    template_name = 'search_visit.html'
    return render(request, template_name, context)


def get_free_visits():
    visits = Visit.objects.filter(patient=None)
    list_v = list(visits.all().values().values_list())
    visits = []
    print('tutaj')
    for v in list_v:
        print(v)
        doctor = Doctor.objects.filter(email=v[2])
        doctor_values = list(doctor.all().values().values_list())
        print(doctor_values)
        # first_name_doctor = 'Jan'
        # last_name_doctor = 'Kowalski'
        first_name_doctor = doctor_values[0][1]
        last_name_doctor = doctor_values[0][2]
        medical_specialty = doctor_values[0][3]

        clinic_name = v[3]
        address = Address.objects.filter(name=clinic_name).all().values().values_list()
        address_street = f"ul. %s" % (address[0][2])
        address_city = f"%s %s" % (address[0][4], address[0][3])
        time = v[1].time().strftime("%H:%M")
        date = v[1].date().strftime("%d/%m/%Y")
        date_time = v[1].date().strftime("%Y-%m-%d") + " " + time

        visit = {'medical_specialty': medical_specialty, 'first_name_doctor': first_name_doctor, 'last_name_doctor': last_name_doctor,
                 'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_city,
                 'time': time, 'date': date, }
        visits.append(visit)

    return visits


def parse_json(data):
    return json.loads(json_util.dumps(data))
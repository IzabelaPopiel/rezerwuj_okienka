import json
from datetime import datetime

from bson import json_util, ObjectId
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from pymongo import MongoClient
import re

from appointments.forms import PatientForm, LoginForm, AddressForm, Doctor, DoctorForm, VisitForm, MedicalSpecialtyForm, \
    AlertForm, SearchVisitForm
from appointments.models import Visit, Address, Patient, MedicalSpecialty, Alert, Doctor
from django.contrib import messages
import json
import smtplib
from reservationsystem import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from reservationsystem import config


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
        template_name, context = redirect_template(request)
        return render(request, template_name, context=context)
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
        patient_mail = request.session.get('email')
        visits = get_patient_visits(patient_mail)
        context = {'home_page': 'active', 'visits': visits}
        template_name = 'patient_home.html'
    elif request.session.get('user_type') == 'doctor':
        visits = get_visits_for_doctor(request.session.get('email'))
        context = {'visits': visits}
        template_name = 'doctor_home.html'
    return template_name, context


def get_patient_visits(patient_mail):
    visits = []
    visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
    matching_visit = visit_collection.find({'patient': patient_mail})

    for v in matching_visit:
        now = datetime.now()
        if v['date'] > now:
            doctor = Doctor.objects.filter(email=v["doctor"])
            doctor_values = list(doctor.all().values().values_list())

            first_name_doctor = doctor_values[0][1]
            last_name_doctor = doctor_values[0][2]
            medical_specialty = doctor_values[0][3]

            clinic_name = v['address']
            address = Address.objects.filter(name=clinic_name).all().values().values_list()
            address_street = f"ul. %s" % (address[0][2])
            address_city = f"%s %s" % (address[0][4], address[0][3])
            time = v['date'].time().strftime("%H:%M")
            date = v['date'].date().strftime("%d/%m/%Y")
            # date_time = v[1].date().strftime("%Y-%m-%d") + " " + time
            visit_id = v["_id"]

            visit = {'medical_specialty': medical_specialty, 'first_name_doctor': first_name_doctor,
                     'last_name_doctor': last_name_doctor,
                     'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_city,
                     'time': time, 'date': date, 'visit_id': visit_id}
            visits.append(visit)

    return visits


def add_visit(request):
    doctor_mail = request.session.get('email')
    options = []
    addresses = Address.objects.all().values().values_list()
    for address in addresses:
        options.append(address[1])

    if request.method == 'POST':
        radio = request.POST['radios']
        address_name_flag = True
        address_form = AddressForm(request.POST)
        visit_form = VisitForm(request.POST)

        if radio == 'enter':
            if address_form.is_valid():
                address_name_flag = check_address_form(address_form)
                if address_name_flag:
                    address = address_form.save()
                    address_name = address.all().values().values_list()[0][1]
                else:
                    messages.warning(request, "Uzupełnij poprawnie pola adresu")

        else:
            address_name = request.POST['selectAddress']
            if address_name == '-----':
                address_name_flag = False
                messages.warning(request, "Wybierz placówkę")
            else:
                address = Address.objects.filter(name=address_name)

        if address_name_flag:
            if visit_form.is_valid():
                visit_form.cleaned_data['address'] = address_name
                visit_form.cleaned_data['doctor'] = doctor_mail
                visit_pk = visit_form.save()

                if visit_pk:
                    set_slots_for_patients(visit_pk, doctor_mail, address)
                    messages.success(request, "Utworzono nową wizytę")
                else:
                    messages.info(request, "Wizyta o podanych parametrach została wcześniej utworzona")
                return redirect('/appointments/home/')

            else:
                messages.warning(request, "Wybierz datę i godzinę")
                print(address_form.errors, visit_form.errors)

    else:
        address_form = AddressForm()
        visit_form = VisitForm()

    return render(request, 'add_visit.html', {'address_form': address_form, 'visit_form': visit_form,
                                              'options': options})


def check_address_form(address_form: AddressForm):
    result = True
    city = address_form.cleaned_data['city']
    if len(city) == 0 or not city.istitle():
        result = False
    postcode = address_form.cleaned_data['postcode']
    if len(postcode) == 0 or not re.match("^\d\d-\d\d\d$", postcode):
        result = False
    street = address_form.cleaned_data['street']
    if len(street) == 0 or not street.istitle():
        result = False
    name = address_form.cleaned_data['name']
    if len(name) == 0 or not name.istitle():
        result = False

    return result


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
        if 'slots' in slots_json:
            slots = slots_json['slots']
            slots_list = list(slots)
            slots_list.append(visit_pk)
            d = {"slots": slots_list}
        else:
            d = {"slots": [visit_pk]}
        patient.update(slots=parse_json(d))

    subject = "Nowe okienko!"
    body = f"Pojawiło się nowe okienko dla specjalności %s oraz miasta %s\n\nAby dokonać rezerwacji zaloguj się na " \
           f"swoje konto http://127.0.0.1:8000/appointments/home/alerts/" % (specialty, city)

    send_email(to_addresses=patients_emails, subject=subject, body=body)


def remove_slots_help(visit_id):
    booked = False
    patient_collection = Patient.objects.all().values('email')
    for p in patient_collection:

        patient = Patient.objects.filter(email=p['email'])
        patient_slots_str = getattr(patient.first(), 'slots')

        if patient_slots_str is not None:
            patient_slots = parse_json(patient_slots_str)["slots"]
            try:
                patient_slots.remove({'$oid': str(visit_id)})
                if patient.update(slots=parse_json({"slots": patient_slots})):
                    booked = True
            except ValueError:
                print("ValueError")
    return booked


def send_email(to_addresses, subject, body):
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    email_address = email.email_address
    password = email.password
    server.login(email_address, password)

    from_address = email_address

    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    text = msg.as_string()

    # for to_address in to_addresses:
    #     server.sendmail(from_address, to_address, text)

    # to_address = "youremailaddress@example.com"
    # server.sendmail(from_address, to_address, text)


def remove_visit(request, date_time):
    doctor_mail = request.session.get('email')
    visit = Visit.objects.get(doctor=doctor_mail, date=date_time)

    if request.method == 'POST':
        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        matching_visit = visit_collection.find_one({'doctor': doctor_mail, 'date': visit.date})
        visit_id = matching_visit["_id"]
        booked = remove_slots_help(visit_id)

        if booked:
            messages.success(request, "Pomyślnie usunięto wizytę")
        else:
            messages.error(request, "Wystąpił błąd, spróbuj ponownie")

        visit_collection.remove(matching_visit)
        return redirect('/appointments/home/')
    else:

        return render(request, 'doctor_home.html')


def remove_visit_send_email(visits_data_list):
    date_time = visits_data_list[0][1]
    doctor_email = visits_data_list[0][2]
    address_name = visits_data_list[0][3]
    patient_email = visits_data_list[0][4]

    doctors_data = Doctor.objects.filter(email=doctor_email).all().values().values_list()
    doctor = doctors_data[0][1] + " " + doctors_data[0][2]

    time = date_time.time().strftime("%H:%M")
    date = date_time.date().strftime("%d/%m/%Y")

    subject = "Odwołanie wizyty"
    body = f"Twoja wizyta w dniu %s o godzinie %s w %s u specjalisty %s została odwołana." \
           % (date, time, address_name, doctor)

    send_email(to_addresses=[patient_email], subject=subject, body=body)


def search_visit(request):
    if request.method == "POST":
        search_form = SearchVisitForm(request.POST)
        city = search_form.data['city']
        specialty = search_form.data['specialty']
        date = search_form.data['date']
        visits = get_free_visits(city, specialty, date)
    else:
        visits = get_free_visits(specialty=None, city=None, date=None)

    form = SearchVisitForm()
    context = {'visits': visits, 'search_visit_page': 'active', 'form': form}
    template_name = 'search_visit.html'
    return render(request, template_name, context)


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
        now = timezone.now()
        if v[1] > now:

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

    patient_slots_str = getattr(Patient.objects.filter(email=patient_mail).first(), 'slots')
    try:
        patient_slots = parse_json(patient_slots_str)["slots"]

        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        cards_text = []

        for slot in patient_slots:
            visit_id = slot['$oid']
            matching_visit = visit_collection.find_one({'_id': ObjectId(visit_id)})
            if matching_visit:
                date_format = matching_visit["date"].date().strftime("%Y-%m-%d") + " godz. " + matching_visit[
                    "date"].time().strftime("%H:%M")
                doctor = Doctor.objects.filter(email=matching_visit["doctor"]).first()
                doc_first_name = getattr(doctor, 'first_name')
                doc_last_name = getattr(doctor, 'last_name')
                doc_name = doc_first_name + " " + doc_last_name
                specialty = getattr(doctor, 'medical_Specialty')
                clinic_address = Address.objects.filter(name=matching_visit["address"]).first()
                full_address = matching_visit["address"] + " ul. " + getattr(clinic_address, 'street') + ", " + getattr(
                    clinic_address, 'city')

                cards_text.append(
                    {'specialty': specialty, 'doctor': doc_name, 'datatime': date_format,
                     'address': full_address, 'visit_id': visit_id})

        context = {'alert_page': 'active', 'alert_form': alert_form,
                   'medical_specialties_form': medical_specialties_form,
                   'patient_alerts': contacts, 'cards': cards_text, }
    except KeyError:
        context = {'alert_page': 'active', 'alert_form': alert_form,
                   'medical_specialties_form': medical_specialties_form,
                   'patient_alerts': contacts, 'cards': [], }

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

    return render(request, template_name, context)


def remove_slot(request, visit_id):
    patient_mail = request.session.get('email')
    patient = Patient.objects.filter(email=patient_mail)

    if request.method == 'POST':
        patient_slots_str = getattr(patient.first(), 'slots')
        patient_slots = parse_json(patient_slots_str)["slots"]
        patient_slots.remove({'$oid': visit_id})

        if patient.update(slots=parse_json({"slots": patient_slots})):
            messages.success(request, "Pomyślnie odrzucono okienko")
        else:
            messages.error(request, "Wystąpił błąd, spróbuj ponownie")

        return redirect('/appointments/home/alerts/')
    else:

        return render(request, 'patient_alerts.html')


def book_visit(request, visit_id):
    patient_mail = request.session.get('email')
    if request.method == 'POST':
        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        visit_collection.update_one({'_id': ObjectId(visit_id)}, {"$set": {"patient": patient_mail}})
        remove_slots_help(visit_id)
        return redirect('/appointments/home/search_visit')
    else:
        return render(request, 'search_visit.html')


def accept_slot(request, visit_id):
    patient_mail = request.session.get('email')

    if request.method == 'POST':
        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        matching_visit = visit_collection.find_one({'_id': ObjectId(visit_id)})

        if matching_visit['patient'] == None:
            visit_collection.update_one({'_id': ObjectId(visit_id)}, {"$set": {"patient": patient_mail}})
            booked = remove_slots_help(visit_id)

        if booked:
            messages.success(request, "Pomyślnie zarezerwowano okienko")
        else:
            messages.error(request, "Wystąpił błąd, spróbuj ponownie")

        return redirect('/appointments/home/alerts/')
    else:

        return render(request, 'patient_alerts.html')


def get_free_visits(city, specialty, date):
    visits = []
    visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
    matching_visit = visit_collection.find({'patient': None})

    for v in matching_visit:

        now = datetime.now()
        if v['date'] > now:
            doctor = Doctor.objects.filter(email=v["doctor"])
            doctor_values = list(doctor.all().values().values_list())

            first_name_doctor = doctor_values[0][1]
            last_name_doctor = doctor_values[0][2]
            medical_specialty = doctor_values[0][3]

            clinic_name = v['address']
            address = Address.objects.filter(name=clinic_name).all().values().values_list()
            address_street = f"ul. %s" % (address[0][2])
            address_city = address[0][3]
            address_code_city = f"%s %s" % (address[0][4], address_city)
            v_time = v['date'].time().strftime("%H:%M")
            v_date = v['date'].date().strftime("%d/%m/%Y")
            visit_id = v["_id"]

            visit = {'medical_specialty': medical_specialty, 'first_name_doctor': first_name_doctor,
                     'last_name_doctor': last_name_doctor,
                     'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_code_city,
                     'time': v_time, 'date': v_date, 'visit_id': visit_id}

            flag = True

            if date is not None and date != "":
                date = date[0:10]
                v_date = v['date'].date().strftime("%m/%d/%Y")
                if v_date != date:
                    flag = False
            if city is not None and city != "":
                if address_city != city:
                    flag = False
            if specialty is not None and specialty != "":
                if specialty != medical_specialty:
                    flag = False

            if flag:
                visits.append(visit)

    return visits


def parse_json(data):
    return json.loads(json_util.dumps(data))

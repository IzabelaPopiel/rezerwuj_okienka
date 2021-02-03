import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from bson import json_util, ObjectId
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import PageNotAnInteger, EmptyPage, Paginator
from django.shortcuts import render, redirect
from django.utils import timezone
from pymongo import MongoClient

from appointments.forms import PatientForm, LoginForm, AddressForm, DoctorForm, VisitForm, MedicalSpecialtyForm, \
    AlertForm, SearchVisitForm
from appointments.models import Visit, Address, Patient, Alert, Doctor
from reservationsystem import config
from reservationsystem import email


def register(request):
    """
    Registers patient.

    If patient is already logged in, he will be redirected to his homepage.
    If request method is POST and form is valid, it'll be saved and patient will be registered and redirected to homepage.
    In other cases patient register form will be rendered.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    render: Result of rendering result of redirect_template(request) - patient's home page
                    render: Result of redirecting to '/appointments/login/'
                    render: Result of rendering 'register.html' with patient's register form in context

    """
    if is_already_logged(request):
        return render(request, redirect_template(request))
    elif request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            form.cleaned_data['slots'] = {'slots': []}
            form.save()
            return redirect('/appointments/login/')
    else:
        form = PatientForm()
    return render(request, 'register.html', {'form': form})


def login(request):
    """
    Logins users.

    If user is already logged in, he will be redirected to his homepage.
    If request method is POST and form is valid, email and user type will be saved in session and user will be
    redirected to homepage.
    In other cases patient login form will be rendered.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    render: Result of rendering patient's or doctor's home page
                    render: Result of redirecting to '/appointments/home/'
                    render: Result of rendering 'login.html' with login form in context

    """
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
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout(request):
    """
    Logouts users.

    If request method is GET, session will be cleaned and login form will be rendered.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    render: Result of rendering 'login.html' with login form in context

    """
    if request.method == 'GET':
        request.session.flush()
    form = LoginForm()
    return render(request, 'login.html', {'form': form})


def home(request):
    """
    Renders proper homepage.

    If user is already logged in, checks to which template he should be recireted and then renders proper homepage.
    If user is not logged in, renders login page.


            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    render: Result of rendering proper homepage
                    render: Result of rendering 'login.html' with login form in context

    """
    if is_already_logged(request):
        template_name, context = redirect_template(request)
        return render(request, template_name, context=context)
    else:
        form = LoginForm()
        return render(request, 'login.html', {'form': form})


def is_already_logged(request):
    """
    Checks if user is already logged in.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    True: if email and user type are saved in session
                    False: if email or user type is not saved in session

    """
    if request.session.get('email') and request.session.get('user_type'):
        return True
    return False


def redirect_template(request):
    """
    Return propoer homepage temple name with context.
    Checks user type saved in session. If user type is patient, all his visits are put in context and returned
    together with patient_home.html template. If user type is doctor also all his visits are put in context
    and returned togther with doctor_home.html template.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    template_name: 'patient_home.html' ora 'doctor_home.html' depending on user type
                    context: dictionary with user's visit

    """
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
            visit_id = v["_id"]

            visit = {'medical_specialty': medical_specialty, 'first_name_doctor': first_name_doctor,
                     'last_name_doctor': last_name_doctor,
                     'clinic_name': clinic_name, 'address_street': address_street, 'address_city': address_city,
                     'time': time, 'date': date, 'visit_id': visit_id}
            visits.append(visit)

    return visits


def add_visit(request):
    """
    A function that supports adding new visits on the doctor's page.

    If request method is POST and the address is entered and the address form is valid and if the new address does
    not exist in the database, it will be saved.
    If request method is POST and the address is selected from the list or correctly entered and
    the date and time of the visit are correct, the new visit will be created and added to the database. And the slots
     will be sent to the patients.

            Parameters:
                request: Request

            Returns:
                render: Result of rendering 'add_visit.html' with visit's form and address's form and a list with
                addresses (address names) to be displayed in context

    """
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
                address_name_flag, message = check_address_form(address_form)
                if address_name_flag:
                    address = address_form.save()
                    address_name = address.all().values().values_list()[0][1]
                else:
                    messages.warning(request, message)

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

    else:
        address_form = AddressForm()
        visit_form = VisitForm()

    return render(request, 'add_visit.html', {'address_form': address_form, 'visit_form': visit_form,
                                              'options': options})


def check_address_form(address_form: AddressForm):
    """
    Checks that the data from the address form is correctly entered.

            Parameters:
                    address_form (AddressForm): address form

            Returns:
                    result (bool): true if the form is correct, false if not
                    message (str): description of the incorrectness

    """
    result = True
    message = ""
    city = address_form.cleaned_data['city']
    if len(city) == 0 or not city.istitle():
        message += "Nazwa miasta powinna zaczynać się wielką literą. "
        result = False
    street = address_form.cleaned_data['street']
    if len(street) == 0 or not street[0].isupper():
        message += "Nazwa ulicy powinna zaczynać się wielką literą. "
        result = False
    name = address_form.cleaned_data['name']
    if len(name) == 0:
        message += "Uzupełnij nazwę placówki. "
        result = False

    return result, message


def set_slots_for_patients(visit_pk, doctor_email, address):
    """
    Sets slots.

    Adds slot information to the slots of patients who have an alert set for this visit's parameters.
    And sends an email to those patients notifying them of the new slot.

            Parameters:
                visit_pk: visit primary key
                doctor_email: e-mail of the doctor
                address: visit address

    """
    doctor = Doctor.objects.get(email=doctor_email)
    specialty = doctor.medical_Specialty

    city = address.all().values().values_list()[0][3]

    alerts = Alert.objects.filter(specialty=specialty, city=city).values().values_list()
    patients_emails = []

    for alert in alerts:
        patient_email = alert[3]

        patients_emails.append(patient_email)

        patient = Patient.objects.filter(email=patient_email)
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
    body = f"Nowe okienko dla specjalności %s oraz miasta %s. Zaloguj się na swoje konto, żeby zarezerwować wizytę." \
           f"\n\nZespół Rezerwuj Okienka" % (specialty, city)

    send_email(to_addresses=patients_emails, subject=subject, body=body)


def remove_slots_help(visit_id):
    patient_collection = Patient.objects.all().values('email')
    for p in patient_collection:

        patient = Patient.objects.filter(email=p['email'])
        patient_slots_str = getattr(patient.first(), 'slots')

        if patient_slots_str is not None:
            patient_slots = parse_json(patient_slots_str)["slots"]
            try:
                patient_slots.remove({'$oid': str(visit_id)})
                patient.update(slots=parse_json({"slots": patient_slots}))
            except ValueError as error:
                pass


def send_email(to_addresses, subject, body):
    """
    Sends e-mails to patients.

            Parameters:
                to_addresses (list): e-mail addresses to which the message will be sent
                subject (str): e-mail subject
                body (str): e-mail text

    """
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

    for to_address in to_addresses:
        server.sendmail(from_address, to_address, text)


def remove_visit(request, date_time):
    doctor_mail = request.session.get('email')
    visit = Visit.objects.filter(doctor=doctor_mail, date=date_time)

    if request.method == 'POST':
        visits_data = list(visit.all().values().values_list())

        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        matching_visit = visit_collection.find_one({'doctor': doctor_mail, 'date': visits_data[0][1]})
        visit_id = matching_visit["_id"]

        result = visit_collection.remove(matching_visit)
        if result:
            remove_slots_help(visit_id)
            patient = visits_data[0][4]

            if patient is not None:
                remove_visit_send_email(visits_data_list=visits_data)

            messages.success(request, "Pomyślnie usunięto wizytę")
        else:
            messages.error(request, "Wizyta nie zostałą usunięta")

        return redirect('/appointments/home/')
    else:
        return render(request, 'doctor_home.html')


def remove_visit_send_email(visits_data_list):
    """
    Sends e-mail when visit is removed.

            Parameters:
                visits_data_list (list): data of a deleted visit; the list includes data such as: date, time, address,
                e-mail of the patient, e-mail of the doctor

    """
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
    """
    A function that supports searching for visits on the patient's page.

    If request method is POST, visits will be filtered.
    Otherwise, visits will not be filtered.

            Parameters:
                    request: Request

            Returns:
                    render: Result of rendering 'search_visit.html' with visit's search form and list of visits
                    to be displayed in context

    """
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
    """
    Admin registers doctor.

    If admin is not already logged in, he will be redirected to admin login page.
    If request method is POST and form is valid, it will be saved and doctor wil be registered. Doctor adding form
    will be rendered with success message.
    In other cases only doctor doctor adding form will be rendered.

            Parameters:
                    request (WSGIRequest): Request

            Returns:
                    render: Result of rendering proper homepage
                    render: Result of rendering 'add_doctor.html' with adding doctor form

    """
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,
                             'Lekarz ' + form.data['first_name'] + ' ' + form.data['last_name'] + ' dodany prawidłowo')
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
            if result is not None:
                messages.success(request, "Pomyślnie ustawiono alert dla specjalizacji: %s oraz miasta: %s"
                                 % (specialty, city))
            else:
                messages.warning(request, "Alert dla specjalizacji: %s oraz miasta: %s został już wcześniej ustawiony"
                                 % (specialty, city))

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

    cards_text = patient_slots_to_cards(patient_mail)

    context = {'alert_page': 'active', 'alert_form': alert_form,
               'medical_specialties_form': medical_specialties_form,
               'patient_alerts': contacts, 'cards': cards_text, }

    return render(request, 'patient_alerts.html', context=context)


def patient_slots_to_cards(patient_mail):
    """
    Converts patients slots list into easy to display dictionaries with slot's additional information .

    Takes all patient slots. For every slots finds visit with matching id. From visit takes date, doctor,
    and address. From doctor takes first name, last name and speciality. From address takes street and city.
    Final dictionary contains properly formatted speciality, doctor name, date, address and visit id.

            Parameters:
                    patient_mail (str): patient's mail

            Returns:
                    cards_text: list of dictionaries containing additional info about slots.

    """
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

    except KeyError:
        cards_text = []

    return cards_text


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
    """
    Removes slot.

    If patient is not interested in proposed slot and he do not want to see this slot card in his alert page, he can
    remove it.
    If request method is POST, all patient's slots are downloaded from database. Slot with given visit_id is removed
    and patient;s slots are updated. Alert page is rerendered with proper message.

            Parameters:
                    request (WSGIRequest): Request
                    visit_id: str

            Returns:
                    render: Result of rendering proper homepage
                    render: Result of rendering 'add_doctor.html' with adding doctor form

        """
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
        result = visit_collection.update_one({'_id': ObjectId(visit_id), 'patient': None},
                                             {"$set": {"patient": patient_mail}})
        if result.matched_count == 0:
            messages.warning(request, "Wizyta nie jest już dostępna")
        else:
            remove_slots_help(visit_id)
            messages.success(request, "Zarezerwowano wizytę")
        return redirect('/appointments/home/search_visit')
    else:
        return render(request, 'search_visit.html')


def accept_slot(request, visit_id):
    patient_mail = request.session.get('email')

    if request.method == 'POST':
        visit_collection = MongoClient(config.host)["appointmentSystem"]["appointments_visit"]
        result = visit_collection.update_one({'_id': ObjectId(visit_id), 'patient': None},
                                             {"$set": {"patient": patient_mail}})
        if result.matched_count == 0:
            messages.warning(request, "Wizyta nie jest już dostępna")
        else:
            remove_slots_help(visit_id)
            messages.success(request, "Zarezerwowano wizytę")
        return redirect('/appointments/home/alerts/')

    return render(request, 'patient_alerts.html')


def get_free_visits(city, specialty, date):
    """


    If parameters: city, specialty and date are None, the function returns all visits.

    """
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

            if is_visit_filter(city=city, specialty=specialty, date=date, visit=v, visit_city=address_city,
                               visit_doctor_specialty=medical_specialty):
                visit = {'medical_specialty': medical_specialty, 'first_name_doctor': first_name_doctor,
                         'last_name_doctor': last_name_doctor,
                         'clinic_name': clinic_name, 'address_street': address_street,
                         'address_city': address_code_city,
                         'time': v_time, 'date': v_date, 'visit_id': visit_id}
                visits.append(visit)

    return visits


def is_visit_filter(city, specialty, date, visit, visit_city, visit_doctor_specialty):
    """
    Checks if the visit data complies with the filtering parameters.

            Parameters:
                city: the first of the filtering parameters
                specialty: the second of the filtering parameters
                date: the third of the filtering parameters
                visit: visit
                visit_city: visit city address
                visit_doctor_specialty: doctor's specialty of the visit

            Returns:
                flag (bool): True if the visit meets the filter criteria, False if not

    """
    flag = True
    if date is not None and date != "":
        date = date[0:10]
        visit_date = visit['date'].date().strftime("%m/%d/%Y")
        if visit_date != date:
            flag = False
    if city is not None and city != "":
        if visit_city != city:
            flag = False
    if specialty is not None and specialty != "":
        if specialty != visit_doctor_specialty:
            flag = False
    return flag


def parse_json(data):
    return json.loads(json_util.dumps(data))

import bcrypt
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import TextInput, NumberInput, EmailInput
from appointments.models import Patient, Doctor, Visit, Address, MedicalSpecialty, Alert

form_class_style = "form-control"
form_class_style_radio = "form-check-input position-static"

USER_TYPES = (
    ("doctor", "Lekarz"),
    ("patient", "Pacjent")
)
DATEPICKER = {
    'type': 'text',
    'class': 'form-control',
    'id': 'datetimepicker4'
}

password_validator = RegexValidator(
    regex="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$",
    message=
    "Hasło musi zawierać przynjamniej jedną dużą literę, małą literę, cyfrę i znak specjalny")


def get_medical_specialties():
    medical_specialty_list = MedicalSpecialty.objects.all().values().values_list()
    choices = [("", "----------")]
    for m_specialty in medical_specialty_list:
        choices.append((m_specialty[1], m_specialty[1]))
    return choices


class AlertForm(forms.ModelForm):
    specialty = forms.ChoiceField(label="Specjalizacja", choices=list(get_medical_specialties()),
                                  widget=forms.Select(attrs={'class': form_class_style + " form-select"}))

    class Meta:
        model = Alert
        fields = '__all__'
        widgets = {
            'city': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz nazwę miasta..."}),
        }
        labels = {
            'city': 'Miasto'
        }

    def clean_city(self):
        city = self.cleaned_data['city']
        if not city:
            raise ValidationError("Należy wpisać nazwę miasta")
        return city

    def clean_specialty(self):
        specialty = self.cleaned_data['specialty']
        if not specialty:
            raise ValidationError("Należy wybrać specjalizację")
        return specialty

    def save(self, commit=True):
        alert = super(AlertForm, self).save(commit=False)

        alert.specialty = self.cleaned_data['specialty']
        alert.city = self.cleaned_data['city']
        alert.patient = self.cleaned_data['patient']

        if commit:
            x = Alert.objects.filter(specialty=alert.specialty, city=alert.city, patient=alert.patient)
            if x.count():
                alert = None
            else:
                alert.save()

        return alert


class MedicalSpecialtyForm(forms.Form):
    specialty = forms.ChoiceField(label="Specjalizacja", choices=list(get_medical_specialties()),
                                  widget=forms.Select(attrs={'class': form_class_style + " form-select"}))


class LoginForm(forms.ModelForm):
    user_type = forms.ChoiceField(label="Typ użytkownika",
                                  widget=forms.RadioSelect(attrs={'class': form_class_style_radio}), choices=USER_TYPES)

    class Meta:
        model = Patient
        fields = ['email', 'password']
        widgets = {
            'email': EmailInput(attrs={'class': form_class_style, 'placeholder': "wpisz adres email..."}),
            'password': forms.PasswordInput(attrs={'class': form_class_style, 'placeholder': "wpisz hasło..."})
        }
        labels = {
            'email': "Adres email",
            'password': "Hasło"
        }

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()

        user_type = self.cleaned_data['user_type']
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        user_found = False

        if user_type == 'patient':
            patient = Patient.objects.filter(email=email).first()
            if patient:
                hashed = getattr(patient, 'password')
                if bcrypt.hashpw(password.encode('utf-8'), hashed.encode('utf-8')) == hashed.encode('utf-8'):
                    user_found = True
        elif user_type == 'doctor':
            doctor = Doctor.objects.filter(email=email).first()
            if doctor:
                hashed = getattr(doctor, 'password')
                if bcrypt.hashpw(password.encode('utf-8'), hashed.encode('utf-8')) == hashed.encode('utf-8'):
                    user_found = True
        if not user_found:
            raise ValidationError("Adres email, hasło lub typ użytkownika nieprawidłowe")

        return cleaned_data


class PatientForm(forms.ModelForm):
    password = forms.CharField(label="Hasło", max_length=255, min_length=8, validators=[password_validator],
                               help_text="Musi zawierać co najmniej 8 znaków, dużą, małą literę, cyfrę i znak specjalny bez polskich liter.",
                               widget=forms.PasswordInput(attrs={'class': form_class_style,
                                                                 'placeholder': "wpisz hasło..."}))
    password_repeat = forms.CharField(label="Potwierdzenie hasła",
                                      widget=forms.PasswordInput(attrs={'class': form_class_style,
                                                                        'placeholder': 'wpisz ponownie hasło...'}),
                                      max_length=255, min_length=8)

    class Meta:
        model = Patient
        fields = '__all__'
        widgets = {
            'email': EmailInput(attrs={'class': form_class_style, 'placeholder': "wpisz adres email..."}),
            'first_name': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz imię..."}),
            'last_name': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz nazwisko..."}),
            'pesel': NumberInput(attrs={'class': form_class_style, 'placeholder': "wpisz PESEL..."})
        }
        labels = {
            'email': "Adres email",
            'first_name': "Imię",
            'last_name': "Nazwisko",
            'pesel': "PESEL"
        }
        help_texts = {
            'email': "Nie udostępnimy nikomu z zewnętrz twojego adresu email. Twoje dane są bezpieczne.",
            'pesel': "Nie udostępnimy nikomu z zewnętrz twojego numeru PESEL. Twoje dane są bezpieczne."
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        r = Patient.objects.filter(email=email)
        if r.count():
            raise ValidationError("Adres email jest już zajęty")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if not first_name.istitle():
            raise ValidationError("Imię musi rozpoczynać się wielką literą")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        if not last_name.istitle():
            raise ValidationError("Nazwisko musi rozpoczynać się wielką literą")
        return last_name

    def clean_pesel(self):
        pesel = self.cleaned_data['pesel']
        r = Patient.objects.filter(pesel=pesel)
        if r.count():
            raise ValidationError("PESEL jest już zajęty")
        return pesel

    def clean_password_repeat(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        if (password != password_repeat) and (password is not None):
            raise ValidationError("Hasła nie są identyczne")
        return password_repeat

    def save(self, commit=True):
        patient = super(PatientForm, self).save(commit=False)

        patient.first_name = self.cleaned_data['first_name']
        patient.last_name = self.cleaned_data['last_name']
        patient.pesel = self.cleaned_data['pesel']
        patient.email = self.cleaned_data['email']
        patient.slots = self.cleaned_data['slots']
        patient.password = bcrypt.hashpw(self.cleaned_data['password'].encode('utf-8'), bcrypt.gensalt()).decode(
            'utf-8')

        if commit:
            patient.save()

        return patient


class DateForm(forms.Form):
    date = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker1'
        })
    )


class VisitForm(forms.ModelForm):
    date = forms.DateTimeField(label="Data i godzina", input_formats=['%m/%d/%Y %I:%M %p'],
                               widget=forms.DateTimeInput(attrs={
                                   'class': 'form-control datetimepicker-input',
                                   'data-target': '#datetimepicker1'
                               }))

    class Meta:
        model = Visit
        fields = ['doctor', 'patient', 'address']

    def save(self, commit=True):
        visit = super(VisitForm, self).save(commit=False)
        visit.address = self.cleaned_data['address']
        visit.patient = self.cleaned_data['patient']
        visit.doctor = self.cleaned_data['doctor']
        visit.date = self.cleaned_data['date']

        visit_pk = None

        if commit:
            x = Visit.objects.filter(doctor=visit.doctor, date=visit.date)
            if not x.count():
                visit.save()
                visit_pk = visit.pk

        return visit_pk


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = '__all__'
        widgets = {
            'name': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz  nazwę placówki..."}),
            'street': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz ulicę..."}),
            'city': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz miasto..."}),
            'postcode': TextInput(
                attrs={'class': form_class_style, 'pattern': '^\d\d-\d\d\d$', 'placeholder': "wpisz kod pocztowy..."})
        }
        labels = {
            'name': "Nazwa placówki",
            'street': "Ulica",
            'city': "Miasto",
            'postcode': "Kod pocztowy"
        }

    def save(self, commit=True):
        address = super(AddressForm, self).save(commit=False)
        address.name = self.cleaned_data['name']
        address.street = self.cleaned_data['street']
        address.city = self.cleaned_data['city']
        address.postcode = self.cleaned_data['postcode']

        if commit:
            x = Address.objects.filter(name=address.name)
            if x.count():
                address = x
            else:
                address.save()
                address = Address.objects.filter(name=address.name)

        return address


class DoctorForm(forms.ModelForm):
    password = forms.CharField(label="Hasło", max_length=255, min_length=8, validators=[password_validator],
                               help_text="Musi zawierać co najmniej 8 znaków, dużą, małą literę, cyfrę i znak specjalny bez polskich liter.",
                               widget=forms.PasswordInput(attrs={'class': form_class_style,
                                                                 'placeholder': "wpisz hasło..."}))
    password_repeat = forms.CharField(label="Potwierdzenie hasła",
                                      widget=forms.PasswordInput(attrs={'class': form_class_style,
                                                                        'placeholder': 'wpisz ponownie hasło...'}),
                                      max_length=255, min_length=8)

    medical_Specialty = forms.ChoiceField(label="Specjalizacja", choices=list(get_medical_specialties()),
                                          widget=forms.Select(attrs={'class': form_class_style + " form-select"}))

    class Meta:
        model = Doctor
        fields = ['first_name', 'last_name', 'email', 'password']
        widgets = {
            'first_name': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz imię..."}),
            'last_name': TextInput(attrs={'class': form_class_style, 'placeholder': "wpisz nazwisko..."}),
            'email': EmailInput(attrs={'class': form_class_style, 'placeholder': "wpisz adres email..."}),
        }
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'email': 'Adres email',
        }

    def clean_password_repeat(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        if (password != password_repeat) and (password is not None):
            raise ValidationError("Podane hasła muszą być takie same")
        return password_repeat

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        r = Doctor.objects.filter(email=email)
        if r.count():
            raise ValidationError("Podany adres email jest zajęty")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        if not first_name.istitle():
            raise ValidationError("Imię musi rozpoczynać się wielką literą")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        if not last_name.istitle():
            raise ValidationError("Nazwisko musi rozpoczynać się wielką literą")
        return last_name

    def save(self, commit=True):
        doctor = super(DoctorForm, self).save(commit=False)
        doctor.first_name = self.cleaned_data['first_name']
        doctor.last_name = self.cleaned_data['last_name']
        doctor.email = self.cleaned_data['email']
        doctor.medical_Specialty = self.cleaned_data['medical_Specialty']
        doctor.password = bcrypt.hashpw(self.cleaned_data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        if commit:
            doctor.save()

        return doctor


class SearchVisitForm(forms.Form):
    specialty = forms.ChoiceField(label="Specjalizacja", required=False, choices=list(get_medical_specialties()),
                                  widget=forms.Select(attrs={'class': form_class_style + " form-select"}))
    city = forms.CharField(label="Miasto", required=False, widget=forms.TextInput(attrs={'class': form_class_style,
                                                                                         'placeholder': "wpisz miasto..."}))
    date = forms.DateTimeField(label="Data i godzina", required=False, input_formats=['%m/%d/%Y %I:%M %p'],
                               widget=forms.DateTimeInput(attrs={
                                   'class': 'form-control datetimepicker-input',
                                   'data-target': '#datetimepicker1'
                               }))

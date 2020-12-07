from django import forms
from django.core.exceptions import ValidationError
from django.forms import TextInput, NumberInput, EmailInput, ChoiceField, RadioSelect

from appointments.models import Patient, Doctor

form_class_style = "form-control"
form_class_style_radio = "form-check-input position-static"
OPTIONS = (
    ("S 1", "S 1"),
    ("S 2", "S 2"),
    ("S 3", "S 3"),
)
USER_TYPES = (
    ("doctor", "Lekarz"),
    ("patient", "Pacjent")
)


class MedicalSpecialtyForm(forms.Form):
    specialty = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple(
        attrs={'class': 'custom-control-checkbox'}), choices=OPTIONS)


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

        if user_type == 'patient':
            correct_email_password = Patient.objects.filter(email=email, password=password)
        elif user_type == 'doctor':
            correct_email_password = Doctor.objects.filter(email=email, password=password)
        if not correct_email_password.count():
            raise ValidationError("Email or password not correct")

        return cleaned_data


class PatientForm(forms.ModelForm):
    password = forms.CharField(label="Hasło", max_length=255, min_length=8,
                               help_text="Musi zawierać co najmniej 8 znaków w tym znaki specjalne.",
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
        print(email)
        r = Patient.objects.filter(email=email)
        if r.count():
            raise ValidationError("Email already exists")
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data['first_name']
        print(first_name)
        if not first_name.istitle():
            raise ValidationError("First name must start with capital letter")
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data['last_name']
        print(last_name)
        if not last_name.istitle():
            raise ValidationError("Last name must start with capital letter")
        return last_name

    def clean_pesel(self):
        pesel = self.cleaned_data['pesel']
        print(pesel)
        r = Patient.objects.filter(pesel=pesel)
        if r.count():
            raise ValidationError("PESEL already exists")
        return pesel

    def clean_password_repeat(self):
        password = self.cleaned_data.get('password')
        password_repeat = self.cleaned_data.get('password_repeat')
        print(password)
        print(password_repeat)
        if password != password_repeat:
            raise ValidationError("Passwords don't match")
        return password_repeat

    def save(self, commit=True):
        patient = super(PatientForm, self).save(commit=False)

        patient.first_name = self.cleaned_data['first_name']
        patient.last_name = self.cleaned_data['last_name']
        patient.pesel = self.cleaned_data['pesel']
        patient.email = self.cleaned_data['email']
        patient.password = self.cleaned_data['password']

        if commit:
            patient.save()

        return patient

from django.forms import Form, Select, CharField, ChoiceField, EmailField, DateTimeField, \
                    DateField, ModelForm, DateInput, HiddenInput, TextInput, PasswordInput
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class LoginForm(Form):
    username = CharField(
        widget=TextInput(attrs={'class': 'registerforms', 'placeholder': 'username'}),
        label='',
    )
    password = CharField(
        widget=PasswordInput(attrs={'class': 'registerforms', 'placeholder': 'Password'}),
        label='',
    )

class SignUpForm(UserCreationForm):
    username = CharField(max_length=254, help_text='Required. Input a Username.',
                        widget=TextInput(attrs={"type": "username", "class": "form-control",
                                                "id": "exampleInputUsername1"
                                        }
            )
    )
    first_name = CharField(max_length=30, required=False, help_text='Optional.',
                        widget=TextInput(attrs={"type": "firstname", "class": "form-control",
                                                "id": "exampleInputFirstname1", "placeholder": "optional"
                                        }
                )
    )
    last_name = CharField(max_length=30, required=False, help_text='Optional.',
                        widget=TextInput(attrs={"type": "lastname", "class": "form-control",
                                                "id": "exampleInputLastname1", "placeholder": "optional"
                                        }
                )
    )
    email = EmailField(max_length=254, help_text='Required.',
                        widget=TextInput(attrs={"type": "email", "class": "form-control",
                                                "id": "exampleInputEmail1",
                                        }
            )
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', )

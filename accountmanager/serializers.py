from django.contrib.auth.models import User
from rest_framework.serializers import HyperlinkedModelSerializer


class UserSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = (
                    "id", "last_login", "is_superuser", "username", "first_name",
                    "last_name", "email", "is_staff", "is_active", "date_joined"
        )

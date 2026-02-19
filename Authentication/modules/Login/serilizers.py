from aquilia.serializers import ModelSerializer
from models.users import Users


class UserSerilizer(ModelSerializer):
    class Meta:
        model = Users
        fields = "__all__"

    def create(self, data):
        return Users.create(**data)
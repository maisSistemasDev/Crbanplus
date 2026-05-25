from core.models import User, ExtraData

class UserInstance:
    def __init__(self, user: User):
        self.user = user
        self.name = user.get_full_name()
        self.email = user.email
        self.cpf = user.cpf
        self.extra_data = self._load_extra_data()
        self.phone = None
        self.pix_key = None
        self.pix_type = None
        self.birth_date = None
        self.role = user.role
        self.leader = user.leader
        self.company = user.company if user.company else None
        self.is_active = user.is_active
        self.is_staff = user.is_staff
        self.is_superuser = user.is_superuser if user.is_superuser else False
    
    def _load_extra_data(self) -> ExtraData:
        try:
            extra_data = ExtraData.objects.get(user=self.user)
            self.pix_key = extra_data.pix_key
            self.pix_type = extra_data.pix_type
            self.birth_date = extra_data.birth_date
            return extra_data
        except ExtraData.DoesNotExist:
            return None

    def __str__(self):
        return f"UserInstance(user={self.user.id}, name={self.name}, email={self.email}, cpf={self.cpf}, extra_data={self.extra_data})"
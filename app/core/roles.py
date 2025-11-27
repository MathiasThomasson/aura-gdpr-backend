from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"


ALLOWED_ROLES = {Role.OWNER.value, Role.ADMIN.value, Role.USER.value}

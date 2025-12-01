from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    EDITOR = "editor"
    VIEWER = "viewer"


ALLOWED_ROLES = {
    Role.OWNER.value,
    Role.ADMIN.value,
    Role.USER.value,
    Role.EDITOR.value,
    Role.VIEWER.value,
}

from app.core.exceptions import EmailDejaUtilise
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def register(self, *, email: str, password: str, display_name: str) -> User:
        if self.users.get_by_email(email):
            raise EmailDejaUtilise("Un compte existe déjà avec cet email")
        return self.users.add(
            User(email=email, display_name=display_name,
                 password_hash=hash_password(password))
        )

    def authenticate(self, *, email: str, password: str) -> User | None:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from passlib.hash import bcrypt

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)

    games = relationship("Game", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

    @property
    def password(self):
        raise AttributeError("Password is write-only.")

    @password.setter
    def password(self, password: str):
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        self.password_hash = bcrypt.hash(password)

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return bcrypt.verify(password, self.password_hash)

    def set_password(self, password: str):
        self.password = password


class Game(Base):
    __tablename__ = "games"

    TIME_CONTROLS = ("bullet", "blitz", "rapid", "classical")
    GAME_TYPES = ("online", "otb")

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_color = Column(Boolean, nullable=False)  # True = white
    result = Column(String(7), nullable=False)  # "1-0", "0-1", "1/2-1/2"
    opponent_rating = Column(Integer)
    pgn = Column(Text, nullable=False)
    time_control = Column(Enum(*TIME_CONTROLS, name="time_control_enum"), nullable=False)
    game_type = Column(Enum(*GAME_TYPES, name="game_type_enum"), nullable=False)
    description = Column(String(255))
    created_at = Column(DateTime, default=func.now())

    owner = relationship("User", back_populates="games")

from database import Base, engine
from models import User, Game, Analysis

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables have been created.")

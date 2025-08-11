from DBModels import Base
from database import engine

def create_database():
    """Создание всех таблиц в базе данных"""
    print("Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("Таблицы созданы успешно!")

if __name__ == "__main__":
    create_database()

from sqlalchemy.orm import sessionmaker
from database import engine
from DBModels import Building, Phone, Activity, Organization

Session = sessionmaker(bind=engine)


def seed_data():
    """Заполнение базы данных тестовыми данными"""
    session = Session()

    try:
        # Создание зданий
        building1 = Building(
            address="г. Москва, ул. Блюхера, 32/1",
            latitude=55.751244,
            longitude=37.618423
        )
        building2 = Building(
            address="г. Москва, ул. Ленина, 1, офис 3",
            latitude=55.753215,
            longitude=37.620393
        )
        building3 = Building(
            address="г. Москва, ул. Красная, 3, офис 1",
            latitude=55.752166,
            longitude=37.621001
        )

        session.add_all([building1, building2])
        session.commit()

        # Создание телефонов
        phone1 = Phone(number="2222222")
        phone2 = Phone(number="3333333")
        phone3 = Phone(number="89236661313")

        session.add_all([phone1, phone2, phone3])
        session.commit()

        # Создание деятельностей (древовидная структура)
        food = Activity(name="Еда")
        session.add(food)
        session.commit()

        meat = Activity(name="Мясная продукция", parent_id=food.id)
        dairy = Activity(name="Молочная продукция", parent_id=food.id)

        cars = Activity(name="Автомобили")
        session.add(cars)
        session.commit()

        trucks = Activity(name="Грузовые", parent_id=cars.id)
        passenger = Activity(name="Легковые", parent_id=cars.id)

        session.add_all([meat, dairy, trucks, passenger])
        session.commit()

        parts = Activity(name="Запчасти", parent_id=passenger.id)
        accessories = Activity(name="Аксессуары", parent_id=passenger.id)

        session.add_all([parts, accessories])
        session.commit()

        # Создание организаций
        org1 = Organization(
            name='ООО "Рога и Копыта"',
            building_id=building1.id
        )
        org1.phones = [phone1, phone2, phone3]
        org1.activities = [meat, dairy]

        org2 = Organization(
            name='АО "Автозапчасти+"',
            building_id=building2.id
        )
        org2.phones = [phone2]
        org2.activities = [parts, accessories]

        session.add_all([org1, org2])
        session.commit()

        print("Тестовые данные успешно добавлены!")

    except Exception as e:
        session.rollback()
        print(f"Ошибка при добавлении данных: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_data()

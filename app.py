import uvicorn
from fastapi import Request, Header
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_
import math

from ExtFastAPI import ModFastAPI
from ExtLogger import logger
from APIDataModels import set_response_model, \
    ActivitySearchOrganizationResponse, ActivitySearchOrganization, OrganizationSearchCoordinateRadius, \
    OrganizationSearchCoordinateRadiusResponse, BuildingSearchOrganizationResponse, BuildingSearchOrganization, \
    OrganizationSearchCoordinateRectangleResponse, OrganizationSearchCoordinateRectangle, OrganizationSearchIdResponse, \
    OrganizationSearchId, OrganizationSearchName, OrganizationSearchNameResponse, BuildingListAllResponse, \
    OrganizationInfo
from postgres_init.database import DATABASE_URL
from postgres_init.DBModels import Organization, Building, Phone, Activity, organization_activities


ENV_VARS = os.getenv("ENV_VARS", default=".env")

try:
    load_dotenv(ENV_VARS)
except Exception as err:
    print(f"Failed to load '{ENV_VARS}' file: {err}")

API_HOST = os.getenv("API_HOST", default='0.0.0.0')
API_PORT = os.getenv("API_PORT", default=8000)

APP_TITLE = os.getenv("APP_TITLE", default='Справочник Организаций, Зданий, Деятельности.')
APP_VERSION = os.getenv("APP_VERSION", default='v1.0.0')
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", default="REST API справочника Организаций, Зданий, Деятельности.")
APP_LOGO = os.getenv("APP_LOGO", default='https://i.pinimg.com/originals/e8/2e/c4/e82ec4007494891eac542ac464b9ec30.png')

EXAMPLE_ACCESS_TOKEN = "ABC123"


app = ModFastAPI(title=APP_TITLE, version=APP_VERSION, description=APP_DESCRIPTION, logo=APP_LOGO)

async_engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=async_engine)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Функция проверки токена авторизации намеренно вынесена отдельно. Реализация RBAC зависит
# от конкретного случая и здесь служит только для демонстрационных целей.
async def check_bearer_token(token: str) -> (bool, str):
    """
    Валидирует токен доступа.

    :param token: Токен авторизации.
    :return: Кортеж из булевого значения (True - доступ разрешен, False - запрещен) и строки с описанием результата
    """
    if token == EXAMPLE_ACCESS_TOKEN:
        return False, "Access denied"
    return True, "Access granted"

# По-хорошему, функцию нужно выносить отдельно, но не стал дробить проект еще больше.
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Вычисляет расстояние между двумя точками на Земле по формуле гаверсина.

    Args:
        lat1, lon1: Координаты первой точки (широта, долгота)
        lat2, lon2: Координаты второй точки (широта, долгота)

    Returns:
        Расстояние в километрах
    """
    # Радиус Земли в километрах
    R = 6371.0

    # Переводим градусы в радианы
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Разности координат
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    # Формула гаверсина
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# По-хорошему, функцию нужно выносить отдельно, но не стал дробить проект еще больше.
def km_to_degrees(km: float, latitude: float) -> tuple[float, float]:
    """
    Преобразует километры в градусы с учетом широты.

    Args:
        km: Расстояние в километрах
        latitude: Широта для корректировки расчета долготы

    Returns:
        Кортеж (смещение по широте в градусах, смещение по долготе в градусах)
    """
    # Один градус широты примерно равен 111.32 км
    lat_degrees = km / 111.32

    # Один градус долготы зависит от широты
    # На экваторе 1° долготы = ~111.32 км, но уменьшается к полюсам
    lon_degrees = km / (111.32 * math.cos(math.radians(latitude))) if math.cos(
        math.radians(latitude)) != 0 else km / 111.32

    return lat_degrees, lon_degrees


@app.post("/building/search/organization", response_model_exclude_none=True,
          response_model=BuildingSearchOrganizationResponse, name="Поиск организаций в здании", tags=["Здания"])
async def building_search_organization(
        request: Request, data: BuildingSearchOrganization, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск всех организаций находящихся в конкретном здании.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        # Сначала проверяем, существует ли здание с указанным ID
        building_query = select(Building).where(Building.id == data.building_id)
        building_result = await db.execute(building_query)
        building = building_result.scalar_one_or_none()

        if not building:
            logger.warning(f"Building with ID {data.building_id} not found")
            response = set_response_model(
                code=22,
                message=f"Здание с ID {data.building_id} не найдено"
            )
            return JSONResponse(status_code=200, content=response, media_type='application/json')

        # Получаем все организации в указанном здании
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).where(Organization.building_id == data.building_id)

        result = await db.execute(query)
        organizations = result.scalars().all()

        # Преобразуем данные в формат ответа
        organizations_info = []
        for organization in organizations:
            organization_info = OrganizationInfo(
                id=organization.id,
                name=organization.name,
                phones=[int(phone.number) for phone in organization.phones],
                activities=[activity.name for activity in organization.activities],
                address=organization.building.address
            )
            organizations_info.append(organization_info.model_dump())

        response = set_response_model(
            code=0,
            message=f"Найдено {len(organizations_info)} организаций в здании",
            organization=organizations_info,
            qty=len(organizations_info)
        )

        logger.info(f"Successfully found {len(organizations_info)} organizations in building ID {data.building_id}")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organizations in building ID {data.building_id}: {str(e)}")
        response = set_response_model(
            code=53,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.get("/building/list/all", response_model_exclude_none=True, response_model=BuildingListAllResponse,
         name="Список всех зданий", tags=["Здания"])
async def building_list_all(
        request: Request, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Список всех зданий в базе данных.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        # Получаем все здания из базы данных
        query = select(Building)
        result = await db.execute(query)
        buildings = result.scalars().all()

        # Преобразуем данные в формат ответа
        buildings_info = []
        for building in buildings:
            building_info = {
                "id": building.id,
                "address": building.address,
                "latitude": building.latitude,
                "longitude": building.longitude
            }
            buildings_info.append(building_info)

        response = set_response_model(
            code=0,
            message=f"Найдено {len(buildings_info)} зданий",
            building=buildings_info
        )

        logger.info(f"Successfully retrieved {len(buildings_info)} buildings from database")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error retrieving buildings list: {str(e)}")
        response = set_response_model(
            code=52,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.post("/activity/search/organization", response_model_exclude_none=True,
          response_model=ActivitySearchOrganizationResponse, name="Поиск организаций по деятельности", tags=["Организации"])
async def activity_search_organization(
        request: Request, data: ActivitySearchOrganization, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск всех организаций, которые относятся к указанному виду деятельности.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        async def get_activity_ids_with_children(activity_name: str, max_depth: int = 3) -> set:
            """
            Получает ID всех видов деятельности по названию, включая дочерние до указанной глубины.

            Args:
                activity_name: Название искомого вида деятельности
                max_depth: Максимальная глубина вложенности (по умолчанию 3)

            Returns:
                Множество ID всех найденных видов деятельности
            """
            activity_ids = set()

            # Находим все виды деятельности с указанным названием
            base_query = select(Activity).where(Activity.name.ilike(f"%{activity_name}%"))
            base_result = await db.execute(base_query)
            base_activities = base_result.scalars().all()

            if not base_activities:
                return activity_ids

            # Добавляем найденные базовые виды деятельности
            for activity in base_activities:
                activity_ids.add(activity.id)

            # Рекурсивно ищем дочерние виды деятельности
            async def find_children(parent_ids: set, current_depth: int):
                if current_depth >= max_depth or not parent_ids:
                    return

                # Находим всех детей для текущего уровня
                children_query = select(Activity).where(Activity.parent_id.in_(parent_ids))
                children_result = await db.execute(children_query)
                children = children_result.scalars().all()

                next_level_ids = set()
                for child in children:
                    activity_ids.add(child.id)
                    next_level_ids.add(child.id)

                # Рекурсивно ищем детей следующего уровня
                await find_children(next_level_ids, current_depth + 1)

            # Начинаем поиск дочерних элементов
            base_ids = {activity.id for activity in base_activities}
            await find_children(base_ids, 1)

            return activity_ids

        activity_ids = await get_activity_ids_with_children(data.activity)

        if not activity_ids:
            logger.warning(f"No activities found matching '{data.activity}'")
            response = set_response_model(
                code=23,
                message=f"Виды деятельности с названием '{data.activity}' не найдены",
                organization=[],
                qty=0
            )
            return JSONResponse(status_code=200, content=response, media_type='application/json')

        organizations_query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).join(
            organization_activities, Organization.id == organization_activities.c.organization_id
        ).where(
            organization_activities.c.activity_id.in_(activity_ids)
        ).distinct()

        result = await db.execute(organizations_query)
        organizations = result.scalars().all()

        organizations_info = []
        organization_ids_seen = set()

        for organization in organizations:
            if organization.id not in organization_ids_seen:
                organization_ids_seen.add(organization.id)

                organization_info = OrganizationInfo(
                    id=organization.id,
                    name=organization.name,
                    phones=[int(phone.number) for phone in organization.phones],
                    activities=[activity.name for activity in organization.activities],
                    address=organization.building.address
                )
                organizations_info.append(organization_info.model_dump())

        response = set_response_model(
            code=0,
            message=f"Найдено {len(organizations_info)} организаций по виду деятельности '{data.activity}' (включая {len(activity_ids)} связанных видов деятельности)",
            organization=organizations_info,
            qty=len(organizations_info)
        )

        logger.info(
            f"Successfully found {len(organizations_info)} organizations for activity '{data.activity}' with {len(activity_ids)} related activity types")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organizations by activity '{data.activity}': {str(e)}")
        response = set_response_model(
            code=54,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.post("/organization/search/coordinate/radius", response_model_exclude_none=True,
          response_model=OrganizationSearchCoordinateRadiusResponse, name="Поиск в радиусе", tags=["Организации"])
async def organization_search_coordinate_radius(
        request: Request, data: OrganizationSearchCoordinateRadius, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск организаций, которые находятся в заданном радиусе относительно указанной точки на карте.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        radius_km = data.radius

        # Вычисляем границы поиска в градусах для предварительной фильтрации
        lat_offset, lon_offset = km_to_degrees(radius_km, data.latitude)

        min_lat = data.latitude - lat_offset
        max_lat = data.latitude + lat_offset
        min_lon = data.longitude - lon_offset
        max_lon = data.longitude + lon_offset

        # Получаем все организации в приблизительном квадрате для предварительной фильтрации
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).join(Building).where(
            and_(
                Building.latitude >= min_lat,
                Building.latitude <= max_lat,
                Building.longitude >= min_lon,
                Building.longitude <= max_lon
            )
        )

        result = await db.execute(query)
        organizations = result.scalars().all()

        # Фильтруем организации по точному расстоянию
        organizations_info = []
        for organization in organizations:
            # Вычисляем точное расстояние в километрах
            distance_km = calculate_distance(
                data.latitude, data.longitude,
                organization.building.latitude, organization.building.longitude
            )

            # Проверяем, находится ли организация в заданном радиусе
            if distance_km <= radius_km:
                organization_info = OrganizationInfo(
                    id=organization.id,
                    name=organization.name,
                    phones=[int(phone.number) for phone in organization.phones],
                    activities=[activity.name for activity in organization.activities],
                    address=organization.building.address
                )
                organizations_info.append((organization_info.model_dump(), distance_km))

        # Сортируем результаты по расстоянию (ближайшие сначала)
        organizations_info.sort(key=lambda x: x[1])
        print(f"organizations_info: {organizations_info}")

        # Извлекаем только информацию об организациях (без расстояний)
        organizations_info_sorted = [org_info for org_info, _ in organizations_info]

        response = set_response_model(
            code=0,
            message=f"Найдено {len(organizations_info_sorted)} организаций в радиусе {radius_km} км от точки ({data.latitude}, {data.longitude})",
            organization=organizations_info_sorted,
            qty=len(organizations_info_sorted)
        )

        logger.info(
            f"Successfully found {len(organizations_info_sorted)} organizations within {radius_km} km radius from ({data.latitude}, {data.longitude})")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organizations by coordinate radius: {str(e)}")
        response = set_response_model(
            code=55,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.post("/organization/search/coordinate/rectangle", response_model_exclude_none=True,
          response_model=OrganizationSearchCoordinateRectangleResponse, name="Поиск в прямоугольной области",
          tags=["Организации"])
async def organization_search_coordinate_rectangle(
        request: Request, data: OrganizationSearchCoordinateRectangle, db=Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск организаций, которые находятся в заданной прямоугольной области относительно указанной точки на карте.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        # Преобразуем смещения из километров в градусы
        lat_offset_degrees, lon_offset_degrees = km_to_degrees(data.latitude_offset, data.latitude)
        lat_offset_degrees_lon, lon_offset_degrees_lon = km_to_degrees(data.longitude_offset, data.latitude)

        # Определяем границы прямоугольной области
        # Прямоугольник строится от базовой точки с заданными смещениями
        min_lat = data.latitude - lat_offset_degrees
        max_lat = data.latitude + lat_offset_degrees
        min_lon = data.longitude - lon_offset_degrees_lon
        max_lon = data.longitude + lon_offset_degrees_lon

        # Логируем границы для отладки
        logger.info(f"Rectangle search bounds: lat[{min_lat:.6f}, {max_lat:.6f}], lon[{min_lon:.6f}, {max_lon:.6f}]")

        # Получаем все организации в прямоугольной области
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).join(Building).where(
            and_(
                Building.latitude >= min_lat,
                Building.latitude <= max_lat,
                Building.longitude >= min_lon,
                Building.longitude <= max_lon
            )
        )

        result = await db.execute(query)
        organizations = result.scalars().all()

        # Преобразуем найденные организации в формат ответа
        organizations_info = []
        for organization in organizations:
            # Вычисляем расстояние от базовой точки для сортировки
            distance_km = calculate_distance(
                data.latitude, data.longitude,
                organization.building.latitude, organization.building.longitude
            )

            organization_info = OrganizationInfo(
                id=organization.id,
                name=organization.name,
                phones=[int(phone.number) for phone in organization.phones],
                activities=[activity.name for activity in organization.activities],
                address=organization.building.address
            )
            organizations_info.append((organization_info.model_dump(), distance_km))

        # Сортируем результаты по расстоянию от базовой точки (ближайшие сначала)
        organizations_info.sort(key=lambda x: x[1])

        # Извлекаем только информацию об организациях (без расстояний)
        organizations_info_sorted = [org_info for org_info, _ in organizations_info]

        # Информация о размерах области поиска
        area_width = data.latitude_offset * 2  # ширина прямоугольника
        area_height = data.longitude_offset * 2  # высота прямоугольника

        response = set_response_model(
            code=0,
            message=f"Найдено {len(organizations_info_sorted)} организаций в прямоугольной области {area_width}×{area_height} км от точки ({data.latitude}, {data.longitude})",
            organization=organizations_info_sorted,
            qty=len(organizations_info_sorted)
        )

        logger.info(
            f"Successfully found {len(organizations_info_sorted)} organizations in rectangle {area_width}×{area_height} km from ({data.latitude}, {data.longitude})")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organizations by coordinate rectangle: {str(e)}")
        response = set_response_model(
            code=56,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.post("/organization/search/id", response_model_exclude_none=True,
          response_model=OrganizationSearchIdResponse, name="Поиск организации по ID", tags=["Организации"])
async def organization_search_id(
        request: Request, data: OrganizationSearchId, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск информации об организации по её идентификатору.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).where(Organization.id == data.organization_id)

        result = await db.execute(query)
        organization = result.scalar_one_or_none()

        if not organization:
            logger.warning(f"Organization with ID {data.organization_id} not found")
            response = set_response_model(
                code=20,
                message=f"Организация с ID {data.organization_id} не найдена"
            )
            return JSONResponse(status_code=200, content=response, media_type='application/json')

        organization_info = OrganizationInfo(
            id=organization.id,
            name=organization.name,
            phones=[int(phone.number) for phone in organization.phones],
            activities=[activity.name for activity in organization.activities],
            address=organization.building.address
        )

        response = set_response_model(
            code=0,
            message="Организация успешно найдена",
            organization=organization_info.model_dump()
        )

        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organization by ID {data.organization_id}: {str(e)}")
        response = set_response_model(
            code=50,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


@app.post("/organization/search/name", response_model_exclude_none=True,
          response_model=OrganizationSearchNameResponse, name="Поиск организации по названию", tags=["Организации"])
async def organization_search_name(
        request: Request, data: OrganizationSearchName, db = Depends(get_db),
        authorization: str = Header(description="Токен авторизации", examples=["p9q348pq347hnp34g"])
):
    """
      Поиск информации об организации по её названию.
    """
    denied, detail = await check_bearer_token(token=authorization)
    if denied:
        logger.error(f"Access denied: {detail}")
        response = set_response_model(code=1, message="Authorization failed")
        return JSONResponse(status_code=200, content=response, media_type='application/json')

    try:
        query = select(Organization).options(
            selectinload(Organization.building),
            selectinload(Organization.phones),
            selectinload(Organization.activities)
        ).where(Organization.name == data.organization_name)

        result = await db.execute(query)
        organization = result.scalar_one_or_none()

        if not organization:
            logger.warning(f"Organization with name '{data.organization_name}' not found")
            response = set_response_model(
                code=21,
                message=f"Организация с названием '{data.organization_name}' не найдена"
            )
            return JSONResponse(status_code=200, content=response, media_type='application/json')

        organization_info = OrganizationInfo(
            id=organization.id,
            name=organization.name,
            phones=[int(phone.number) for phone in organization.phones],
            activities=[activity.name for activity in organization.activities],
            address=organization.building.address
        )

        response = set_response_model(
            code=0,
            message="Организация успешно найдена",
            organization=organization_info.model_dump()
        )

        return JSONResponse(status_code=200, content=response, media_type='application/json')

    except Exception as e:
        logger.error(f"Error searching organization by name '{data.organization_name}': {str(e)}")
        response = set_response_model(
            code=51,
            message=f"Внутренняя ошибка сервера: {str(e)}"
        )
        return JSONResponse(status_code=200, content=response, media_type='application/json')


if __name__ == "__main__":
    uvicorn.run("app:app", host=API_HOST, port=API_PORT, reload=True)

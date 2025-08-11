from typing import List

from pydantic import BaseModel, validator, Field, root_validator, field_validator


class CommonResponse(BaseModel):
    code: int = Field(description="Код ответа. 0 - успешный запрос, либо номер ошибки.", examples=[0])


class CommonResponseDetail(BaseModel):
    message: str = Field(description="Ответное сообщение", examples=["Запрос успешно выполнен."])
    response_type: str = Field(description="Тип ответа", examples=["success", "error"])


class ResponseModel(CommonResponse):
    detail: CommonResponseDetail = Field(description="Детальная информация")


def set_response_model(code: int, message: str, response_type: str = None, **kwargs) -> dict:
    response_data = ResponseModel(code=999, detail=CommonResponseDetail(message="", response_type="error"))
    response_data.code = code
    response_data.detail.message = message
    if response_type is not None:
        response_data.detail.response_type = response_type
    else:
        response_data.detail.response_type = "error" if code != 0 else "success"

    data = response_data.model_dump()
    data['detail'].update(dict(kwargs))

    return data


class OrganizationInfo(BaseModel):
    id: int = Field(description="ID организации", examples=[1])
    name: str = Field(description="Название организации", min_length=1, max_length=50, examples=["ООО Рога и Копыта"])
    phones: List[int] = Field(description="Телефон(-ы) организации", examples=[333222111])
    activities: List[str] = Field(description="Виды деятельности", examples=["Мясная продукция", "Молочная продукция"])
    address: str = Field(description="ID здания", examples=["г. Москва, ул. Блюхера, 32/1"])


example_organization_info_1 = OrganizationInfo(id=1, name="ООО Рога и Копыта", phones=[111222, 333444],
                                               activities=["Колбасы", "Говядина"],
                                               address="г. Москва, ул. Блюхера, 32/1").model_dump()

example_organization_info_2 = OrganizationInfo(id = 2, name = "Автозапчасти+", phones = [555444, 999888],
                                               activities = ["Грузовые", "Легковые"],
                                               address = "г. Москва, ул. Ленина, 1, офис 3").model_dump()

class BuildingSearchOrganization(BaseModel):
    building_id: int = Field(description="ID здания", examples=[1])


class BuildingSearchOrganizationResponse(CommonResponse):
    class BuildingSearchOrganizationRes(CommonResponseDetail):
        organization: List[OrganizationInfo] = Field(description="Найденные организации",
                                                     examples=[[example_organization_info_1, example_organization_info_2]],
                                                     default=None)
        qty: int = Field(description="Количество найденных организаций", examples=[2], default=None)

    detail: BuildingSearchOrganizationRes


class ActivitySearchOrganization(BaseModel):
    activity: str = Field(description="Вид деятельности", min_length=2, max_length=20, examples=["Колбасы"])


class ActivitySearchOrganizationResponse(CommonResponse):
    class OrganizationSearchActivityRes(CommonResponseDetail):
        organization: List[OrganizationInfo] = Field(description="Найденные организации", examples=[[example_organization_info_1]], default=None)
        qty: int = Field(description="Количество найденных организаций", examples=[1], default=None)

    detail: OrganizationSearchActivityRes


class OrganizationSearchCoordinateRadius(BaseModel):
    latitude: float = Field(description="Широта", ge=-90.0, le=90.0, examples=[43.15])
    longitude: float = Field(description="Долгота", ge=-180.0, le=180.0, examples=[64.20])
    radius: float = Field(description="Радиус области области поиска в километрах", gt=0, le=6371, examples=[1.1])

class OrganizationSearchCoordinateRadiusResponse(CommonResponse):
    class OrganizationSearchCoordinateRadiusRes(CommonResponseDetail):
        organization: List[OrganizationInfo] = Field(description="Найденные организации", examples=[[example_organization_info_2]], default=None)
        qty: int = Field(description="Количество найденных организаций", examples=[1], default=None)

    detail: OrganizationSearchCoordinateRadiusRes


class OrganizationSearchCoordinateRectangle(BaseModel):
    latitude: float = Field(description="Координата широты стартовой точки поиска (центр области поиска)", ge=-90.0, le=90.0, examples=[43.15])
    longitude: float = Field(description="Координата долготы стартовой точки поиска (центр области поиска)", ge=-180.0, le=180.0, examples=[64.20])
    latitude_offset: float = Field(description="Размер области поиска по широте (запад-восток) в километрах",
                                   gt=0, le=6371, examples=[3.15])
    longitude_offset: float = Field(description="Размер области поиска по долготе (север-юг) в километрах",
                                    gt=-0, le=6371, examples=[4.20])


class OrganizationSearchCoordinateRectangleResponse(CommonResponse):
    class OrganizationSearchCoordinateRectangleRes(CommonResponseDetail):
        organization: List[OrganizationInfo] = Field(description="Найденные организации", examples=[[example_organization_info_1, example_organization_info_2]], default=None)
        qty: int = Field(description="Количество найденных организаций", examples=[2], default=None)

    detail: OrganizationSearchCoordinateRectangleRes


class OrganizationSearchId(BaseModel):
    organization_id: int = Field(description="ID организации", ge=1, examples=[1])


class OrganizationSearchIdResponse(CommonResponse):
    class OrganizationSearchIdRes(CommonResponseDetail):
        organization: OrganizationInfo = Field(description="Найденная организация", examples=[example_organization_info_2], default=None)

    detail: OrganizationSearchIdRes


class OrganizationSearchName(BaseModel):
    organization_name: str = Field(description="Название организации", min_length=1, max_length=50, examples=["ООО Рога и Копыта"])


class OrganizationSearchNameResponse(CommonResponse):
    class OrganizationSearchNameRes(CommonResponseDetail):
        organization: OrganizationInfo = Field(description="Найденная организация", examples=[example_organization_info_1], default=None)

    detail: OrganizationSearchNameRes


example_building_info_1 = {
    "id": 1,
    "address": "г. Москва, ул. Блюхера, 32/1",
    "latitude": 42.11,
    "longitude": 45.10
}

class BuildingListAllResponse(CommonResponse):
    class BuildingListAllRes(CommonResponseDetail):
        class BuildingInfo(BaseModel):
            id: int = Field(description="ID здания", examples=[1])
            address: str = Field(description="Адрес", examples=["г. Москва, ул. Блюхера, 32/1"])
            latitude: float = Field(description="Широта", examples=[42.11])
            longitude: float = Field(description="Долгота", examples=[45.10])
        building: List[BuildingInfo] = Field(description="Найденная организация", examples=[[example_building_info_1]], default=None)

    detail: BuildingListAllRes


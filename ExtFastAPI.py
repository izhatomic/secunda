from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


class ModFastAPI(FastAPI):
    def __init__(self, title: str, version: str, description: str, logo: str = None, **kwargs):
        """
        Конструктор класса

        :param title: Заголовок документации Swagger
        :param version: Версия приложения. Пример: 'v1.0.2'
        :param description: Поясняющий текст к заголовку документации Swagger
        :param logo: Ссылка на логотип к документации Swagger
        :param kwargs: Остальные аргументы для инициализации родительского класса FastAPI
        """
        FastAPI.__init__(self, **kwargs)
        self.openapi_schema = None
        self.title = title
        self.version = version
        self.description = description
        self.logo = logo

        self.openapi = self.custom_openapi

    def custom_openapi(self):
        if self.openapi_schema:
            return self.openapi_schema
        openapi_schema = get_openapi(
            title=self.title,
            version=self.version,
            description=self.description,
            routes=self.routes,
        )
        if self.logo is not None:
            openapi_schema["info"]["x-logo"] = {
                "url": self.logo
            }
        self.openapi_schema = openapi_schema

        return self.openapi_schema

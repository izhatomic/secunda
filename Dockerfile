FROM python:3.12-alpine

ARG ARG_DATABASE_URL

ENV DATABASE_URL=$ARG_DATABASE_URL

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir /app/postgres_init
COPY ./postgres_init/* /app/postgres_init/
COPY ./*.py /app/

CMD [ "python3", "/app/app.py" ]
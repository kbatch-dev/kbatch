FROM python:3.12-slim

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade --only-binary :all: -r requirements.txt
COPY ./docker/production/gunicorn_conf.py /code/
COPY ./kbatch_proxy /code/kbatch_proxy

ENV APP_HOST=0.0.0.0
ENV APP_PORT=80

# Do not use --preload, because it doesn't work correctly with OpenCensus
CMD gunicorn kbatch_proxy.main:app -k uvicorn.workers.UvicornWorker \
    -c /code/gunicorn_conf.py \
    --bind ${APP_HOST}:${APP_PORT} --log-level info

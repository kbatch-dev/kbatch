FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./django_kbatch_server /code/django_kbatch_server
COPY ./kbatch_server /code/kbatch_server
COPY ./manage.py /code/manage.py
COPY entrypoint /entrypoint

COPY ./docker/local/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start
# TODO: figure out k3s / docker-compose stuff
# COPY .kubeconfig /.config

ENTRYPOINT [ "/entrypoint" ]
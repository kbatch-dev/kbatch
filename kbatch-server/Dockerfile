FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./django_kbatch_server /code/django_kbatch_server
COPY ./kbatch_server /code/kbatch_server
COPY ./manage.py /code/manage.py
COPY entrypoint /entrypoint

ENTRYPOINT [ "/entrypoint" ]
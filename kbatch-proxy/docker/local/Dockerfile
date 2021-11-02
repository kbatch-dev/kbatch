FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./kbatch_proxy /code/kbatch_proxy

CMD ["uvicorn", "kbatch_proxy.main:app", "--host", "0.0.0.0", "--port", "80"]
FROM python:3.12-alpine

WORKDIR /usr/src/collector

COPY apps/collector/requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

COPY apps/collector/ .

CMD ["/bin/sh"]
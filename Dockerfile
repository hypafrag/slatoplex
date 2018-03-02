FROM python:3-alpine

WORKDIR /srv
ADD ./src .
RUN pip install --no-cache-dir websockets bencoder
EXPOSE 4002
ENTRYPOINT python slatoplex.py

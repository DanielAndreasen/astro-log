FROM python:3.10-alpine
EXPOSE 5065
WORKDIR /app
COPY . .

RUN pip install -U \
    pip \
    setuptools \
    wheel
RUN pip install --quiet -e .

CMD python /app/src/astrolog/web/app.py

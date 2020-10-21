FROM python:3.8.6
LABEL maintainer="dogwood008"
ARG workdir=/app

RUN mkdir $workdir
WORKDIR $workdir
ADD Pipfile $workdir
ADD Pipfile.lock $workdir

RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv sync

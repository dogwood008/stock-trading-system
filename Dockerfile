FROM python:3.8.6
LABEL maintainer="dogwood008"
ARG workdir=/app

RUN mkdir $workdir
WORKDIR $workdir

RUN pip install --upgrade pip && \
    pip install pipenv

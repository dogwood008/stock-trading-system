# syntax = docker/dockerfile:1.2

FROM python:3.9.4-buster
LABEL maintainer="dogwood008"
ARG btrepodir=/opt/backtrader

ENV TZ=Asia/Tokyo

WORKDIR $workdir
COPY Pipfile $workdir
COPY Pipfile.lock $workdir

RUN --mount=type=cache,target=/root/.cache \ 
    pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --system --ignore-pipfile --python=$(which python) --site-packages

CMD ["/usr/bin/env", "python"]


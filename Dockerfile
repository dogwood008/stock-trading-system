# syntax = docker/dockerfile:1.2

FROM python:3.10.1-buster
LABEL maintainer="dogwood008"
ARG btrepodir=/opt/backtrader

ARG WORKDIR
ENV WORKDIR ${WORKDIR:-/app}
ENV TZ=Asia/Tokyo
ARG USERNAME=${USER_NAME:-python}
ARG USER_UID=${USER_UID:-9000}
ARG USER_GID=${USER_GID:-9000}

RUN groupadd --gid ${USER_GID?} $USERNAME
RUN useradd --shell /bin/bash --create-home \
  --uid ${USER_UID?USER_UID_IS_MISSING} \
  --gid $USER_GID ${USERNAME?}

WORKDIR ${WORKDIR}
COPY Pipfile ${WORKDIR}/Pipfile
COPY Pipfile.lock ${WORKDIR}/Pipfile.lock

RUN --mount=type=cache,target=/root/.cache \ 
    pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --ignore-pipfile --python=$(which python) --site-packages

USER ${USERNAME}
CMD ["/usr/bin/env", "python"]


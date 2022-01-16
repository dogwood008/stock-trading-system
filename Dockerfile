# syntax = docker/dockerfile:1.2

FROM python:3.10.1-buster
LABEL maintainer="dogwood008"
ARG btrepodir=/opt/backtrader

ENV WORKDIR /workspace
ENV TZ=Asia/Tokyo
ENV USERNAME python
ARG USER_UID

RUN useradd --user-group --shell /bin/bash --create-home --uid ${USER_UID?USER_UID_IS_MISSING} ${USERNAME}

WORKDIR ${WORKDIR}
COPY Pipfile ${WORKDIR}/Pipfile
COPY Pipfile.lock ${WORKDIR}/Pipfile.lock

RUN --mount=type=cache,target=/root/.cache \ 
    pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --system --ignore-pipfile --python=$(which python) --site-packages

USER ${USERNAME}
CMD ["/usr/bin/env", "python"]


FROM python:3.8.6
LABEL maintainer="dogwood008"
ARG workdir=/app

RUN mkdir $workdir
WORKDIR $workdir
COPY Pipfile $workdir
COPY Pipfile.lock $workdir

ENV TZ=Asia/Tokyo

RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv sync && \
    git clone https://github.com/mementum/backtrader.git /opt/backtrader

CMD ["pipenv", "run", "python", "main.py"]


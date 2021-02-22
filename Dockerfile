FROM jupyter/scipy-notebook:42f4c82a07ff
LABEL maintainer="dogwood008"
ARG workdir=/home/jovyan/work
ARG btrepodir=/opt/backtrader
ARG tmpdir=/tmp

EXPOSE 8888

ENV TZ=Asia/Tokyo

USER root
RUN git clone https://github.com/mementum/backtrader.git $btrepodir && \
     chown -R jovyan $btrepodir

USER jovyan

WORKDIR $tmpdir
COPY Pipfile $tmpdir
COPY Pipfile.lock $tmpdir

RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --ignore-pipfile --python=$(conda run which python) --site-packages
WORKDIR $workdir

# Run Jupyter
CMD ["start-notebook.sh"]

# When Run backtest
# CMD ["pipenv", "run", "python", "main.py"]


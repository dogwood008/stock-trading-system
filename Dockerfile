FROM jupyter/scipy-notebook:42f4c82a07ff
LABEL maintainer="dogwood008"
ARG homedir=/home/jovyan
ARG workdir=${homedir}/work
ARG btrepodir=/opt/backtrader

ENV TZ=Asia/Tokyo
ENV JUPYTER_CONFIG_DIR=$homedir/.jupyter

USER jovyan

WORKDIR $workdir
COPY Pipfile $workdir
COPY Pipfile.lock $workdir

RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --ignore-pipfile --python=$(conda run which python) --site-packages && \
    mkdir -p $(jupyter --data-dir)/nbextensions && \
    cd $(jupyter --data-dir)/nbextensions && \
    git clone https://github.com/lambdalisue/jupyter-vim-binding vim_binding

RUN pipenv run jupyter contrib nbextension install --user && \
    pipenv run jupyter nbextension enable vim_binding/vim_binding

RUN pipenv run jt -t monokai -f fira -fs 13 -nf ptsans -nfs 11 -N -kl -cursw 5 -cursc r -cellw 95% -T

# Run Jupyter
EXPOSE 8888
CMD ["pipenv", "run", "start-notebook.sh"]

# When Run backtest
# CMD ["pipenv", "run", "python", "main.py"]


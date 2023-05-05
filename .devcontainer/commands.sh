#!/bin/sh

cat ./.devcontainer/aliases.sh >> /home/vscode/.bashrc
touch ./.envrc
echo "$(direnv hook bash)" >> ~/.bashrc
echo export PYTHON_PATH=`pipenv --venv` >> ~/.bashrc

direnv allow
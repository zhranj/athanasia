FROM python:3.7

# Set up code directory
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Install linux dependencies
RUN apt-get update && apt-get install -y libssl-dev

RUN apt-get update && apt-get install -y \
    npm

RUN npm install -g ganache-cli

COPY requirements.in .
COPY requirements-dev.in .

RUN pip install -r requirements.in
RUN pip install -r requirements-dev.in

SHELL ["/bin/bash", "-c"]

RUN python3 -m pip install pipx
RUN python3 -m pipx ensurepath
RUN pipx install eth-brownie

WORKDIR /code
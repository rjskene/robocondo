 FROM python:3.6
 ENV PYTHONUNBUFFERED 1
 ARG GIT_USER
 ARG GIT_PWORD
 RUN mkdir /code && apt-get update && apt-get install -y \
    sudo \
    git \
    nano \
    glpk-utils

 COPY requirements.txt /code
 WORKDIR /code
 RUN pip install --upgrade pip && pip install -r requirements.txt && \
    pip install --no-cache-dir pandas

 # create unprivileged user
 RUN adduser --disabled-password --gecos '' myuser

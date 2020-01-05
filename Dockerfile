FROM ubuntu:18.10

LABEL maintainer="Phillip Tarrant <https://gitlab.com/Ptarrant1> and Dockerfile created by kevdagoat <https://gitlab.com/kevdagoat>"

RUN apt-get update
RUN apt-get install -y python3 python3-dev python3-pip default-jre

COPY ./ /crafty_web
WORKDIR /crafty_web

RUN pip3 install -r requirements.txt

EXPOSE 8000
EXPOSE 25500-25600

CMD ["python3", "crafty.py", "-c", "/crafty_web/configs/docker_config.yml"]


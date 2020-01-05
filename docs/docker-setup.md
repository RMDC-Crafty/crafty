# Installation via Docker

## Prerequisites

1. The latest Docker version, you can get it [here](https://www.docker.com/get-started)
2. The latest version of [docker-compose](https://github.com/docker/compose)
3. `git` installed on your system

## Installation

First, lets clone the crafty-web repository to the directory you want. For this tutorial, I will be using `/opt/minecraft`.

Open up a shell window and type:

```bash
mkdir /opt
cd /opt
git clone https://gitlab.com/crafty-controller/crafty-web minecraft
cd minecraft
git checkout 3.0
```

Next, put your minecraft server JAR's into `docker/minecraft_servers`. 

Once that is done, run the container

#### Foreground Mode

```bash
docker-compose up
```

#### Background Mode

```bash
docker-compose up -d
```

Then just access crafty as you normally would. When specifying the minecraft server directory, please use `/minecraft_servers`
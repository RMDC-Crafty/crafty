# Alpha 1 install Documentation

- This guide assumes you have python 3.6 installed, along with Virtualenv, Pip, and Git, but if not, install instructions are below

## Install instructions for installing Pip and Virtualenv

### ubuntu/debian install instructions for Pip / Virtualenv / Git

    sudo apt-get install python3-pip 
    sudo pip3 install virtualenv 
    sudo apt install git

### cent os7 install instructions for Pip / Virtualenv / Git

    sudo yum install python34-setuptools
    sudo easy_install pip
    sudo pip install virtualenv
    sudo yum install git

## Crafty Install Instructions

    virtualenv crafty
    cd crafty
    git clone https://gitlab.com/Ptarrant1/crafty-web.git
    source bin/activate
    cd crafty-web
    pip install -r requirements.txt
    python crafty.py

You should now be presented with the installer

## Crafty installer

* Question 1
    * What is the path to your server? Example: /var/opt/minecraft_server

* Question 2
    * What is the name of your server.jar file? Example: spigot-1.14.4.jar

* Question 3
    * What is the max amount of memory to use? Example: 2048

* Question 4
    * What is the min amount of memory to use? Example: 1024

* Question 5
    * What are the additional arguments? Example: just hit enter, unless you add extra arguments to your launch string.

* Question 6
    * Do you want to auto-start the server when crafty starts? Example: y

* Question 7 (if 6 was y)
    * How many seconds to wait to auto-start the server? Example: 15

The installer will then present your answers and ask if this is ok - if not, type n and enter, and it will start the installer over

The installer will then ask what port the webserver should run on - Unless you are running as root - 8000 is best (port 80 requires root)

Assuming all went well, Crafty will start.

Once crafty is sitting at it's prompt waiting commands - you can visit http://server-ip:8000/admin/dashboard and hopefully see a dashboard

Most of the stats are correct (except Players, and the scheduled stuff)
Server control link on the left should work - the start/stop buttons should also work.

## I'm alpha testing, what do you want me to do?

### Report Format:
    First - THANK YOU for Alpha testing. Creating a program that works for all is rough, and I apprectiate your time, energy, and willingness to help.
    These are the details I need when you are reporting.

    email address: your email address - so we can communicate
    Operatiing System: Linux/Windows - Version - Example: Ubuntu 19.04 or Windows 10
    Crafty Version: Found in crafty/crafty-web/app/config/version.py
    What happened:
    What you expected:
    Any errors you saw

### What to test/do

1. Make sure this document is correct! If this document needs changes, you can hit me up on reddit, or ptarrant@gmail.com. If you had to add/remove or edit the instructions here to get crafty to run, please let me know.

2. Make sure the installer worked for you - any questions hard to understand?

3. Make sure Crafty is working - and the web page stays up.

4. Using the web interface, start / stop your server a few times and see if the minecraft server backend behaves as expected

5. Using the console (terminal) - start / stop crafty and report if the results were expected.

### How do I update?

Changes will be pushed to the master git branch as things are added / bugs squashed. To update your instance without having to start all over - you can go into the same directory crafty is installed (where you run python crafty.py) and just type git pull + enter. This should pull the latest changes for you.

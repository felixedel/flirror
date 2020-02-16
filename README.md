# Flirror - A smartmirror based on Flask


# Deploy flirror on a Raspberry Pi

## Requirements
- [Docker](https://www.docker.com/)
- [docker-compose](https://docs.docker.com/compose/)

### Install docker
To install docker on raspbian OS, you can simply run the following command:

```
$ curl -sSL https://get.docker.com | sh
```

This will download the installation script and directly execute it via shell.
Running the script may take some time. Afterwards, you might want to add your
user (pi) to the docker group, so you can run docker without sudo:

```
$ sudo usermod -aG docker pi
```

Afterwards log out and back or reboot the Raspberry Pi via

```
$ sudo reboot -h
```

### Install docker-compose
There are various ways to install docker-compose. Please see the
[docker-compose installation guide](https://docs.docker.com/compose/install/)
for more detailed information.

I personally installed docker-compose via
[pipx](https://pipxproject.github.io/pipx/). Using this variant requires
the `python-dev` and `libffi-dev` packages to be installed on the system.

```
$ sudo apt install python-dev libffi-dev
$ python3 -m pip install --user pipx
$ python3 -m pipx ensurepath
$ pipx install docker-compose
```

## Start flirror

Both components, `flirror-web` and `flirror-crawler` can be started via the
`docker-compose.yaml` file within this repository. Thus, you can simply start
both services by running.

```
$ docker-compose up web crawler
```

within the root of this repository.

With both services running we still need to open some kind of browser to
see the actual flirror UI. This can be done by executing the `helpers/start_gui.sh`
script. Apart from starting chromium in full screen mode targeting the running
flirror-web instance inside the docker container, the script also ensures that
some environment variables like `DISPLAY` are set and deactivates screen saver
and energy saving mode of the X server - so the display doesn't go into sleep
mode after a few minutes.

## Optional configuration

To hide the mouse cursor, install unclutter via

```
sudo apt install unclutter
```

and add the following line to `/home/pi/.config/lxsession/LXDE-pi/autostart`

```
@unclutter -display :0 -noevents -grab
```

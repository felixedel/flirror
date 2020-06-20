<h1 align="center">Flirror - A smartmirror based on Flask</h1>

<p align="center">
  <a href="https://travis-ci.com/felixedel/flirror">
    <img alt="Build Status" src="https://travis-ci.com/felixedel/flirror.svg?branch=master"/>
  </a>
  <a href="https://github.com/felixedel/flirror/blob/master/LICENSE">
    <img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-blueviolet"/>
  </a>
  <a href="https://pypi.org/project/flirror">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/flirror"/>
  </a>
  <a href="https://github.com/psf/black">
    <img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"/>
  </a>
</p>

Flirror is a modular smartmirror application developed in Python. It consists of
a simple webserver based on [Flask](https://palletsprojects.com/p/flask/) which
holds the UI and a command line application that retrieves information from
different APIs (e.g. OpenWeather, Google Calendar, ...). Currently, there is
only a small set of available [modules](#available-modules), but I'm planning to
add some more (see [planned features and ideas](#planned-features-and-ideas)).

Despite the number of commits, this project is still in an early phase, so I'm
happy about any contribution!

---

*Contents:*
**[Motivation](#motivation)** |
**[Architecture](#architecture)** |
**[Usage](#usage)** |
**[Available Modules](#available-modules)** |
**[Developing Custom Modules](#developing-custom-modules)** |
**[Deploy on Raspberry](#deploy-flirror-on-a-raspberry-pi)** |
**[Development](#development)** |
**[Planned features and ideas](#planned-features-and-ideas)** |

---

## Motivation

I mainly started this project because I wanted to build a smartmirror using a
Raspberry Pi. I searched for existing projects and found a few, but none of them
really suited my needs. There are a few smaller ones developed in Python, but
most of them don't seem to be actively maintaned anymore. A very public one I
found is for sure
[MagicMirror<sup>2</sup>](https://github.com/MichMich/MagicMirror). I think,
this is a really awesome project - taking a look at all the customizable parts,
contributions and custom modules that were developed in the meantime. I'm just
not much of a JavaScript developer and don't like the idea of having everything
in a single application.

But I got inspired by the features it provides and decided to develop my own
smartmirror in Python. Maybe someone else in the Python community is also
interested in a project like this.

## Architecture

Flirror mainly consists of two components - a webserver based on Flask and a
command line application, the so called "crawler" that retrieves data from
different APIs/backends (whatever you want to call it).

### flirror-web

The webserver is mainly used to show the information that is retrieved by the
crawlers. Currently, it doesn't allow any "interaction" from a user side. But
maybe something like this will come in the future.

### flirror-crawler

The crawler application can simply be invoked from the command line and is used
to crawl the various backends / APIs for the actual data that is displayed by
flirror-web. The crawler application supports two different modes: ``periodic``
and ``immediate`` (default). The periodic mode will crawl all available APIs in
customizable intervals, while the immediate mode can be used as a one-shot
command to retrieve the data directly from all available backends.

### SQLite database

To bring both components together I decided for a very simple approach, using a
local SQLite databse. I mainly made this choice, because we are only storing
simple key value pairs and SQLite comes
[out of the box](https://docs.python.org/3/library/sqlite3.html) with python.

## Usage

### Installation

Flirror can simply be installed via pip:
```shell
$ pip install flirror
```

or via docker:
```shell
$ docker pull felixedel/flirror
```

Deploying flirror via docker is simplest using docker-compose. An example
docker-compose stack can be found in the `deploy/docker-compose.example.yaml`
file.

### Configuration

Both applications - **flirror-web** and **flirror-crawler** - read their
configuration from the file path given via the `FLIRROR_SETTINGS` environment
variable, e.g.

```shell
$ export FLIRROR_SETTINGS=$(pwd)/settings.cfg
```

A basic configuration file must at least contain the path to a `DATABASE_FILE`
and a list of `MODULES` with at least one module configured.

Each entry in the `MODULES` list accepts the following parameters:

| Parameter | Description
|-----------|------------
| `id` | **Required** The ID to identify this module inside the application.
| `module` | **Required** The name of the module to use for this tile. A list of available modules can be found [here](#available-modules)
| `config` | **Required** The configuration for the specific module. Some modules come up with a default configuration, but usually this is needed to for each module. For more details on how to configure the specific module, take a look at the module's configuration part in the [modules](#available-modules) section.
| `crawler` | Crawler specific settings. This can be used to speficy e.g.the crawling interval for a specific module. For more details see the crawler config section.
| `display` | Configure the `position` and reloading `time` of a module

An example configuration with at least one module with the minimum required
parameters might look like the following:

``` python
MODULES = [
    {
        "id": "weather-tile",
        "module": "weather",
        "config": {
            "city": "My hometown",
            "api_key": "<your-openweathermap-api-key>",
            "language": "en",
            "temp_unit": "celsius",
        },
        "display": {
            "position": 0,
        },
    }
]
```

For more detailed configuration examples, please take a look at the
`settings.example.cfg` file.

Each module entry defined in this configuration file will be shown as a single
tile in **flirror-web** and will be crawled independently in **flirror-crawler**.

### Start flirror-web

To start flirror-web, simply run the following command:

```shell
$ flirror-web
```

which will start a [gunicorn](https://gunicorn.org/) server serving the flirror
application on `http://127.0.0.1`. The script accepts arbitrary parameters, so
you could further configure the gunicorn command that is executed in the end, by
e.g. specifying the number workers or changing the address. For a list of
available command line arguments, please refer to gunicorn's [documentation](https://docs.gunicorn.org/en/stable/run.html#commonly-used-arguments).

If you don't want to use gunicorn, you could take a look at Flask's
[uWSGI](https://flask.palletsprojects.com/en/1.1.x/deploying/uwsgi/) guide.

### Start the crawler

To start the crawler simply run one of the following commands

```shell
# Periodic mode
$ flirror-crawler crawl --periodic

# Immediate mode
$ flirror-crawler crawl
```

to run the crawler either in periodic or immediate mode. In both cases flirror
will look up all modules specified in the configuration file and try to retrieve
the data for each one by invoking the respective crawler.

## Available Modules

Modules provide the base functionality that is used by Flirror to show e.g. a
clock or the current weather. Every module defines a view (which is visible in
flirror-web) and a crawler that retrieves the actual data from an API or
backend.

Some modules may come without a crawler (like the clock module) but usually it's
recommended to do any data retrieving / calculation in the crawler and use the
view only to show the data.

The following modules are available in flirror by default:

* Clock
* Weather
* Calendar
* News
* Stocks

### Clock

The clock module displays a clock either in digital or analog format. This is a
pure JavaScript/CSS module, as it wouldn't make much sense to use a Python
backend to retrieve the current time.

#### Configuration

| Option | Description
|--------|------------
| `mode` | Must be one of `analog` or `digital` to display the clock in the selected format. **Default:** `digital`

### Weather

The weather module displays the current weather information together with a
forecast for the next six days. The weather information is retrieved from
[OpenWeather](https://openweathermap.org/), so an OpenWeather API key is
necessary to access those information. Information on how to get a free API key
can be found in their [How to start](https://openweathermap.org/appid) section.

#### Configuration

| Option | Description
|--------|------------
| `api_key` | **Required** Your personal OpenWeather API key
| `language` | **Required** The language in which the results are returned from the API (and thus displayd in flirror). For a list of available language codes, please refer to the [OpenWeather multilingual support](https://openweathermap.org/current#multi).
| `city` | **Required** The city to retrieve the weather information for.
| `temp_unit` | **Required** The unit in which the results are returned from the API (and thus displayed in flirror).

### Calendar

The calendar modules displays upcoming events from a Google calendar. Currently,
Flirror only supports the [OAuth 2.0 for TV and Limited-Input Device Applications](https://developers.google.com/identity/protocols/OAuth2ForDevices).

#### Configuration

| Option | Description
|--------|------------
| `calendars` | **Required** A list of google calendars to retrieve the events from. If you don't want to mix up multiple calendars in one tile, you can configure multiple calendar modules with one calendar each. Your default google calendar is usually named after your gmail address.
| `max_items` | The maximum number of events to show. **Default:** 5

### Stocks

The stocks module displays current stock values either in table format or as a
time series. The information is retrieved from
[Alpha Vantage](https://www.alphavantage.co/), so an Alpha Vantage API keys is
necessary to access those information. Information on how to get a free API key
can be found in their [Getting started guide](https://medium.com/alpha-vantage/get-started-with-alpha-vantage-data-619a70c7f33a).

#### Configuration

| Option | Description |
|--------|-------------|
| `api_key` | **Required** Your personal Alpha Vantage API key
| `symbols` | **Required** The list of equities you want to retrieve. Each element must be in the format `("<symbol>", "<display_name>")`
| `mode` | One of `table` or `series` to display the stocks information in the selected format. **Default:** `table`

### News

The news module displays entries from a RSS feed. Flirror uses the
[feedparser](https://pypi.org/project/feedparser/) package to crawl the
newsfeeds. Please take a look at feedparser's
[documentation](https://pythonhosted.org/feedparser/introduction.html) to get an
overview about available formats which can be parsed.

#### Configuration
| Option | Description |
|--------|-------------|
| `name` | **Required** The title to display over the news entries
| `url` | **Required** The url pointing to the RSS feed

## Developing Custom Modules
Flirror provides a plugin mechanism using an extended version of Flask
[Blueprints](https://flask.palletsprojects.com/en/1.1.x/blueprints/).

The so called `FlirrorModule` provides some decorators and functions to register
the necessary view and crawler for a module. Apart from that you could still
utilize the whole Blueprint functionality to provide e.g. custom templates,
filters and more.

A simple module may consist of the following file structure:

```
flirror_awesome_module
|-- __init__.py
|-- templates/
    |-- awesome_module/
        |-- index.html
```

The `__init__.py` file contains the module's python code including the module
definition itself.

```python
import time

from flask import current_app

from flirror.modules import FlirrorModule

awesome_module = FlirrorModule(
    "awesome_module", __name__, template_folder="templates"
)


@awesome_module.view()
def get():
    return current_app.basic_get(template_name="awesome_module/index.html")

@awesome_module.crawler()
def crawl(module_id, app, user_name):
    awesome_data = {
        "_timestamp": time.time(),
        "message": f"Hello, '{user_name}",
    }
    app.store_module_data(crawler_id, awesome_data)


FLIRROR_MODULE = awesome_module
```

A few notes on what's going on here:

First, we create a new `FlirrorModule()` instance which contains all the
necessary parameters of our custom module like its `name`, `import_path` and the
`template_folder`. The latter one is necessary to make our custom template
usable in Flirror.

Once the module is defined, we can use the `@awesome_module.view()` decorator to
register the module's view function in Flirror. Using this decorator will
register a new route `/awesome_module/` on the underlying Flask application.
Flirror-web will then request this route while providing the `module_id` as GET
parameter. The helper function `basic_get()` will evaluate this GET parameter,
look up the data which is stored in the database for this `module_id` and
populate the data to the template provided via the `template_name` parameter.
Finally, it returns the rendered template so that flirror-web can integrate it
in its UI.

To store the data in the database, we provide a crawler function decorated with
`@awesome_module.crawler()`. This registers the function as crawler for this
module in flirror. When invoking `flirror-crawler` this function will be
called with a set of predefined parameters:
* The `module_id` for which the function is called
* The `app` (which is mainly used as a back-reference to get access to the
  database)
* All config values that the module provides. In our case we want to greet a
  user whereby the `user_name` is configurable. Usually there is no need to
  store the `user_name` in the database as we could also directly access it in
  the view. It's just used like this to show the typical use case of view and
  crawler.

Finally, we expose our module as `FLIRROR_MODULE` so that it can be detected by
Flirror.

The `templates/awesome_module/index.html` file contains the view's HTML code in
form of a [Jinja2](https://jinja.palletsprojects.com/en/2.11.x/) template. It
might look redundant that the module's name is specified again in the path to
the template. That's necessary to avoid overriding templates of other modules.
More information on this can be found in the
[Templates](https://flask.palletsprojects.com/en/1.1.x/blueprints/#templates)
section of Flask's Blueprint documentation.

```html
{% extends "module.html" %}

{% block body %}
<div class="card-body">
    <div class="text-right">
        <small>
            <i id="{{ module.id }}-spinner" class="fas fa-sync-alt"></i> {{ module.data._timestamp | prettydate }}
        </small>
    </div>
    <h2>{{ module.data.message }}</h2>
</div>
{% endblock %}
```

To seamlessly include the module's view in the flirror-web UI, make sure to
extend the `module.html` template and use `<div class="card-body">` as outer
element in the body block.

### Module Detection
Flirror will try to detect installed plugins automatically if they follow a
predefined naming schema. For each plugin found, Flirror will look up the
provided flirror modules and register them on the app.

To make your plugin discoverable by flirror, it must fulfil the following
requirements:
* The name of python package providing the custom module (or modules) must start
  with `flirror_` (e.g. `flirror_awesome_module`).
* The package must expose the modules via one of the following top-level
  variables:

  ```python
  # To expose a single module, use
  FLIRROR_MODULE = <my_awesome_module>
  # If the plugin provides multiple modules, expose them via
  FLIRROR_MODULES = [<my_awesome_module_1>, <my_awesome_module_2>]
  ```
* Each module must be a valid [FlirrorModule](https://github.com/felixedel/flirror/blob/master/flirror/modules/__init__.py#L8) instance.

Flirror's standard modules are defined in the same manner like custom modules,
thus you could take a closer look on their
[source](https://github.com/felixedel/flirror/tree/master/flirror/modules) if
you are interested in how you could develop a custom module.

## Deploy Flirror on a Raspberry Pi

Although Flirror could simply be installed via `pip`, the recommended way to
install it on a Raspberry Pi is via Docker. The main reason for this is that not
all python dependencies are packaged for ARM and thus must be built from
sources. This takes a lot of time (up to 60 minutes) especially for those using
C extensions.

[Flirror's Docker image](https://hub.docker.com/r/felixedel/flirror) already
comes with all dependencies installed and you can directly start Flirror after
pulling the image.

### Requirements

* [Docker](https://www.docker.com/)
* [docker-compose](https://docs.docker.com/compose/)

#### Install docker

To install docker on raspbian OS, you can simply run the following command:

```shell
$ curl -sSL https://get.docker.com | sh
```

This will download the installation script and directly execute it via shell.
Running the script may take some time. Afterwards, you might want to add your
user (pi) to the docker group, so you can run docker without sudo:

```shell
$ sudo usermod -aG docker pi
```

Afterwards log out and back or reboot the Raspberry Pi via

```shell
$ sudo reboot -h
```

#### Install docker-compose

There are various ways to install docker-compose. Please see the
[docker-compose installation guide](https://docs.docker.com/compose/install/)
for more detailed information.

I personally installed docker-compose via
[pipx](https://pipxproject.github.io/pipx/).
Using this variant requires the `python-dev` and `libffi-dev` packages to be
installed on the system.

```shell
$ sudo apt install python-dev libffi-dev
$ python3 -m pip install --user pipx
$ python3 -m pipx ensurepath
$ pipx install docker-compose
```

### Start flirror

Both componenents can be started using the docker-compose file provided in
`deploy/docker-compose.example.yaml`. Just copy this file and name it
`docker-compose.yaml`. If necessary, adapt (or remove) some of the volume mounts
to your needs. Afterwards, you can run

```shell
$ docker-compose up
```

to start the web server and the crawler in periodic mode.

With both services running we still need to open some browser to see the actual
flirror UI. Therefore, you could download and execute the following helper
script like so:

```shell
$ wget https://raw.githubusercontent.com/felixedel/flirror/master/helpers/start_gui.sh
$ chmod u+x start_gui.sh
$ ./start_gui.sh
```

Apart from starting chromium in full screen mode pointing to the running
flirror-web instance inside the docker container, this script will also ensure
that some necessary environment variables like `DISPLAY` are set and that the
screen saver and energy saving mode of the X server are disabled - so the
display doesn't go into sleep mode after a few minutes.

### Optional configuration

To hide the mouse cursor, install unclutter via

```shell
$ sudo apt install unclutter
```

and add the following line to `/home/pi/.config/lxsession/LXDE-pi/autostart`

```shell
@unclutter -display :0 -noevents -grab
```

## Development

### Use docker buildx for a multi-architecture build
To use the Flirror docker image on a Raspberry Pi, it must be built for the ARM
architecture. To not always utilize a Raspberry Pi itself to build the docker
image for ARM, we could use docker's `buildx` command and run a
multi-architecture build on Linux or Mac.

When using [Docker for Mac](https://docs.docker.com/docker-for-mac/), the
`buildx` command should already be available. You just have to enable the
"experimental features" in the "Command Line" section of the application's
settings.

For Linux, you could use the [Getting started with Docker for Arm on Linux](https://www.docker.com/blog/getting-started-with-docker-for-arm-on-linux/)
guide to install buildx.

To test if the docker buildx command is available, simply run
```shell
$ docker buildx --help
```

To show the available platforms for which buildx can be utilized, run
```shell
$ docker buildx ls
```

Docker for Mac already comes with a few preinstalled platforms including
`linux/arm/v7` (which we are going to use).

For Linux, you first need to register the ARM executables via qemu. Information
on how to achieve this can also be found in the guide mentioned above.

Once everything is set, we can create a new builder instance which we will use
for our multi-archtitecture build:

```shell
$ docker buildx create --name flirrorbuilder
$ docker buildx use flirrorbuilder
$ docker buildx inspect --bootstrap
```

This will download the necessary `buildkit` docker image and should show an
output similar to the following if successful:

```shell
[+] Building 12.1s (1/1) FINISHED
 => [internal] booting buildkit                                                                 12.1s
 => => pulling image moby/buildkit:buildx-stable-1                                              11.0s
 => => creating container buildx_buildkit_flirrorbuilder0                                        1.0s
Name:   flirrorbuilder
Driver: docker-container

Nodes:
Name:      flirrorbuilder0
Endpoint:  unix:///var/run/docker.sock
Status:    running
Platforms: linux/amd64, linux/arm64, linux/riscv64, linux/ppc64le, linux/s390x, linux/386, linux/arm/v7, linux/arm/v6
```

Now we can use this builder to build the Flirror multi-architecture image with
the following command:
```shell
$  docker buildx build --platform linux/arm,linux/amd64 -t felixedel/flirror:latest -f dockerfiles/flirror-Dockerfile --push .
```

## Planned features and ideas

* A plugin mechamisn to allow custom modules to be included in flirror
* Provide webhooks to allow interacting with flirror from the outside (and maybe event between modules)
* Provide some notification mechanism

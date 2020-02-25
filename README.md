# Flirror - A smartmirror based on Flask

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
**[Deploy on Raspberry](#deploy-flirror-on-a-raspberry-pi)** |
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
| `type` | **Required** The name of the module to use for this tile. A list of available modules can be found [here](#available-modules)
| `config` | **Required** The configuration for the specific module. Some modules come up with a default configuration, but usually this is needed to for each module. For more details on how to configure the specific module, take a look at the module's configuration part in the [modules](#available-modules) section.
| `crawler` | Crawler specific settings. This can be used to speficy e.g.the crawling interval for a specific module. For more details see the crawler config section.
| `display` | Configure the `position` and reloading `time` of a module

An example configuration with at least one module with the minimum required
parameters might look like the following:

``` python
MODULES = [
    {
        "id": "weather-tile",
        "type": "weather",
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

### TODO How to start flirror-web

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
| `language` | **Required** The language in which the results are returned from the API (and thus displayd in flirror). For a list of available language codes, please refer to the [OpenWeather multilangual support](https://openweathermap.org/current#multi).
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
| `mode` | One of `table` or `series` to display the stocks information in the selected format. **DEfault:** `table`

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

## Deploy flirror on a Raspberry Pi

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

Both components, `flirror-web` and `flirror-crawler` can be started via the
`docker-compose.yaml` file within this repository. Thus, you can simply start
both services by running

```shell
$ docker-compose up web crawler
```

within the root of this repository. This will start the web UI and the crawler
application in periodic mode.

With both services running we still need to open some browser to see the actual
flirror UI. This can be done by executing the `helpers/start_gui.sh` helper
script. Apart from starting chromium in full screen mode pointing to the running
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

## Planned features and ideas

* A plugin mechamisn to allow custom modules to be included in flirror
* Provide webhooks to allow interacting with flirror from the outside (and maybe event between modules)
* Provide some notification mechanism

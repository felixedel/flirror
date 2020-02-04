import logging
import os
from pathlib import Path

import click
from flask.config import Config

from flirror import FLIRROR_SETTINGS_ENV
from flirror.crawler.crawlers import CrawlerFactory
from flirror.crawler.scheduling import SafeScheduler
from flirror.database import create_database_and_entities
from flirror.exceptions import CrawlerConfigError, CrawlerDataError


LOGGER = logging.getLogger(__name__)


def configure_logger(verbosity):
    # Import root logger to apply the configuration to all module loggers
    from flirror.crawler import LOGGER

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    console_handler.setFormatter(log_formatter)

    level = getattr(logging, verbosity.upper())
    environment_level = getattr(
        logging, os.environ.get("FLIRROR_VERBOSITY", verbosity).upper()
    )

    LOGGER.setLevel(min(environment_level, level))
    LOGGER.addHandler(console_handler)


@click.group(invoke_without_command=True)
@click.option(
    "--verbosity",
    help="Set the active log level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
)
@click.pass_context
def main(ctx, verbosity):
    configure_logger(verbosity)

    # Load the configurations from file
    config = Config(root_path=".")
    # TODO Add default settings, once we have some
    # config.from_object(default_settings)

    if not os.environ.get(FLIRROR_SETTINGS_ENV):
        raise click.ClickException(
            "Unable to load configuration. The environment variable 'FLIRROR_SETTINGS' "
            "is not set. Please set this variable and make it point to a configuration "
            "file."
        )

    # Validate that the path exist for a nicer error message.
    # Otherwise, we will only get a FileNotFoundError() when the config.from_envvar fails.
    config_path = Path(os.environ[FLIRROR_SETTINGS_ENV])
    if not config_path.exists():
        raise click.ClickException(
            f"The config file '{config_path}' set in 'FLIRROR_SETTINGS' environment "
            "variable does not exist. Please make this variable point to an existing "
            "configuration file."
        )

    config.from_envvar(FLIRROR_SETTINGS_ENV)

    # TODO Validate config?
    # Store everything in click's context object to be available for subcommands
    ctx.obj = {"config": config}

    if ctx.invoked_subcommand is None:
        ctx.invoke(crawl)


@main.command()
@click.option(
    "--module", "-m", help="Crawl only the module with the specified ID", multiple=True
)
@click.option(
    "--periodic/--no-periodic",
    help="Crawl modules periodically (default)",
    default=False,
)
@click.pass_context
def crawl(ctx, module, periodic):
    LOGGER.info("Hello, Flirror!")

    config = ctx.obj["config"]

    # Connect to the sqlite database
    db = create_database_and_entities(
        provider="sqlite", filename=config["DATABASE_FILE"], create_db=True
    )

    # Create the crawler factory to use for initializing new crawlers
    factory = CrawlerFactory()

    config_modules = config.get("MODULES", [])

    if module:
        # Filter crawlers for provided module IDs
        crawler_configs = [m for m in config_modules if m["id"] in module]
        # TODO If only a subset of the specified modules could be found,
        # log the remaining ones as "not found".
        if not crawler_configs:
            raise click.ClickException(
                f"None of the specified modules '{','.join(module)}' could be "
                "found in the configuration file. Nothing to run."
            )
    else:
        crawler_configs = config_modules

    if not crawler_configs:
        raise click.ClickException(
            "No modules specified in config file. Nothing to run."
        )

    crawlers = []
    # Look up crawlers from config file
    for crawler_config in crawler_configs:
        crawler_id = crawler_config.get("id")
        crawler_type = crawler_config.get("type")
        # TODO Error handling for wrong/missing keys
        LOGGER.info(
            "Initializing crawler of type '%s' with id '%s'", crawler_type, crawler_id
        )

        # Initialize the crawler
        try:
            crawler_cls = factory.get_crawler(crawler_type)
        except CrawlerConfigError:
            LOGGER.exception(
                "Could not initialize crawler '%s'. Skipping this crawler.", crawler_id
            )
            continue
        interval = crawler_config.get("crawler", {}).get("interval")
        crawler = crawler_cls(
            crawler_id=crawler_id,
            database=db,
            **crawler_config["config"],
            interval=interval,
        )
        crawlers.append(crawler)

    # Do the actual crawling - periodically or not
    if periodic:
        scheduler = SafeScheduler()
        for crawler in crawlers:
            scheduler.add_job(crawler)

        # Finally, start the scheduler
        scheduler.start()
    else:
        for crawler in crawlers:
            try:
                crawler.crawl()
            except CrawlerDataError as e:
                LOGGER.error("Crawler '%s' failed: '%s'", crawler.id, str(e))


if __name__ == "__main__":
    main()

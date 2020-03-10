import functools
import logging
import os

import click

from flirror import create_app
from flirror.crawler.scheduling import SafeScheduler


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

    app = create_app()

    # Store everything in click's context object to be available for subcommands
    ctx.obj = {"app": app}

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

    app = ctx.obj["app"]

    config_modules = app.config.get("MODULES", [])

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

    scheduler = SafeScheduler()
    # Look up crawlers from config file
    for crawler_config in crawler_configs:
        crawler_id = crawler_config.get("id")
        crawler_type = crawler_config.get("type")
        # TODO Error handling for wrong/missing keys
        LOGGER.info(
            "Initializing crawler of type '%s' with id '%s'", crawler_type, crawler_id
        )

        # Get crawler callable from module
        crawler_callable = app.crawlers.get(crawler_type)
        if crawler_callable is None:
            LOGGER.warning(
                "Could not find appropriate crawler callable for '%s'. "
                "Skipping this crawler",
                crawler_type,
            )
            continue

        # Create a copy of the function with prefilled arguments (id, config values)
        func = functools.partial(
            crawler_callable, crawler_id=crawler_id, app=app, **crawler_config["config"]
        )

        interval_string = crawler_config.get("crawler", {}).get("interval", "5m")
        scheduler.add_job(func, crawler_id, interval_string)

    # Do the actual crawling - periodically or not
    if periodic:
        scheduler.start()
    else:
        scheduler.run_all()


if __name__ == "__main__":
    main()

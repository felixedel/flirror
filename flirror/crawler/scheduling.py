import logging
import time

import schedule

from flirror.utils import parse_interval_string


INTERVAL_METHODS = {"s": "seconds", "m": "minutes", "h": "hours"}

LOGGER = logging.getLogger(__name__)


class Scheduler:

    # TODO (felix): Implement SafeScheduler to not fail the schedule when a
    # crawler throws an exception (e.g. CrawlerDataErrors):
    # https://gist.github.com/mplewis/8483f1c24f2d6259aef6
    # https://schedule.readthedocs.io/en/stable/faq.html#what-if-my-task-throws-an-exception

    def add_job(self, crawler):
        # Get interval from crawler config, parse it and call appropriate methods
        # in the schedule module

        interval, unit = parse_interval_string(crawler.interval)
        LOGGER.info(
            "Adding job for crawler '%s' with interval '%s'",
            crawler.id,
            crawler.interval,
        )
        unit_method = INTERVAL_METHODS.get(unit)
        if unit_method is None:
            LOGGER.error(
                "Invalid interval '%s'. Could not find appropriate scheduling "
                "method.",
                crawler.interval,
            )
            return

        self._add_job(interval, unit_method, crawler.crawl)

    def _add_job(self, interval, unit_method_name, job_to_execute):
        job = schedule.every(interval)
        # Add the job to the schedule
        getattr(job, unit_method_name).do(job_to_execute)

    def start(self):
        LOGGER.info("Starting scheduler")
        while True:
            schedule.run_pending()
            time.sleep(1)

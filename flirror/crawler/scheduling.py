import logging
import time
from datetime import datetime
from typing import Callable

from schedule import Scheduler

from flirror.exceptions import CrawlerDataError, FlirrorConfigError
from flirror.utils import parse_interval_string


INTERVAL_METHODS = {"s": "seconds", "m": "minutes", "h": "hours"}

LOGGER = logging.getLogger(__name__)


class SafeScheduler(Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.
    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.

    Taken from: https://gist.github.com/mplewis/8483f1c24f2d6259aef6
    on suggestion of https://schedule.readthedocs.io/en/stable/faq.html#what-if-my-task-throws-an-exception

    In addition, it provides some method to create jobs based on a crawler configuration.
    """

    def __init__(self, reschedule_on_failure: bool = True):
        """
        If reschedule_on_failure is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        super().__init__()

    def _run_job(self, job):
        # TODO (felix): Use threads for parallel execution?
        # https://schedule.readthedocs.io/en/stable/faq.html#how-to-execute-jobs-in-parallel
        try:
            LOGGER.debug("Executing job '%s'", job.tags)
            # TODO (felix): Implement an exponential backoff, that lowers the frequency
            # in which the job is executed in case it failed until it's successful again.
            super()._run_job(job)
        except Exception as e:
            LOGGER.error("Execution of job '%s' failed: '%s'", job.tags, str(e))
            job.last_run = datetime.now()
            job._schedule_next_run()

    def add_job(self, job_func: Callable, job_id: str, interval_string: str) -> None:
        # Get interval from crawler config, parse it and call appropriate methods
        # in the schedule module
        LOGGER.info(
            "Adding job for crawler '%s' with interval '%s'", job_id, interval_string
        )
        try:
            interval, unit = parse_interval_string(interval_string)
        except FlirrorConfigError as e:
            LOGGER.error(str(e))
            return None

        unit_method = INTERVAL_METHODS.get(unit)
        if unit_method is None:
            LOGGER.error(
                "Invalid interval '%s'. Could not find appropriate scheduling "
                "method.",
                interval_string,
            )
            return None

        self._add_job(interval, unit_method, job_id, job_func)

    def _add_job(
        self, interval: int, unit_method_name: str, job_id: str, job_func: Callable
    ) -> None:
        job = self.every(interval)
        # Add the job to the schedule
        getattr(job, unit_method_name).do(job_func).tag(job_id)

    def start(self):
        LOGGER.info("Starting scheduler")
        while True:
            try:
                self.run_pending()
            except CrawlerDataError as e:
                LOGGER.error(e)
            finally:
                time.sleep(1)

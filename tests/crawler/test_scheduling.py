from datetime import datetime

import pytest
from schedule import Scheduler

from flirror.crawler.crawlers import Crawler
from flirror.crawler.scheduling import SafeScheduler


class DummyCrawler(Crawler):
    def __init__(self, interval):
        super().__init__(crawler_id="test", database=None, interval=interval)

    def crawl():
        # Just a test crawl
        return True


def test_add_job():
    crawler_30s = DummyCrawler(interval="30s")
    crawler_5m = DummyCrawler(interval="5m")
    crawler_10m = DummyCrawler(interval="10m")
    crawler_1h = DummyCrawler(interval="1h")

    scheduler = SafeScheduler()
    scheduler.add_job(crawler_30s)
    scheduler.add_job(crawler_5m)
    scheduler.add_job(crawler_10m)
    scheduler.add_job(crawler_1h)

    jobs = scheduler.jobs
    assert jobs[0].interval == 30
    assert jobs[0].unit == "seconds"
    assert jobs[0].job_func.func == crawler_30s.crawl
    assert jobs[0].tags == {"test"}

    assert jobs[1].interval == 5
    assert jobs[1].unit == "minutes"
    assert jobs[1].job_func.func == crawler_5m.crawl
    assert jobs[1].tags == {"test"}

    assert jobs[2].interval == 10
    assert jobs[2].unit == "minutes"
    assert jobs[2].job_func.func == crawler_10m.crawl
    assert jobs[2].tags == {"test"}

    assert jobs[3].interval == 1
    assert jobs[3].unit == "hours"
    assert jobs[3].job_func.func == crawler_1h.crawl
    assert jobs[3].tags == {"test"}


def _failjob():
    raise Exception("I will always fail")


def test_exception_handling():
    # The normal scheduler will fail when a job raises an exception and the job
    # will be marked as if it was never run.
    normal_scheduler = Scheduler()
    normal_scheduler.every(1).hour.do(_failjob)

    with pytest.raises(Exception) as excinfo:
        normal_scheduler.run_all()
    assert "I will always fail" in str(excinfo)
    assert normal_scheduler.jobs[0].last_run is None
    assert normal_scheduler.jobs[0].next_run > datetime.now()

    # The Safe scheduler can deal with this and just schedules the next
    # execution of this job
    safe_scheduler = SafeScheduler()
    safe_scheduler.every(1).hour.do(_failjob)
    safe_scheduler.run_all()

    assert safe_scheduler.jobs[0].last_run < datetime.now()
    assert safe_scheduler.jobs[0].next_run > datetime.now()

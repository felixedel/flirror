from unittest import mock

import flirror
from flirror.crawler.crawlers import Crawler
from flirror.crawler.scheduling import Scheduler


class TestCrawler(Crawler):
    def __init__(self, interval):
        super().__init__(crawler_id="test", database=None, interval=interval)

    def crawl():
        # Just a test crawl
        return True


@mock.patch.object(flirror.crawler.scheduling, "schedule")
def test_add_job(schedule_mock):
    crawler_30s = TestCrawler(interval="30s")
    crawler_5m = TestCrawler(interval="5m")
    crawler_10m = TestCrawler(interval="10m")
    crawler_1h = TestCrawler(interval="1h")

    scheduler = Scheduler()
    scheduler.add_job(crawler_30s)
    scheduler.add_job(crawler_5m)
    scheduler.add_job(crawler_10m)
    scheduler.add_job(crawler_1h)

    # Ensure that the crawl() method of the different crawlers is added as job
    # in the correct interval methods.
    assert {30, 5, 10, 1} == {call[0][0] for call in schedule_mock.every.call_args_list}
    assert {crawler_30s.crawl} == {
        call[0][0]
        for call in schedule_mock.every.return_value.seconds.do.call_args_list
    }
    assert {crawler_5m.crawl, crawler_10m.crawl} == {
        call[0][0]
        for call in schedule_mock.every.return_value.minutes.do.call_args_list
    }
    assert {crawler_1h.crawl} == {
        call[0][0] for call in schedule_mock.every.return_value.hours.do.call_args_list
    }

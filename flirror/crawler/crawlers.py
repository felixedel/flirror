import logging
import time
from datetime import datetime

import feedparser
from alpha_vantage.timeseries import TimeSeries
from requests.exceptions import ConnectionError

from flirror.database import store_object_by_key
from flirror.exceptions import CrawlerDataError

LOGGER = logging.getLogger(__name__)


class Crawler:
    def __init__(self, crawler_id, database, interval=None):
        if interval is None:
            interval = "5m"
        self.id = crawler_id
        self.database = database
        self.interval = interval

    @property
    def object_key(self):
        return f"{self.FLIRROR_OBJECT_KEY}-{self.id}"


class NewsfeedCrawler(Crawler):

    FLIRROR_OBJECT_KEY = "module_newsfeed"

    DEFAULT_MAX_ITEMS = 5

    def __init__(
        self,
        crawler_id,
        database,
        url,
        name,
        max_items=DEFAULT_MAX_ITEMS,
        interval=None,
    ):
        super().__init__(crawler_id, database, interval)
        self.url = url
        self.name = name
        self.max_items = max_items

    def crawl(self):
        LOGGER.info("Requesting news feed '%s' from '%s'", self.name, self.url)

        news_data = {"_timestamp": time.time(), "news": []}

        feed = feedparser.parse(self.url)

        # The feedparser will set the bozo flag/exception whenever something went wrong
        # (e.g. the XML is not well formatted or couldn't be retrieved at all):
        # https://pythonhosted.org/feedparser/bozo.html
        if "bozo_exception" in feed and feed.bozo_exception:
            raise CrawlerDataError(
                f"Could not retrieve any news for '{self.name}' due to "
                f"'{feed.bozo_exception}'"
            )

        if not feed.entries:
            LOGGER.warning("News feed entries are empty for '%s'", self.name)
            return

        for entry in feed.entries[: self.max_items]:
            news_data["news"].append(
                {
                    "title": entry.title,
                    "summary": entry.summary,
                    "link": entry.id,
                    # TODO tzinfo?
                    "published": datetime(*entry.updated_parsed[:7]).timestamp(),
                }
            )

        store_object_by_key(self.database, self.object_key, news_data)


class StocksCrawler(Crawler):

    FLIRROR_OBJECT_KEY = "module_stocks"

    def __init__(
        self, crawler_id, database, api_key, symbols, mode="table", interval=None
    ):
        super().__init__(crawler_id, database, interval)
        self.api_key = api_key
        self.symbols = symbols
        self.mode = mode

    def crawl(self):
        ts = TimeSeries(key="YOUR_API_KEY")
        stocks_data = {"_timestamp": time.time(), "stocks": []}

        # Get the data from the alpha vantage API
        for symbol, alias in self.symbols:
            if self.mode == "table":
                LOGGER.info(
                    "Requesting global quote for symbol '%s' with alias '%s'",
                    symbol,
                    alias,
                )
                try:
                    data = ts.get_quote_endpoint(symbol)
                except ConnectionError:
                    raise CrawlerDataError("Could not connect to Alpha Vantage API")
                print(data)
                stocks_data["stocks"].append(
                    # TODO It looks like alpha_vantage returns a list with the data
                    # at first element and a second element which is always None
                    # TODO Normalize the data and get rid of all those 1., 2., 3. in
                    # the dictionary keys
                    {"symbol": symbol, "alias": alias, "data": data[0]}
                )
            else:
                LOGGER.info(
                    "Requesting intraday for symbol '%s' with alias '%s'", symbol, alias
                )
                try:
                    data, meta_data = ts.get_intraday(symbol)
                except ConnectionError:
                    raise CrawlerDataError("Could not connect to Alpha Vantage API")

                # As the dictionary is already "sorted" by the time in chronologial (desc) order,
                # we could simply reformat it into a list and move the time frame as a value
                # inside the dictionary. This makes visualizing the data much simpler.
                norm_values = []
                times = []
                for timeframe, values in data.items():
                    norm_values.append(
                        {
                            "open": values["1. open"],
                            "high": values["2. high"],
                            "low": values["3. low"],
                            "close": values["4. close"],
                            "volume": values["5. volume"],
                        }
                    )
                    times.append(timeframe)

                stocks_data["stocks"].append(
                    {
                        "symbol": symbol,
                        "alias": alias,
                        "data": {"values": norm_values[::-1], "times": times[::-1]},
                        "meta_data": meta_data,
                    }
                )
                # TODO Use meta_data to calculate correct timezone information
                # {'1. Information': 'Intraday (15min) open, high, low, close prices and volume',
                # '2. Symbol': 'GOOGL', '3. Last Refreshed': '2019-10-04 16:00:00',
                # '4. Interval': '15min', '5. Output Size': 'Compact', '6. Time Zone': 'US/Eastern'}

        store_object_by_key(self.database, key=self.object_key, value=stocks_data)

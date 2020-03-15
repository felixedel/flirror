import logging
import time

from alpha_vantage.timeseries import TimeSeries
from flask import current_app
from requests.exceptions import ConnectionError

from flirror.exceptions import CrawlerDataError
from flirror.modules import FlirrorModule

LOGGER = logging.getLogger(__name__)

FLIRROR_OBJECT_KEY = "module_stocks"

stocks_module = FlirrorModule("stocks", __name__, template_folder="templates")


@stocks_module.view()
def get():
    return current_app.basic_get(
        template_name="stocks/index.html", flirror_object_key=FLIRROR_OBJECT_KEY
    )


@stocks_module.app_template_filter()
def list_filter(list_of_dicts_to_filter, key):
    return [d[key] for d in list_of_dicts_to_filter]


@stocks_module.crawler()
def crawl(crawler_id, app, api_key, symbols, mode="table"):
    ts = TimeSeries(key="YOUR_API_KEY")
    stocks_data = {"_timestamp": time.time(), "stocks": []}

    # Get the data from the alpha vantage API
    for symbol, alias in symbols:
        if mode == "table":
            LOGGER.info(
                "Requesting global quote for symbol '%s' with alias '%s'", symbol, alias
            )
            try:
                data = ts.get_quote_endpoint(symbol)
            except ConnectionError:
                raise CrawlerDataError("Could not connect to Alpha Vantage API")
            stocks_data["stocks"].append(
                # TODO It looks like alpha_vantage returns a list with the data
                # at first element and a second element which is always None
                # TODO Normalize the data and get rid of all those 1., 2., 3.
                # in the dictionary keys
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

            # As the dictionary is already "sorted" by the time in chronologial
            # (desc) order, we could simply reformat it into a list and move
            # the time frame as a value inside the dictionary. This makes
            # visualizing the data much simpler.
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

    app.store_module_data(crawler_id, FLIRROR_OBJECT_KEY, stocks_data)

import logging
import time
from datetime import datetime

import feedparser
from flask import current_app

from flirror.exceptions import CrawlerDataError
from flirror.modules import FlirrorModule

LOGGER = logging.getLogger(__name__)

FLIRROR_OBJECT_KEY = "module_newsfeed"
DEFAULT_MAX_ITEMS = 5

newsfeed_module = FlirrorModule("newsfeed", __name__, template_folder="templates")


@newsfeed_module.route("/")
def get():
    return current_app.basic_get(
        template_name="newsfeed/index.html", flirror_object_key=FLIRROR_OBJECT_KEY
    )


@newsfeed_module.crawler()
def crawl(crawler_id, app, url, name, max_items=DEFAULT_MAX_ITEMS):
    LOGGER.info("Requesting news feed '%s' from '%s'", name, url)

    news_data = {"_timestamp": time.time(), "news": []}

    feed = feedparser.parse(url)

    # The feedparser will set the bozo flag/exception whenever something went
    # wrong (e.g. the XML is not well formatted or couldn't be retrieved at
    # all):
    # https://pythonhosted.org/feedparser/bozo.html
    if "bozo_exception" in feed and feed.bozo_exception:
        raise CrawlerDataError(
            f"Could not retrieve any news for '{name}' due to "
            f"'{feed.bozo_exception}'"
        )

    if not feed.entries:
        LOGGER.warning("News feed entries are empty for '%s'", name)
        return

    for entry in feed.entries[:max_items]:
        news_data["news"].append(
            {
                "title": entry.title,
                "summary": entry.summary,
                "link": entry.id,
                # TODO tzinfo?
                "published": datetime(*entry.updated_parsed[:7]).timestamp(),
            }
        )

    app.store_module_data(crawler_id, FLIRROR_OBJECT_KEY, news_data)

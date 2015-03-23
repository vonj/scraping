from __future__ import print_function
import datetime
import scraper
import pytz

sc = scraper.Scraper()

stockholm=pytz.timezone('Europe/Stockholm')
print(sc.search_keywords(['cyberbrott'],
                          before=datetime.datetime(2015, 1, 1, 0, 0, tzinfo=stockholm),
                          after=datetime.datetime(2013, 1, 1, 0, 0, tzinfo=stockholm))    )


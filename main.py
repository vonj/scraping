#!/usr/local/bin/python
# vim: set fileencoding=utf8 :
from __future__ import print_function
import datetime
import scraper
import pytz
import sys
import json

reload(sys)
sys.setdefaultencoding('UTF-8')


stockholm=pytz.timezone('Europe/Stockholm')

if len(sys.argv) < 2:
    print(sys.argv)
    sys.stderr.write('Usage: ' + sys.argv[0] + ' <config file with keywords in JSON array>')
    sys.exit(1)

grace = 2.0
if len(sys.argv) == 3:
    grace = float(sys.argv[2])

sc = scraper.Scraper(grace)

with open(sys.argv[1]) as conf:
    keywords = json.load(conf)

before=datetime.datetime(2015, 1, 1, 0, 0, tzinfo=stockholm)
after=datetime.datetime(2013, 1, 1, 0, 0, tzinfo=stockholm)
report = sc.generate_reports(keywords, before=before, after=after)


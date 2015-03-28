#!/usr/local/bin/python
# vim: set fileencoding=utf8 :
from __future__ import print_function
import datetime
import scraper
import pytz
import sys

reload(sys)
sys.setdefaultencoding('UTF-8')


stockholm=pytz.timezone('Europe/Stockholm')

kws = ['cyberkrim',
    'hets mot folkgrupp',
    'itbrott',
    'IT-brott',
    'cybercrime',
    'cyberbrott',
    'cyberbrottslighet',
    'IT-brottslighet',
    'ITbrottslighet',
    'IT-relaterade brott',
    'IT-relaterad brottslighet',
    'dataintrång',
    'datorbedrägeri',
    'datorintrång',
    'barnpornografibrott',
    'näthat',
    'bedrägeri',
    'gromning',
    'grooming',
    'phishing',
    'skimming',
    'skimmning',
    'hacking',
    'hackning',
    'intrång',
    'trojan',
    'cracking',
    'cyberterrorism',
    'pirater',
    'förtal']

sh = ['itbrott', 'IT-relaterad brottslighet']

sc = scraper.Scraper()

report = sc.search_keywords(kws,
                            before=datetime.datetime(2015, 1, 1, 0, 0, tzinfo=stockholm),
                            after=datetime.datetime(2013, 1, 1, 0, 0, tzinfo=stockholm))

f = open('report.html', 'w')
f.write(report)
f.close()


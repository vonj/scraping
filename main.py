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

kws = [
    'hets mot folkgrupp',
    'itbrott',
    'IT-brott',
    'ITbrott',
    'cyberkrim',
    'cybercrime',
    'cyber-crime',
    'cyberbrott',
    'cyber-brott',
    'IT-relaterade brott',
    'IT-relaterad brott',
    'datorintrång',
    'dator-intrång',
    'dataintrång',
    'data-intrång',
    'datorbedrägeri',
    'databedrägeri',
    'barnporno',
    'näthat',
    'nät-hat',
    'gromning',
    'groom',
    'phishing',
    'phishning',
    'skimming',
    'skimmning',
    'hacking',
    'hackning',
    'trojan',
    'cracking',
    'cracker',
    'hacker',
    'cyberterror',
    'cyber-terror',
    'pirater',
    'förtal'
]

sh = ['it-brott', 'IT-relaterad brottslighet']


if len(sys.argv) < 1:
    sys.stderr.write('Usage: ' + sys.argv[0])
    sys.exit(1)

sc = scraper.Scraper(0.3)

before=datetime.datetime(2015, 1, 1, 0, 0, tzinfo=stockholm)
after=datetime.datetime(2013, 1, 1, 0, 0, tzinfo=stockholm)
report = sc.generate_reports(sh, before=before, after=after)


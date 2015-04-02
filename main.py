#!/usr/local/bin/python
# vim: set fileencoding=utf8 :
from __future__ import print_function
import datetime
import scraper
import pytz
import sys
import subprocess

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

sh = ['itbrott', 'IT-relaterad brottslighet']


if len(sys.argv) < 2:
    sys.stderr.write('Usage: ' + sys.argv[0] + ' <site to scrape>\n')
    sys.exit(1)

publication = sys.argv[1]

sc = scraper.Scraper(publication=publication)

report = sc.generate_report(sh,
                            before=datetime.datetime(2015, 1, 1, 0, 0, tzinfo=stockholm),
                            after=datetime.datetime(2013, 1, 1, 0, 0, tzinfo=stockholm))

filename = publication + '.html'
f = open(filename, 'w')
f.write(report)
f.close()


subprocess.call(['wkhtmltopdf', filename, filename.replace('.html', '.pdf')])
pdf_filename = filename.replace('.html', '.pdf')
excel_filename = filename.replace('.html', '.xlsx')
subprocess.call(['open', excel_filename])


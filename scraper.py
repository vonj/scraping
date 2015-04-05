#!/usr/local/bin/python
# vim: set fileencoding=utf8 :
from __future__ import print_function
import tidylib
import bs4
import requests
import arrow
import re
import sys
import codecs
import dateutil.parser
import datetime
import pytz
import time
import os
import cachecontrol
import html2text
import xlsxwriter
import savReaderWriter
import shutil
import subprocess
from lxml.html import html5parser
import markdown



class Scraper(object):
    def __init__(self, grace=1):
        self._proxies = {
            'http': 'http://127.0.0.1:3128'
        }
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = True
        self._html2text.ignore_images = True
        self._html2text.body_width = 78
        self._html2text.images_to_alt = True

        self._grace = grace
        reload(sys)
        sys.setdefaultencoding('UTF-8')
        self._stockholm = pytz.timezone('Europe/Stockholm')

        tidylib.BASE_OPTIONS['bare'] = 1
        tidylib.BASE_OPTIONS['clean'] = 1
        tidylib.BASE_OPTIONS['drop-empty-paras'] = 1
        tidylib.BASE_OPTIONS['drop-font-tags'] = 1
        tidylib.BASE_OPTIONS['drop-proprietary-attributes'] = 1
        tidylib.BASE_OPTIONS['enclose-block-text'] = 1
        tidylib.BASE_OPTIONS['escape-cdata'] = 1
        tidylib.BASE_OPTIONS['hide-comments'] = 1
        tidylib.BASE_OPTIONS['logical-emphasis'] = 1
        tidylib.BASE_OPTIONS['output-xhtml'] = 1
        tidylib.BASE_OPTIONS['quote-nbsp'] = 1
        tidylib.BASE_OPTIONS['replace-color'] = 1
        tidylib.BASE_OPTIONS['uppercase-tags'] = 1
        tidylib.BASE_OPTIONS['break-before-br'] = 1
        tidylib.BASE_OPTIONS['indent'] = 1
        tidylib.BASE_OPTIONS['indent-attributes'] = 1
        tidylib.BASE_OPTIONS['indent-spaces'] = 1
        tidylib.BASE_OPTIONS['markup'] = 1
        tidylib.BASE_OPTIONS['punctuation-wrap'] = 1
        tidylib.BASE_OPTIONS['tab-size'] = 4
        tidylib.BASE_OPTIONS['vertical-space'] = 1
        tidylib.BASE_OPTIONS['wrap'] = 80
        tidylib.BASE_OPTIONS['wrap-script-literals'] = 1
        tidylib.BASE_OPTIONS['char-encoding'] = 'utf8'

        self._articles = {}
        self._keywords = {}
        sess = requests.session()
        self._cached_sess = cachecontrol.CacheControl(sess)

    def _search_keyword_idg(self, keyword, before, after, pageNr=1):
        print('IDG stub search for ' + keyword)
        urlbase = 'http://www.idg.se/2.1085/1.50095?actionType=goToPage&articleType=0&publicationSelect=0&dateRange=4&sort=0'
        index = 0
        we_may_still_find_what_we_are_looking_for = True
        urlmemory = {}

        articlenotfound = 0
        while we_may_still_find_what_we_are_looking_for:
            try:
                url = urlbase + '&queryText=' + keyword + '&pageNr=' + str(pageNr)
                print('GETTING INDEX: ' + url)
                r = self._cached_sess.get(url, proxies=self._proxies)
            except requests.exceptions.ConnectionError as e:
                print(e)
                time.sleep(60)
                break

            # Be polite
            time.sleep(self._grace)

            html = r.text
            soup = bs4.BeautifulSoup(html)
            pretty = soup.prettify()
            soup = bs4.BeautifulSoup(pretty)

            # Loop through result set:

            teasers = soup.findAll('div', {'class' : re.compile('teaserContainer*')})

            articlefound = True
            i = 0
            for teaser in teasers:
                if teaser:
                    a = teaser.find('a')
                    if a is None:
                        pass
                    title = a.contents[0].encode('utf-8').strip().replace('\n', '')
                    url = a.get('href').strip()

                    publication = 'FIXME'
                    p = teaser.find('p', {'class' : 'articlePreTeaser'})
                    if p:
                        a = p.find('a')
                        if a:
                            publication = a.contents[0].encode('utf-8').strip().replace('\n', '')
                            print(publication, ' <-------- ')

                    if url.find('queryText=') > 0:
                        if url[0:4] != 'http':
                            url = 'http://www.idg.se' + url
                        if url.find('\?'):
                            print('GETTING ARTICLE: ' + url)
                            print('title: ', title)
                            print('pageNr: ', pageNr)
                            if url in urlmemory:
                                print('  URL ' + url + ' is a duplicate, returning')
                                return
                            urlmemory[url] = True
                            if self._get_article_idg(url, publication, title, before, after, keyword):
                                articlefound = True
                    i += 1

            if not articlefound:
                articlenotfound += 1

            if articlenotfound >= 2:
                print('No article found - twice')
                return

            pageNr += 1

    def _search_keyword_aftonbladet(self, keyword, before, after):
        urlbase = 'http://sok.aftonbladet.se/?sortBy=pubDate&q='
        index = 0
        we_may_still_find_what_we_are_looking_for = True

        while we_may_still_find_what_we_are_looking_for:
            url = urlbase + keyword + '&start=' + str(index)
            try:
                r = self._cached_sess.get(url, proxies=self._proxies)
            except requests.exceptions.ConnectionError as e:
                print(e)
                time.sleep(60)
                break

            time.sleep(self._grace) # Sleep to not hammer the web server - be polite

            html = r.text
            soup = bs4.BeautifulSoup(html)
            pretty = soup.prettify()
            soup = bs4.BeautifulSoup(pretty)

            ol = soup.find('ol', {'id': 'searchResultList'})
            if ol is None:
                break

            items = ol.find_all('li')

            # By default try to give up:
            we_may_still_find_what_we_are_looking_for = False
            for li in items:
                item = {}

                link = li.find('a')
                spans = li.find_all('span')
                category = spans[0]
                is_article = 'resultInfo' == category.get('class')[0]

                if is_article:
                    # A search result! We may yet prevail!
                    we_may_still_find_what_we_are_looking_for = True
                    timestamps = spans[1]
                    created, updated = self._get_created_updated(timestamps.text)
                    if created < after:
                        # Alas, results are too old.
                        we_may_still_find_what_we_are_looking_for = False
                    if created >= after and created < before:
                        title = link.contents[0].encode('utf-8').strip()
                        url = link.get('href').strip()
                        self._get_article_aftonbladet(url, title, created, updated, keyword)
                        time.sleep(self._grace) # Sleep to not hammer the web server - be polite
                        # Step out of loop, so we can restart search on next index...
                        break
            index += 1

    def _render_email(self, email):
        return '<a href="mailto:' + email + '">' + email + '</a>'

    def generate_reports(self, keywords, before, after):
        reportbase = 'keywords_aftonbladet_idg_' + after.strftime('%Y-%m-%d') + '-' + before.strftime('%Y-%m-%d')

        try:
            shutil.rmtree(reportbase)
        except OSError:
            pass

        os.mkdir(reportbase)

        self._reportname = os.path.join(reportbase, reportbase)
        
        f = open(self._reportname + '.html', 'w')

        self._rownames = [
            'idx',
            'fetched',
            'keywords',
            'publication',
            'date',
            'updated',
            'author',
            'author_email',
            'url',
            'title',
            'fulltext_plain',
        ]
        spss_types = {
            'idx': 0,
            'fetched': 34,
            'keywords': 150,
            'publication': 30,
            'date': 34,
            'updated': 34,
            'author': 50,
            'author_email': 50,
            'url': 100,
            'title': 140,
            'fulltext_plain': 10000,
        }

        with savReaderWriter.SavWriter(
            self._reportname + '.sav',
            self._rownames,
            spss_types,
            ioUtf8=True,
        ) as self._SPSSwriter:
            f.write(self._generate_report(keywords, before, after))
            f.close()
            subprocess.call(
                ['wkhtmltopdf',
                self._reportname + '.html',
                self._reportname + '.pdf']
            )

    def _generate_report(self, keywords, before, after):
        # Gather data
        for keyword in keywords:
            keyword = keyword.strip()
            self._search_keyword_idg(keyword, before, after)
            #self._search_keyword_aftonbladet(keyword, before, after)

        # Build Excel report
        workbook = xlsxwriter.Workbook(self._reportname + '.xlsx')
        fmt = workbook.add_format({'bold': True, 'font_name': 'Verdana'})
        sheet = workbook.add_worksheet('Data')
        col = 0
        for rowname in self._rownames:
            sheet.write(0, col, rowname, fmt)
            col += 1

        # Build HTML report
        report = '''
<html>
 <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <head>
   <style>
    body {
      line-height: 1.0;
    }
   </style>
  </head>
  <body>
   Artikelsökning på Aftonbladet.se och IDG.se från ''' + \
    str(after.date()) + ' till ' + str(before.date()) + \
''', med nyckelord enligt tabellen:
   <table BORDER="1" RULES=ALL FRAME=VOID CELLPADDING="10">
    <tr>
     <th>Nyckelord</th>
     <th>Matchande länkar</th>
    </tr>
'''

        for keyword, props in self._keywords.items():
            report += \
                '<tr>' + \
                '<td><small>' + keyword + '</small></td>' + \
                '<td>'
            for url in props['url']:
                report += ' <small><a href="' + url + '">' + url + '</a></small> '
            report += \
                '</td>' + \
                '</tr>'

        report += \
            '</table>' + \
            '<p style="page-break-before: always" />'

        sheet.set_column(0, 0, 10)
        sheet.set_column(1, 1, 29)
        sheet.set_column(2, 2, 30)
        sheet.set_column(3, 3, 12)
        sheet.set_column(4, 4, 22)
        sheet.set_column(5, 5, 22)
        sheet.set_column(6, 6, 21)
        sheet.set_column(7, 7, 35)
        sheet.set_column(8, 8, 70)
        sheet.set_column(9, 9, 70)
        sheet.set_column(10, 10, 240)

        row = 0
        for _key, a in sorted(self._articles.items()):

            fetched = a['fetched'].isoformat()
            keywords = ', '.join(a['keywords'])
            publication = a['publication']
            created = a['created'].isoformat()
            updated = a['updated'].isoformat()
            author = self._html2text.handle(a['author'])
            author_email = a['author_email']
            url = a['url']
            title = a['title'].replace('\n', ' ')
            fulltext_plain = a['fulltext_plain'].replace('\n', ' ')

            row += 1
            sheet.write(row,  0, row)
            sheet.write(row,  1, fetched)
            sheet.write(row,  2, keywords)
            sheet.write(row,  3, a['publication'])
            sheet.write(row,  4, created)
            sheet.write(row,  5, updated)
            sheet.write(row,  6, author)
            sheet.write(row,  7, author_email)
            sheet.write(row,  8, url)
            sheet.write(row,  9, title)
            sheet.write(row, 10, fulltext_plain)

            self._SPSSwriter.writerow([
                row,
                fetched,
                keywords,
                a['publication'],
                created,
                updated,
                author,
                author_email,
                url,
                title,
                fulltext_plain,
            ])

            report += \
            '<table CELLPADDING=6 RULES=GROUPS  FRAME=BOX>' + \
            '<tr>' + \
            '<td>Publikation:</td>' + \
            '<td><b>' + a['publication'] + '</b></td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Titel:</td>' + \
            '<td><b>' + a['title'] + '</b></td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Skapad:</td>' + \
            '<td>' + self._dstr(a['created']) + '</td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Senast uppdaterad:</td>' + \
            '<td>' + self._dstr(a['updated']) + '</td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Källa:</td>' + \
            '<td><i><a href="' + a['url'] + '">' + a['url'] + '</a></i></td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Hämtad:</td>' + \
            '<td>' + self._dstr(a['fetched']) + ' </td>' + \
            '</tr>' + \
            '<tr>' + \
            '<td>Nyckelord:</td>' + \
            '<td>' + keywords + ' </td>' + \
            '</table>' + \
            a['lead'] + \
            a['body'] + \
            a['author'] + \
            self._render_email(a['author_email']) + \
            '<p style="page-break-before: always" />'

        report += \
            '</body>' + \
            '</html>'

        report_text, errors = tidylib.tidy_document(report)
        report_text = report

        workbook.close()

        return report_text

    def _parsedate(self, s):
        d = dateutil.parser.parse(s, fuzzy=True)
        if None == d.tzinfo:
            d = d.replace(tzinfo = self._stockholm)
        return d

    def _get_created_updated(self, datestr):
        datestr = datestr.strip()
        pos = datestr.find('(uppdaterad')

        if pos < 0 or ')' != datestr[-1]:
        	return 0, 0

        s1 = datestr[0:pos].strip()
        s2 = datestr[pos:].strip()
        created = self._parsedate(s1)
        updated = self._parsedate(s2)

        return created, updated

    def _tostring(self, resultset):
        if not resultset:
            return ''
        s = ''
        for r in resultset:
            s += str(r)
        return s

    def _dstr(self, d):
        return d.strftime('%Y-%m-%d kl %H:%M')

    def _extract_email_address(self, href):
        reobj = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,6}\b", re.IGNORECASE)
        l = re.findall(reobj, href)
        if l:
            return l[0]
        return ''

    def _get_article_aftonbladet(self, url, title, created, updated, keyword):
        request_done = False
        while not request_done:
            try:
                r = self._cached_sess.get(url)
                request_done = True
            except requests.exceptions.ConnectionError as e:
                print(e)

        soup = bs4.BeautifulSoup(r.text)
        lead = soup.find('div', {'class': 'abLeadText'})
        body = soup.find_all('div', {'class': 'abBodyText'})
        author = ''
        email = ''

        author = soup.find('address')
        if author:
            anchor = author.find('a')
            if anchor and anchor.attrs.has_key('href'):
                email = self._extract_email_address(anchor['href'])
                author = self._html2text.handle(self._tostring(anchor)),

        if keyword not in self._keywords:
            self._keywords[keyword] = {'url': []}
        if url not in self._keywords[keyword]['url']:
            self._keywords[keyword]['url'].append(url)

        if url in self._articles:
            if keyword not in self._articles[url]['keywords']:
                self._articles[url]['keywords'].append(keyword)
        else:
            leadtext = self._tostring(lead)
            bodytext = self._tostring(body)
            fulltext = leadtext + ' ' + bodytext
            self._articles[url] = {
                'title':          title,
                'created':        created,
                'updated':        updated,
                'url':            url,
                'fetched':        datetime.datetime.now(self._stockholm),
                'keywords':       [keyword],
                'lead':           '<small>' + leadtext + '</small>',
                'body':           '<small>' + bodytext + '</small>',
                'author':         self._tostring(author),
                'author_email':   email,
                'publication':    'aftonbladet.se',
                'fulltext_plain': self._html2text.handle(fulltext),
            }

    def _get_article_idg(self, url, publication, title, before, after, keyword):
        email = ''

        request_done = False
        while not request_done:
            try:
                r = self._cached_sess.get(url)
                request_done = True
            except requests.exceptions.ConnectionError as e:
                print(e)
                time.sleep(60)

        soup = bs4.BeautifulSoup(r.text)
        body = soup.find('div', attrs={'id': 'articleBodyText'})

        if not body:
            print('No body - return')
            return False

        author = ''
        div = soup.find('div', attrs={'itemprop': 'author'})
        if div:
            author = div.find('meta')['content']

        if not author:
            author = ''

        created = None
        datePublished = soup.find('meta', {'itemprop': 'datePublished'})
        if datePublished:
            created = self._parsedate(datePublished['content'])

        if not created:
            print('No create date')
            return False
        print('CREATED: ', created)

        if created > before:
            print('created > ', created)
            print('before ', before)
            return False

        if created < after:
            print('created < ', created)
            print('after ', before)
            return False

        updated = created

        if keyword not in self._keywords:
            self._keywords[keyword] = {'url': []}
        if url not in self._keywords[keyword]['url']:
            self._keywords[keyword]['url'].append(url)


        if url in self._articles:
            if keyword not in self._articles[url]['keywords']:
                self._articles[url]['keywords'].append(keyword)
        else:
            leadtext = ''
            soup = bs4.BeautifulSoup(self._tostring(body))
            [s.extract() for s in soup('img')]
            [s.extract() for s in soup('iframe')]
            text = self._tostring(soup)
            fulltext_plain = self._html2text.handle(text)
            bodytext = markdown.markdown(text)
            self._articles[url] = {
                'title':          title,
                'created':        created,
                'updated':        updated,
                'url':            url,
                'fetched':        datetime.datetime.now(self._stockholm),
                'keywords':       [keyword],
                'lead':           '<small>' + leadtext + '</small>',
                'body':           '<small>' + bodytext + '</small>',
                'author':         self._tostring(author),
                'author_email':   email,
                'publication':    publication,
                'fulltext_plain': fulltext_plain
            }
        print('added ' + url)

        return True


from __future__ import print_function
# -*- coding: utf8 -*-
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


class Scraper(object):
    def __init__(self):
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
        tidylib.BASE_OPTIONS['char-encoding'] = 'latin1'

        self._urlbase = 'http://sok.aftonbladet.se/?sortBy=pubDate&q='
        self._articles = {}
        self._keywords = {}

    def _search_keyword(self, keyword, before, after):
        index = 0
        we_may_still_find_what_we_are_looking_for = True

        while we_may_still_find_what_we_are_looking_for:
            url = self._urlbase + keyword + '&start=' + str(index)
            print(url)
            try:
                r = requests.get(self._urlbase + keyword + '&start=' + str(index))
            except ConnectionError as e:
                print(e)
                time.sleep(60)
                break
            time.sleep(0.1) # Sleep to not hammer the web server - be polite

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
                        self._get_article(url, title, created, updated, keyword)
                        # Step out of loop, so we can restart search on next index...
                        time.sleep(0.1) # Sleep to not hammer the web server - be polite
                        break
            index += 1

    def _render_email(self, email):
        return '<a href="mailto:' + email + '">' + email + '</a>'

    def search_keywords(self, keywords, before, after):
        # Gather data
        for keyword in keywords:
            self._search_keyword(keyword.strip(), before, after)

        # Build report
        report = \
            '<html>' + \
            '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />' + \
            '<head>' + \
            '<title>Aftonbladet articles for keywords ' + ', '.join(keywords) + '</title>' + \
            '</head>' + \
            '<body>' + \
            '<table CELLPADDING=6 RULES=GROUPS  FRAME=BOX>'

        sup = True
        for keyword, props in self._keywords.items():
            report += \
                '<tr>' + \
                '<td>' + keyword + '</td>' + \
                '<td><' + su + '>' + ' '.join(props['url']) + '</' + su + '></td>' + \
                '</tr>'
            sup = not sup
            if sup:
                su = 'sup'
            else:
                su = 'sub'
                

        report += \
            '</table>' + \
            '<p style="page-break-before: always" />'

        for _key, a in self._articles.items():
            report += \
            '<table CELLPADDING=6 RULES=GROUPS  FRAME=BOX>' + \
            '<tr>' + \
            '<td>Titel:</td>' + \
            '<td>' + a['title'] + '</td>' + \
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
            '<td>' + ', '.join(a['keywords']) + ' </td>' + \
            '</table>' + \
            a['lead'] + \
            a['body'] + \
            a['author'] + ' ' + self._render_email(a['email']) + \
            '<p style="page-break-before: always" />'

        report += \
            '</body>' + \
            '</html>'

        report_text, errors = tidylib.tidy_document(report)

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

    def _get_article(self, url, title, created, updated, keyword):
        request_done = False
        while not request_done:
            try:
                r = requests.get(url)
                request_done = True
            except requests.exceptions.ConnectionError as e:
                print(r)

        soup = bs4.BeautifulSoup(r.text)
        lead = soup.find('div', {'class': 'abLeadText'})
        body = soup.find_all('div', {'class': 'abBodyText'})
        email = ''

        author = soup.find('address')
        if author:
            anchor = author.find('a')
            if anchor and anchor.attrs.has_key('href'):
                email = self._extract_email_address(anchor['href'])

        if keyword not in self._keywords:
            self._keywords[keyword] = {'url': []}
        if url not in self._keywords[keyword]['url']:
            self._keywords[keyword]['url'].append(url)

        if url in self._articles:
            if keyword not in self._articles[url]['keywords']:
                self._articles[url]['keywords'].append(keyword)
        else:
            self._articles[url] = {
                'title':     title,
                'created':   created,
                'updated':   updated,
                'url':       url,
                'fetched':   datetime.datetime.now(self._stockholm),
                'keywords':  [keyword],
                'lead':      self._tostring(lead),
                'body':      self._tostring(body),
                'author':    self._tostring(author),
                'email':     email,
            }


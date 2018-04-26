import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
import pickle
import json
import codecs
import os.path
import random

class AmebaTagSpider(scrapy.Spider):
    name = 'ameba'
    allowed_domains = ['ameba.jp']
    start_urls = (
        'http://profile.ameba.jp/general/ametsuna/list.do',
    )

    def __init__(self):
        self.tag_list = []

    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        for link in soup.find_all('a'):
            self.tag_list.append(link.get('href'))
        print(self.tag_list)
        #pickle.dump(self.tag_list, open('tag_list.pkl', 'wb'))
        yield

class AmebaProfileSpider(scrapy.Spider):
    name = 'ameba'
    allowed_domains = ['ameba.jp']

    def __init__(self):
        self.root_address = 'http://profile.ameba.jp'
        self.tag_list = pickle.load(open('tag_list.pkl', 'rb'))
        self.tag_list = [self.root_address + link + '&row=50' for link in self.tag_list if 'general' in link]
        self.start_urls = self.tag_list
        self.visited = set()

    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        next_pages = []

        with open('profile_list.txt', 'a') as f:
            for link in soup.find_all('a'):
                add = link.get('href')
                if add is None:
                    continue
                #print(add)
                if 'http://profile.ameba.jp' in add:
                    profile_id = add.split('/')[-1]
                    #print(profile_id)
                    f.write(profile_id + '\n')
                if '//search.profile.ameba.jp/profileSearch/search?' in add:
                    next_pages.append('http://' + add)

        #print(next_pages)
        for next_page in next_pages:
            if next_page not in self.visited:
                self.visited.add(next_page)
                yield scrapy.Request(next_page, callback=self.parse)

class AmebaProfileDetailSpider(scrapy.Spider):
    name = 'ameba'
    allowed_domains = ['ameba.jp']

    def __init__(self):
        self.root_address = 'http://profile.ameba.jp/'
        with open('profile_ids.txt', 'r') as f:
            self.profile_ids = f.readlines()
        self.profile_ids = [self.root_address + profile_id.strip() for profile_id in self.profile_ids]
        print(self.profile_ids)
        self.start_urls = self.profile_ids


    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        user_profile = {}
        user_profile['id'] = response.request.url.split('/')[-1]

        dt = soup.find_all('dt')
        dd = soup.find_all('dd')
        for i, item in enumerate(dt):
            user_profile[item.string.strip()] = dd[i].string.strip()

        self_intro = soup.find_all('p')[-1]
        if self_intro.text:
            user_profile['self-intro'] = self_intro.text

        with open('profile_data.txt', 'a') as f:
            r = json.dumps(user_profile)
            f.writelines(r + '\n')

class AmebaBlogEntrySpider(scrapy.Spider):
    name = 'ameba'
    allowed_domains = ['ameblo.jp']

    def __init__(self):
        self.root_address = 'http://ameblo.jp/'
        with open('profile_ids.txt', 'r') as f:
            self.profile_ids = f.readlines()
        self.profile_entries = ['{}{}/entrylist.html'.format(self.root_address, profile_id.strip()) for profile_id in self.profile_ids]
        #print(self.profile_entries)
        self.start_urls = self.profile_entries[64800:100000]
        self.visited = set()
        self.entries = set()

    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        user_id = response.request.url.split('/')[-2]

        next_pages = []
        with open('entry_list.txt', 'a') as f:
            for link in soup.find_all('a'):
                add = link.get('href')
                #print(add)
                if add is None:
                    continue
                if '/entry-' in add and user_id in add and 'http://ameblo.jp' in add:
                    entry_add = add.split('#')[0]
                    if entry_add not in self.entries:
                        f.write(add.strip() + '\n')
                        self.entries.add(entry_add)
                if '/entrylist-' in add and add.count('-') == 1:
                    next_pages.append(add)

        for next_page in next_pages:
            if next_page not in self.visited:
                self.visited.add(next_page)
                print(next_page)
                yield scrapy.Request(next_page, callback=self.parse)

class AmebaBlogDetailSpider(scrapy.Spider):
    name = 'ameba'
    allowed_domains = ['ameba.jp']

    def __init__(self):
        self.root_address = 'http://ameblo.jp/'
        with open('blog_entry_list.txt', 'r') as f:
            self.entry_list = f.readlines()
        self.entry_list = [item.strip() for item in self.entry_list]
        #random.shuffle(self.entry_list)
        self.start_urls = self.entry_list[8489544:]

    def parse(self, response):
        soup = BeautifulSoup(response.body, "html.parser")
        link = response.request.url
        user_id = link.split('/')[-2]

        # type original_link title theme time content comments
        template = '''<div type="{}">
        <div id="title"><h1>{}</h1></div>
        <div id="link"><a href="{}">{}</a></div>
        <div id="date">{}</div>
        <div id="theme">{}</div>
        <div id="content">{}</div>
        <div id="comments">{}</div>
        </div>
        '''

        # type 4, no right to access
        # http://secret.ameba.jp/bakaoroka/amemberentry-10524746555.html
        # <h1 amb-component="amemberLoginHeading">この記事はアメンバーさん限定です。</h1>
        results = soup.findAll("h1", {"amb-component": "amemberLoginHeading"})
        if len(results) == 1:
            return

        # write utf encoding header the first access the file
        file_path = 'D:/blog/{}.html'.format(user_id)
        if not os.path.exists(file_path):
            with codecs.open(file_path, 'a', encoding='utf-8') as f:
                f.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n')

        with codecs.open(file_path, 'a', encoding='utf-8') as f:
            # type 3
            # http://ameblo.jp/ask1018/entry-11820404664.html
            # <h3 class="title">
            # <span class="date">2012-02-11 09:39:07</span>
            # <span class="theme">テーマ：<a href="http://ameblo.jp/ask1018/theme-10015155250.html">ブログ</a></span>
            # <div class="subContentsInner">
            # <div class="each_comment">
            title = soup.findAll("h3", {"class": "title"})
            date = soup.findAll("span", {"class": "date"})
            if len(title) > 0 and len(date) == 1:
                type = 3
                date = date[0].text.strip()
                title = title[0].text.strip()
                theme = soup.findAll("span", {"class": "theme"})[0].text.strip()
                content = soup.findAll("div", {"class": "subContentsInner"})[0]
                comments = ''
                for comment in soup.findAll("div", {"class": "each_comment"})[:]:
                    comments += '{}'.format(comment)
                f.write(template.format(type, title, link, link, date, theme, content, comments).replace('</br>', ''))
                return

            # type 2
            # http://ameblo.jp/kazuny-myumyu/entry-10600827724.html
            # <h1 amb-component="entryTitle" class="skin-entryTitle"><a href="http://ameblo.jp/kazuny-myumyu/entry-10600827724.html" rel="bookmark">アメブロでは、はじめまして！</a></h1>
            # <time datetime="2010-07-25" class="skin-textQuiet">2010-07-25 21:08:34</time>
            # <dl amb-component="entryThemes" class="skin-entryThemes">
            # <div amb-component="entryBody" class="skin-entryBody">
            # <div amb-component="comments">
            title = soup.findAll("h1", {"class": "skin-entryTitle"})
            if len(title) == 1:
                type = 2
                title = title[0].text.strip()
                date = soup.findAll("time")[0].text.strip()
                theme = soup.findAll("dl", {"class": "skin-entryThemes"})[0].text.strip()
                content = soup.findAll("div", {"class": "skin-entryBody"})[0]
                comments = ''
                for comment in soup.findAll("div", {"amb-component": "comments"})[:]:
                    comments += '{}'.format(comment)
                f.write(template.format(type, title, link, link, date, theme, content, comments).replace('</br>', ''))
                return

            # type 1
            # http://ameblo.jp/arashimimiko/entry-12036561478.html
            # <h1><a href="http://ameblo.jp/arashimimiko/entry-12036561478.html" class="skinArticleTitle" rel="bookmark">潤くん日立新ＣＭでシェイクスピアに＠ＷＳ</a></h1>
            # <span class="articleTime"><time datetime="2015-06-08" pubdate="pubdate">2015年06月08日(月) 19時30分29秒</time></span>
            # <span class="articleTheme">テーマ：<a href="http://ameblo.jp/platinumbell/theme-10026640424.html" rel="tag">ブログ</a></span>
            # <div class="articleText">
            # <div class="blogComment">
            date = soup.findAll("span", {"class": "articleTime"})
            if len(date) == 1:
                type = 1
                date = date[0].text.strip()
                title = soup.findAll("a", {"class": "skinArticleTitle"})[0].text.strip()
                theme = soup.findAll("span", {"class": "articleTheme"})[0].text.strip()
                content = soup.findAll("div", {"class": "articleText"})[0]
                comments = ''
                for comment in soup.findAll("div", {"class": "blogComment"})[:]:
                    comments += '{}'.format(comment)
                f.write(template.format(type, title, link, link, date, theme, content, comments).replace('</br>', ''))
                return

        # log unknown type
        with open('log.txt', 'a') as f:
            f.write(link + '\n')

        return

process = CrawlerProcess({'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'})
process.crawl(AmebaTagSpider)
process.start()

def filter_entry_list():
    with open('entry_list.txt', 'r') as f:
        lists = f.readlines()
        list_set = set()
        for link in lists:
            link = link.strip()
            if link.startswith('http://ameblo.jp'):
                list_set.add(link + '\n')
        print(len(list_set))
        new_list = list(list_set)
        print(len(new_list))
        print(new_list.sort(reverse=True))
        with open('blog_entry_list.txt', 'w') as f2:
            f2.writelines(new_list)

def dump_blog_content():
    with codecs.open('blog_content_dump.txt', 'a', encoding='utf-8') as wf:
        filenames = next(os.walk('blog'))[2]
        for filename in filenames:
            if filename.endswith('.html'):
                print(filename)
                with codecs.open('blog/' + filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    content = ''.join(lines)
                    soup = BeautifulSoup(content, 'html.parser')
                    contents = soup.findAll("div", {"id": "content"})
                    for content in contents:
                        wf.write(content.text)

#dump_blog_content()
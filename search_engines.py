from bs4 import BeautifulSoup
from urllib.parse import urlsplit, unquote
from html import unescape
from random import choice

import requests, json, re, unicodedata, urllib3


urllib3.disable_warnings()


'''
Search engines
'''

class SearchEngine(object):
    '''This is a parent class designed for creating child classes of search
    engines with predefined methods. It does not intend to be instantiated!

    It implements constants, content getter/setter methods that are intended
    for a testing purpose in the subclasses, query string filter, etc.

    The ".get_results" method builds a list of URLs by the specified query string.
    This method is only declared in the class and raises "NotImplementedError"
    exception, and should be implemented in the child classes to make it work
    properly.
    '''

    BASE_URL = None
    NUM = 10

    @property
    def content(self):
        return self._content


    @content.setter
    def content(self, val):
        '''Preloads html or any other string content
        '''

        if type(val) == str:
            self._content = val
        else:
            raise TypeError('Type mismatch: only variable of string type is allowed to set.')


    @staticmethod
    def filter_query_string(chars='\'",:;'):
        '''The default method of filtering unnecessary characters in
        search query string.

        Input
            @chars: str containing characters to filter out

        Returns:
            Enclosed filter function related to @chars
        '''

        def enclosed_fqs(q):
            for c in chars:
                q = q.replace(c, '')

            return q.strip()

        return enclosed_fqs


    def get(self, p):
        '''Sends HTTP GET request method to the predefined URL. It also does
        rotation of the "User-Agent" parameter value in the HTTP-header.

        Input
            @p: dict of params added to the request

        Returns:
            str
        '''

        h = requests.utils.default_headers()

        h.update({
            'User-Agent': choice([
                'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 DuckDuckGo/7; +http://www.google.com/bot.html)',
                'Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
                'Mozilla/5.0 (compatible; YandexAccessibilityBot/3.0; +http://yandex.com/bots)',
                'Mozilla/5.0 (compatible; Yahoo! Slurp/3.0; http://help.yahoo.com/help/us/ysearch/slurp)',
            ])
        })

        self._content = requests.get(self.BASE_URL, params=p, headers=h).text


    def get_results(self, q):
        raise NotImplementedError('This method requires to be implemented.')


class GoogleCustomSearch(SearchEngine):
    '''A search engine based on "Google Custom Search API". It requires <ID> and
    <API KEY> to serve the requests.

    This is the easiest and reliable option to get the search results information
    from Google in structured data (JSON) format.

    A free developer's account is limited by 100 requests a day to the API. The
    limit increase is worth $5 per 1000 requests.
    '''

    BASE_URL = 'https://www.googleapis.com/customsearch/v1'
    API_KEY = '<Google_App_API_key>'
    ID = '<Google_App_Id>'


    def __init__(self, api_key=None, app_id=None, num=10, filter=None):
        '''Creates an instance of the class.

        Input
            @api_key: Google API Key of str type. If set to None overrides
                      default <API KEY> value;
            @app_id:  Google APP Id of str type. If set to None overrides
                      default <ID> value;
            @num:     int, the number of the search results;
            @filter:  query string filter function. If set to None, overrides
                      default filter. Set it to SearchEngine.filter_query_string('')
                      to baypass the query string filter.
        '''

        if api_key is not None:
            self.API_KEY = api_key

        if app_id:
            self.ID = app_id

        self._fqs = filter or self.filter_query_string()

        self.NUM = SearchEngine.NUM if num > 10 or num < 1 else num


    def __repr__(self):
        return '{}(\nBASE_URL: {url}\nAPI_KEY: {api_key}\nID: {id}\nNUM: {num}\nfilter: {fqs}\n)'. \
            format(
                self.__class__.__name__,
                url = self.BASE_URL,
                api_key = self.API_KEY,
                id = self.ID,
                num = self.NUM,
                fqs = self._fqs,
            )


    @staticmethod
    def _normalize(j):
        '''Simplifies Google structured data to a simpler format, having
        only URL, title, and description information per each item.

        Input
            @j: dict, the response data from Google Custom Search API

        Returns
            list of dicts -> [{'link': str, 'title': str, 'descr': str}, ...]
        '''

        res = []

        items = j.get('items')

        if items:
            for item in items:
                res.append({
                    'link':  item['link'],
                    'title': item['title'],
                    'descr': item['snippet']
                })

        return res


    def results(self):
        '''Returns data in format acceppted by UrlFinder.
        '''

        try:
            return self._normalize(json.loads(self._content, encoding='utf-8'))

        except json.decoder.JSONDecodeError:
            return []


    def get_results(self, q):
        '''Sends requests to the Google Custom Search API and return data in format
        acceppted by UrlFinder.

        Input
            @q: query string

        Returns
            list of dicts -> [{'link': str, 'title': str, 'descr': str}, ...]
        '''

        try:
            self.get({
                'q':   self._fqs(q),
                'num': self.NUM,
                'cx':  self.ID,
                'key': self.API_KEY
            })

            try:
                return self.results()

            except json.decoder.JSONDecodeError:
                return []

        except requests.exceptions.ConnectionError:
            return []


class GoogleSearch(SearchEngine):
    '''A search engine based on parsing results taken via Google website.
    This is a complex option to get search results information but it is
    free of charge.

    The engine passes a query string to the Google website and gets html
    content as a response. Than parses the content and excludes links,
    titles, and descriptions.

    Also, Google detects unusual traffic to the website. So, it is needed
    to make a pause between requests and rotate "User-Agent" in th HTTP
    header of the request to bypass Google's restrictions.
    '''

    BASE_URL = 'https://www.google.com/search'


    def __init__(self, num=10, filter=None):
        '''Creates an instance of the class.

        Input
            @num:    int, the number of the search results;
            @filter: query string filter function. If set to None, overrides
                     default filter. Set it to SearchEngine.filter_query_string('')
                     to baypass the query string filter
        '''

        self._fqs = filter or self.filter_query_string()

        self.NUM = 10 if num < 1 or num > 30 else num


    def __repr__(self):
        return '{}(\nBASE_URL: {url}\nNUM: {num}\nfilter: {fqs}\n)'. \
            format(
                self.__class__.__name__,
                url = self.BASE_URL,
                num = self.NUM,
                fqs = self._fqs,
            )


    @staticmethod
    def _parse_url(url, home=False):
        '''Extracts an actual website URL from the link provided by Google Search

        Input
            @url:  str containing Google link to the website
            @home: bool. If set True forces return URL of homepage

        Returns
            str containing URL
        '''

        u = unquote(re.sub('&sa=.+&ved=.+&usg=.+', '', url.replace('/url?q=', '')))

        if home:
            p = urlsplit(u)
            
            u = '{}://{}/'.format(p[0], p[1])

        return u


    def results(self):
        '''Returns data in format acceppted by UrlFinder.
        '''

        res = []

        main = BeautifulSoup(self._content, 'html.parser').find('div', attrs={'id': 'main'})

        if main:
            divs = main.div.find_next_siblings('div')

            divs.pop(0) # element No.0 contains commentary-separator

            for div in divs:
                ch = div.findChild('div', recursive=False)

                # Empty divs
                if not ch:
                    continue

                ch = list(ch)

                # company widget exists
                if len(ch) == 4:
                    title_and_descr = ch[0].find_all('span', recursive=False)
                    a = ch[2].find_all('a')

                    title = title_and_descr[0].get_text()

                    if len(title_and_descr) == 2:
                        descr = title_and_descr[1].get_text() + '\n' + ch[3].get_text()
                    else:
                        descr = ''

                    if a and len(a) > 1:
                        alink = ch[2].find_all('a')[1].attrs['href']

                        res.append({
                            'link': GoogleSearch._parse_url(alink, True),
                            'title': title,
                            'descr': descr
                        })

                # regular search result -- link on the first place
                elif len(ch) == 3 and ch[0].a:
                    alink = ch[0].a.attrs['href']
                    title = ch[0].a.findChild('div').text
                    descr = ch[2].get_text()

                    res.append({
                        'link': GoogleSearch._parse_url(alink),
                        #'link': self._parse_url(alink),
                        'title': title,
                        'descr': descr
                    })

                #else: other info from Google // notes, help, etc.

        return res


    def get_results(self, q):
        '''Sends requests to the Google Search website and return data in format
        acceppted by UrlFinder.

        Input
            @q: query string

        Returns
            list of dicts -> [{'link': str, 'title': str, 'descr': str}, ...]
        '''

        try:
            self.get({
                'q':   self._fqs(q),
                'num': self.NUM,
                'ie': 'UTF-8'
            })

            return self.results()

        except requests.exceptions.ConnectionError:
            return []


class UrlFinder():
    '''A class to create a crawler. For a given query string with ".get" method,
    it requests the search engines and receives back the list of URLs. For each
    URL in the list, it downloads the webpage content related to this URL and
    analyses it by a list of validation rules for being a corporate website.
    '''

    _exclude_ext = {'.jpg', '.png', '.pdf', '.jpeg', '.gif', '.avi', '.mp4', '.mkv', '.mp3', '.mpg', '.mpeg'}
    _exclude_dom = ('linkedin', 'glassdoor', 'facebook', 'societe', 'wikipedia', 'google', 'youtube')


    def __init__(self, engines, proc, home_weight=1, skip_social=True, home_only=False, threshold=0.3):
        '''Creates an instance of the crawler.

        Input
            @engines:     single instance or list of instances of any SearchEngine
                          child classes;
            @procs:       dict, defines a series of validation rules used to check the
                          URL for being an address of the corporate website. The keys of
                          the @procs represent data field names. And the values of the
                          @procs are lists of tuples. Each tuple represents a validation
                          rule: (<filter function>, <search function>, <weight>,
                                 <content function>);
            @home_weight: float, defines a weight for an URL pointing to the homepage of
                          the website;
            @skip_social: bool, defines skipping or not URLs of social networks during
                          the validation process;
            @home_only:   bool, defines skipping or not the non-homepage URLs;
            @threshold:   float, a value of weight for the URLs to be filtered below or
                          equal this value. Set it to 999 for no threshold.
        '''

        self._engines     = list(engines)

        self._processors  = procs
        self._exclude_re  = re.compile('(' + ')|('.join(['^http.*://.*' + ex + '\..{2,}/*.*$' for ex in self._exclude_dom]) + ')')
        self._skip_social = skip_social
        self._home_weight = home_weight
        self._home_only   = home_only
        self._threshold   = threshold


    def get(self, query, params):
        '''Finds an URL of the corporate website by a given search string

        Input
            @query:  str, a query string passing to the instance of any of @SearchEngine subclasses;
            @params: dict of data fields and values to search in the webpage contents.
        '''

        h = requests.utils.default_headers()

        h.update({
            'User-Agent': choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.54 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
            ])
        })

        results = []

        # Building the total list of URLs using all provided search engines
        for e in self._engines:
            try:
                res = e.get_results(query)

                # Adding only unique URLs
                for r in res:
                    if r not in results:
                        results.append(r)

            except Exception as ex:
                print(ex)

        weights = []

        # Looping through collected URLs
        for r in results:
            print('Retreiving from url:', r['link'])

            is_home = (
                r['link'] == '{}://{}/'.format(*urlsplit(r['link'])[:2])
            )

            if r['link'][-4:].lower() in self._exclude_ext or r['link'][-5:].lower() in self._exclude_ext or ( \
                    self._skip_social and self._exclude_re.match(r['link']) ) or ( \
                    self._home_only and not is_home ):

                weights.append(-1)

                continue

            # Calculating the initial weight using "is_home" argument value and homepage threshold value
            # @w will hold total weight of the URL
            w = int(is_home) * self._home_weight

            # Downloading and analysing the webpage content
            if self._processors is not None and params is not None:
                try:
                    html = requests.get(r['link'], headers=h, verify=False).text
                    soup = BeautifulSoup(html, 'html.parser')

                    content = {
                        None: html
                    }

                    # Looping through the dict of validation rules and extracting
                    # @p_name: field name, @p_proc: validation rules (list of tuples)
                    for p_name, p_proc in self._processors.items():

                        # Extracing search string linked to the field name @p_name
                        p_str = params.get(p_name)

                        # Search string is not empty
                        if p_str is not None:

                            # Looping through the list of validation rules and extracting parameters:
                            # preprocessor, search processor, weight of result, content preprocessor
                            # @str_f: string filter function, @str_p: string search function, @weight,
                            # @content_p: function returning content to search in
                            for str_f, str_p, weight, content_p in p_proc:

                                # Filters search string if filter function is provided
                                #p_str_filtered = str_f(p_str) if str_f is not None else p_str
                                p_str_filtered = str_f(p_str) if callable(str_f) else p_str

                                # Does the content has been already filtered with this filter
                                text = content.get(content_p)

                                # No. Ok, lets filter and save it for direct use in the next iteration
                                if text is None:
                                    text = self.strip_accents(content_p(soup))
                                    content[content_p] = text

                                # String search function call, multiply by the weight,
                                # and summarise it with total weight
                                w += str_p(text, p_str_filtered) * weight

                except requests.exceptions.ConnectionError as e:
                    w = -1

                    print('Unable to retreive data from url:', r['link'])

            weights.append(w)

        # Returning URL with maximum weight if it is greater or equal to the threshold value
        if weights:
            idx, _ = sorted(enumerate(weights), key=lambda x: x[1], reverse=True)[0]

            return results[idx]['link'] if weights[idx] >= self._threshold else None

        else:
            return None


    @staticmethod
    def meta_description(soup):
        '''Returns the meta description of the webpage, i.e. the content string of
        the <meta name="description" content="content string">

        Input
            @soup: BeautifulSoup

        Returns
            str
        '''

        try:
            m = unescape(soup.findAll('meta', attrs={'name':'description'})[0]['content'])
        except IndexError:
            m = ''

        return m


    @staticmethod
    def html_title(soup):
        '''Returns the title of the webpage, i.e. the content string inside the <title> tag.

        Input
            @soup: BeautifulSoup

        Returns
            str
        '''

        t = soup.find('title')

        return unescape(t.text) \
            if t else ''


    @staticmethod
    def body_text(soup):
        '''Returns only the text content inside the <body> tag, stripping out other tags.

        Input
            @soup: BeautifulSoup

        Returns
            str
        '''

        t = soup.find('body')

        return unescape(t.text) \
            if t else ''


    @staticmethod
    def body(soup):
        '''Returns the content inside the <body> tag.

        Input
            @soup: BeautifulSoup

        Returns
            str
        '''

        t = soup.find('body')

        return unescape(t) \
            if t else ''


    @staticmethod
    def h1_text(soup):
        '''Returns the content string inside the <h1> tag.

        Input
            @soup: BeautifulSoup

        Returns
            str
        '''

        t = soup.find('h1')

        return unescape(t.text) \
            if t else ''


    @staticmethod
    def strip_accents(s):
        '''Normalizes string containing letters with diacritical sign converting
        them to regular characters

        Input
            @s: str

        Returns
            str
        '''

        return ''.join([c for c in unicodedata.normalize('NFD', s) \
            if unicodedata.category(c) != 'Mn'])


    @staticmethod
    def strip_accents_old(s):
        '''Normalizes string containing letters with diacritical sign converting
        them to regular characters. Old version of algoritm.

        Input
            @s: str

        Returns
            str
        '''

        nfkd_form = unicodedata.normalize('NFKD', s)

        return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
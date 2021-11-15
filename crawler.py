'''
The task of this web crawler -- to search the Web for corporate websites,
using various data columns from the input CSV file. Each row in the file
represents a company.

The result is saved in another CSV file with the same column
structure, and an additional one named "website". Using this
file as an input file allows skipping URLs that is already found
and process only the rows having the "website" column empty.
'''

from search_engines import *
from time import sleep

import sys, getopt, csv, re


def words_filter(s, num_chr=2):
    '''For a given string @s the function strips accents and other
    special chars. It also keeps words longer than @num_chr only.
    Set @num_chr = 0 for no filtering words by length

    Input
        @s:       str
        @num_chr: int

    Returns
        list of str
    '''

    fqs = SearchEngine.filter_query_string() # enclosed function

    return [
        UrlFinder.strip_accents(w) for w in fqs(s).split()
            if num_chr == 0 or len(w) > num_chr
    ]


def words_find(s, words):
    '''Calculates percentage of @words found in string @s

    Input
        @s:     str
        @words: list of str

    Returns
        float
    '''

    f = 0

    for w in words:
        f += bool(re.search(r'\b{}\b'.format(w), s, re.IGNORECASE))

    return f / len(words)


def words_find_all(s, words):
    '''Checks the string @s for containg all @words

    Input
        @s:     str
        @words: list of str

    Returns
        bool
    '''

    return words_find(s, words) >= 1


def sentence_find(s, words):
    '''Counts the amount sentences in @s containing all @words

    Input
        @s:     str
        @words: list of str

    Returns
        int
    '''
    f = 0

    for l in re.split(r'[\.!?]', s):
        f += words_find_all(l.strip(), words)

    return f


def str_filter(s):
    '''Normalizes string @s by stripping accents and filtering other characters

    Input
        @s: str

    Returns
        str
    '''

    return UrlFinder.strip_accents(s.strip())
    #return SearchEngine.filter_query_string()(UrlFinder.strip_accents(s.strip()))


def str_find_all(s, s2):
    '''Checks accent-insensitive occurrence of string @s2 in the string @s

    Input
        @s:  str (searchable string)
        @s2: str (search string)

    Returns
        bool
    '''

    return bool(s2 and re.search(UrlFinder.strip_accents(s2), s, re.IGNORECASE))


def str_find(s, s2):
    '''Checks for occurrence of the string @s2 in the string @s2

    Input
        @s:  str
        @s2: str

    Returns
        bool
    '''

    return s.find(s2) >= 0


def help_and_quit(err_msg=None):
    '''Displays help information
    '''

    if err_msg:
        print(err_msg)

    print(
'''
This web crawler finds corporate websites using information from the input CSV file.

$ python crawler.py -i <filename> -o <filename> [-s <number>] [-l <number>] [-u] [-h]

Options:
    -i <filename>   Specifies input CSV file. Mandatory option.
    -o <filename>   Specifies output CSV file. Mandatory option.
                    Output file can not be the same as the input file.
    -s <number>     Specifies how many rows to skip from the start. Optional.
                    If omitted, the process starts from the beginning of the input file.
    -l <number>     Limits number of rows to process. Optional.
                    If omitted, the process runs until the end of the input file will be reached.
    -u              Updates existing URLs. Optional.
                    By default, the rows having "website" column already filled is not processed.
                    Use this parameter to force crawling process again for the such rows.
    -h              Displays this help information.
''')

    quit()


def main(fn_input, fn_output, start, limit):
    '''Main processing function

    The crawler builds around @UrlFinder class and its method ".get" which
    takes a string as an argument, performs the search over the Internet
    for a list of URLs related to this string, and returns a single URL if the
    search process has been completed successfully. Otherwise, it returns None.

    To init an instance of @UrlFinder class it is required to specify the
    following arguments:
    1) list of search engines that are used to build a list of URLs related
       to the query string that probably might be corporate website addresses.
       Each search engine in the list is an instance of any child class derived
       from the @SearchEngine class. The only two @SearchEngine's child classes
       are available right now: @GoogleCustomSearch and @GoogleSearch. The first
       one uses "Google Custom Search JSON API" which is not a free-of-charge
       service. It also requires having <App ID> and <API Key>. The second one
       uses parsing of search results taken on the "Google Search" website, which
       is free of charge but the requests to the website are time-limited.
    2) keyword argument @proc:dict defines a series of validation rules used to
       check the URL for being an address of the corporate website. The @proc's
       keys represent column names from the input CSV file. And the @proc's
       values are lists of tuples. Each tuple represents a validation rule:
       (None or <string filter function>, <string search function>,
        <weight>, <content function>)
    3) keyword argument @skip_social:bool defines skipping or not URLs of
       social networks during validation process;
    4) keyword argument @home_only:bool defines skipping non-homepage URLs;
    5) keyword argument @threshold:float is a value of weight for the URLs
       to be filtered below or equal this value. Set it to 999 for no threshold.
    '''

    proc = {
        'name': [
            (str_filter,   str_find_all,   1.0, UrlFinder.html_title),
            (words_filter, words_find_all, 0.3, UrlFinder.html_title),
            (words_filter, words_find,     0.1, UrlFinder.html_title),
            (str_filter,   str_find_all,   1.0, UrlFinder.meta_description),
            (words_filter, words_find_all, 0.3, UrlFinder.meta_description),
            (words_filter, words_find,     0.1, UrlFinder.meta_description),
            (str.strip,    str_find_all,   1.0, UrlFinder.h1_text),
            (words_filter, words_find_all, 0.3, UrlFinder.h1_text),
            (words_filter, words_find,     0.1, UrlFinder.h1_text),
            (str_filter,   str_find_all,   1.0, UrlFinder.body_text),
            (words_filter, sentence_find,  0.5, UrlFinder.body_text),
        ],
        'city': [
            (str_filter,   str_find_all,   0.1, UrlFinder.html_title),
            (str_filter,   str_find_all,   0.1, UrlFinder.meta_description),
            (str_filter,   str_find_all,  0.05, UrlFinder.body_text),
        ],
        'country': [
            (str_filter,   str_find_all,   0.1, UrlFinder.html_title),
            (str_filter,   str_find_all,   0.1, UrlFinder.meta_description),
            (str_filter,   str_find_all,  0.05, UrlFinder.body_text),
        ],
        'phone': [
            (str_filter,   str_find,       1.0, UrlFinder.html_title),
            (str_filter,   str_find,       0.5, UrlFinder.meta_description),
            (str_filter,   str_find,       0.1, UrlFinder.body_text),
        ],
        'postcode': [
            (str_filter,   str_find,       0.1, UrlFinder.body_text),
        ],
        'street_line_1': [
            (str_filter,   str_find_all,   0.5, UrlFinder.body_text),
        ],
    }

    u = UrlFinder([
            #GoogleCustomSearch(filter=True),
            GoogleSearch(num=30),
        ],
        proc, home_weight=0.0, skip_social=True, home_only=True, threshold=0.05
    )

    i = 1

    with open(fn_input, 'r', encoding='utf-8') as fi, \
        open(fn_output, 'w', newline='', encoding='utf-8') as fo:

        csv.register_dialect('excelesc', doublequote=False, delimiter=',', escapechar='\\', quoting=csv.QUOTE_MINIMAL)

        samples = csv.DictReader(fi, dialect='excelesc')

        fields = samples.fieldnames

        if 'website' not in samples.fieldnames:
            fields.append('website')

        dw = csv.DictWriter(fo, fieldnames=fields, dialect='excelesc')

        dw.writeheader()

        for s in samples:
            brk = (limit > 0) and (i - start >= limit)

            if not brk and i >= start and (not s.get('website') or update):
                lnk_found = u.get('"{}"'.format(s['name']), s)
                #lnk_found = u.get('"{}" +"{}" +"{}"'.format(s['name'], s['country'], s['city']), s)

                print(s['id'], '>', s['name'], '>', lnk_found)

                s.update({'website': lnk_found})

                sleep(15)

            dw.writerow(s)

            i = i + 1

        fo.close()


if __name__ == '__main__':
    fn_input = None
    fn_output = None

    update = False

    start = 0
    limit = 0

    try:
        opts, args = getopt.getopt(sys.argv[1:], 's:l:i:o:hu')

        for opt, val in opts:
            if opt == '-i':
                fn_input = val

            if opt == '-o':
                fn_output = val

            if opt == '-s':
                start += int(val)

            if opt == '-l':
                limit = int(val)

            if opt == '-h':
                help_and_quit()

            if opt == '-u':
                update = True

    except getopt.GetoptError as e:
        help_and_quit('Wrong input parameters: ' + str(e))

    if not fn_input or not fn_output or fn_input == fn_output:
        help_and_quit()

    main(fn_input, fn_output, start, limit)


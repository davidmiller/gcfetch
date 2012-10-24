"""
gcfetch

Package init file
"""
import collections
import json
import re
import sys
import urlparse

import argparse
from lxml import html
import requests

from _version import __version__

# C&P from another project
def protocolise(url):
    """
    Given a URL, check to see if there is an assocaited protocol.

    If not, set the protocol to HTTP and return the protocolised URL
    """
    # Use the regex to match http//localhost/something
    protore = re.compile(r'https?:{0,1}/{1,2}')
    parsed = urlparse.urlparse(url)
    if not parsed.scheme and not protore.search(url):
        url = 'http://{0}'.format(url)
    return url

def indomain(url, domain):
    """
    Predicate function to determine whether URL is in DOMAIN


    Arguments:
    - `url`: str
    - `domain`: str

    Return: bool
    Exceptions: None
    """
    if url and domain:
        return url.startswith(domain)
    return False

def getstatic(markup):
    """
    Given some MARKUP, return a list of the static assets.

    Arguments:
    - `markup`: lxml.html.HtmlElement

    Return: [str,]
    Exceptions: None
    """
    statics = []
    statictags = [
        ('script', 'src'),
        ('link', 'href'),
        ('img', 'src')
        ]
    for tag, attr in statictags:
        for elem in markup.cssselect(tag):
            target = elem.get(attr, None)
            if target:
                statics.append(target)
    return statics

def getlinks_to(markup, domain):
    """
    Given some MARKUP, return a list of links that are in DOMAIN


    Arguments:
    - `markup`: lxml.html.HtmlElement
    - `domain`: str

    Return: [str,]
    Exceptions: None
    """
    links = []
    for link in markup.cssselect('a'):
        target = link.get('href')

        if indomain(target, domain):
            links.append(target)

    return links

def fetch_website(sitemap, base, url):
    """
    Recursive function to fill SITEMAP with the documents that
    make up BASE, looking at URL at the first pass.


    Arguments:
    - `sitemap`: dict
    - `base`: str
    - `url`: str

    Return: None
    Exceptions: None
    """
    # Use requests because lxml's default fetch url code doesn't
    # respect 301 redirects
    req = requests.get(url)

    root = html.document_fromstring(req.content)
    root.make_links_absolute(base)

    sitemap[url]['statics'] = getstatic(root)
    sitemap[url]['links'] = getlinks_to(root, base)

    for link in sitemap[url]['links']:
        if link not in sitemap:
            fetch_website(sitemap, base, link)

    return


def main(args):
    """
    Entrypoint when run as a script

    Arguments:
    - `args`: argparse Arglist

    Return: int
    Exceptions: None
    """
    # Most of the URL fetching libraries will want an explicit protocol.
    # Allow loose commandline args
    base = protocolise(args.domain)

    sitemap = collections.defaultdict(lambda: collections.defaultdict(list))
    fetch_website(sitemap, base, base)

    print json.dumps(sitemap, indent=2)

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and visualise website sitemaps")
    parser.add_argument('domain', help="Domain you'd like to scrape")
    args = parser.parse_args()
    sys.exit(main(args))

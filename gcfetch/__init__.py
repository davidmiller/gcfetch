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
import matplotlib.pyplot as plt
import networkx
import pylab
import requests

from _version import __version__

DONE = """
*******************************************************
Dear valued user,

Your sitemap is ready to view at {0}.

Please use your favourite image viewer to take a look.
"""

PROTORE = re.compile(r'https?:{0,1}/{1,2}')

# originally C&P from another project
def protocolise(url):
    """
    Given a URL, check to see if there is an assocaited protocol.

    If not, set the protocol to HTTP and return the protocolised URL
    """
    parsed = urlparse.urlparse(url)
    if not parsed.scheme and not PROTORE.search(url):
        url = 'http://{0}'.format(url)
    return url

def deprotocolise(url):
    """
    If URL has a protocol, strip it.

    Arguments:
    - `url`: str

    Return: str
    Exceptions: None
    """
    return PROTORE.sub('', url)


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

def fetch_website(sitemap, seen, base, url):
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
    print url
    # Use requests because lxml's default fetch url code doesn't
    # respect 301 redirects
    req = requests.get(url)

    root = html.document_fromstring(req.content)
    root.make_links_absolute(base)

    seen.add(url)

    statics = getstatic(root)
    links = getlinks_to(root, base)

    sitemap.add_node(url, statics=statics, links=links)

    for link in links:
        sitemap.add_edge(url, link)

        if link not in seen:
            fetch_website(sitemap, seen, base, link)

    return

def output(sitemap, domain):
    """
    Produce our representation of the graph SITEMAP

    Arguments:
    - `graph`: networkx.DiGraph

    Return: None
    Exceptions: None
    """
    labels = dict((n, n +"\n" + ("-" * len(n)) + "\n" + "\n".join(d['statics'])) for n,d in sitemap.nodes(data=True))
    networkx.draw(sitemap, labels=labels)
    # Adjust the size up to the point at which it's useful
    F = pylab.gcf()
    DPI = F.get_dpi()
    DEF = F.get_size_inches()
    F.set_size_inches(DEF[0] * 5, DEF[1] * 5)

    filename = '{0}.sitemap.png'.format(domain)
    plt.savefig(filename)
    return filename

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

    seen = set()
    sitemap = networkx.DiGraph()
    fetch_website(sitemap, seen, base, base)

    outfile = output(sitemap, deprotocolise(base))

    print DONE.format(outfile)

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and visualise website sitemaps")
    parser.add_argument('domain', help="Domain you'd like to scrape")
    args = parser.parse_args()
    sys.exit(main(args))

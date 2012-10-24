"""
gcfetch
"""
import collections
import json
import itertools
import re
import sys
import time
import urlparse

import argparse
import gevent
from gevent import monkey
from lxml import html
import matplotlib.pyplot as plt
import networkx
import pylab
import requests

monkey.patch_all()

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

    SEEN should be a set of urls we have encountered already, and
    thus should not parse.

    Arguments:
    - `sitemap`: dict
    - `seen`: set
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

def fetch_url_gevent(sitemap, base, url):
    """
    Expected to be the target function of a Greenlet, we
    fetch a single URL, parse it, and add it's information to
    the SITEMAP.

    Arguments:
    - `sitemap`: networkx.DiGraph
    - `base`: str
    - `url`: str

    Return: None
    Exceptions: None
    """
    print "starting", url
    markup = html.document_fromstring(requests.get(url).content)
    print "got", url
    markup.make_links_absolute(base)
    statics, links = getstatic(markup), getlinks_to(markup, base)
    sitemap.add_node(url, statics=statics, links=links)
    for link in links:
        sitemap.add_edge(url, link)
    return links

def fetch_website_gevent(sitemap, seen, base, urls):
    """
    Recursive function to fill SITEMAP with the documents that
    make up BASE, looking at each url in URLS at the first pass.

    SEEN should be a set of urls we have encountered already, and
    thus should not parse.1

    Arguments:
    - `sitemap`: dict
    - `seen`: set
    - `base`: str
    - `urls`: [str,]

    Return:
    Exceptions:
    """
    jobs = [gevent.spawn(fetch_url_gevent, sitemap, base, u) for u in urls]
    gevent.joinall(jobs)
    links = set(itertools.chain(*[greenlet.get() for greenlet in jobs]))
    unseen = links.difference(seen)
    if unseen:
        seen.update(unseen)
        fetch_website_gevent(sitemap, seen, base, unseen)
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
    # These work decreasingly well for larger sites.
    # I guess that's to be expected, as top notch visualisation of
    # these kind of graphs is, itself an interesting problem.
    # Possibly out of scope here.
    networkx.draw(sitemap, labels=labels)
    # Adjust the size up to the point at which it's useful
    F = pylab.gcf()
    DPI = F.get_dpi()
    DEF = F.get_size_inches()
    F.set_size_inches(DEF[0] * 5, DEF[1] * 5)

    filename = '{0}.sitemap.png'.format(domain)
    plt.savefig(filename)
    return filename

def bench_report(t1, t2):
    """
    Simplistic benchmarking reporting. Print the time taken.

    Arguments:
    - `t1`: float
    - `t2`: float

    Return: None
    Exceptions: None
    """
    print "\n\n Time taken: {0}".format(t2 - t1)


def main(args):
    """
    Entrypoint when run as a script

    Arguments:
    - `args`: argparse Arglist

    Return: int
    Exceptions: None
    """
    t1 = time.time()
    # Most of the URL fetching libraries will want an explicit protocol.
    # Allow loose commandline args
    base = protocolise(args.domain)

    seen = set()
    sitemap = networkx.DiGraph()

    #fetch_website(sitemap, seen, base, base)
    fetch_website_gevent(sitemap, set([base]), base, [base])

    outfile = output(sitemap, deprotocolise(base))

    t2 = time.time()
    print DONE.format(outfile)
    if args.bench:
        bench_report(t1, t2)

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Fetch and visualise website sitemaps")
    parser.add_argument('domain', help="Domain you'd like to scrape")
    parser.add_argument('-b', '--bench', action="store_true", help="Benchmark this run")
    args = parser.parse_args()
    sys.exit(main(args))

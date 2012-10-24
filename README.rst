
How to generate a sitemap:

$ git clone https://github.com/davidmiller/gcfetch.git

$ virtualenv /where/you/put/your/virtualenvs/gcfetch

$ . /where/you/put/your/virtualenvs/gcfetch/bin/activate

$ pip install numpy

$ pip install -r requirements.txt

$ python gcfetch.py yourfancydomain.py

Notes:

There's some funkiness with the Python matplotlib bindings which means that they both bomb out on failed dependencies when installing, and also don't just require those dependencies.

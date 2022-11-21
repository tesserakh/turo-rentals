import sys, os
sys.path.append(os.path.abspath(os.path.pardir))

from turo import crawler
from logging import config

config.fileConfig(fname='../config.conf', disable_existing_loggers=False)
crawler.turo_crawl(
    [
        'https://turo.com/us/en/search?location=Denver%2C%20CO',
        'https://turo.com/us/en/search?location=Phoenix%2C%20AZ'
    ]
)

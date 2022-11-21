from turo import crawler
from turo import scraper
from logging import config
import logging
import json

def crawl(keywords:list, output_file:str) -> None:
    # output_file in txt
    urls = crawler.turo_crawl(keywords=keywords)
    url_list = []
    for url in urls:
        if url not in url_list:
            url_list.append(url)
    with open(output_file, 'w') as fout:
        fout.write('\n'.join(str(url) for url in url_list))
    fout.close()
    return

def scrape(input_file:str, output_file:str) -> None:
    # input txt, output json
    with open(input_file, 'r') as fin:
        urls = [url.replace('\n', '') for url in fin.readlines()]
    fin.close()
    data = scraper.turo_scrape(urls[0:10])
    with open(output_file, 'w') as fout:
        json.dump(data, fout)
    fout.close()
    return

def print_result(data_file:str):
    with open(data_file, 'r') as read_data:
        data = json.load(read_data)
    read_data.close()
    return print(json.dumps(data, indent=2))

if __name__ == '__main__':
    config.fileConfig(fname='config.conf', disable_existing_loggers=False)
    logging.basicConfig(level=logging.DEBUG)
    query = [
        'https://turo.com/us/en/search?location=Denver%2C%20CO',
        'https://turo.com/us/en/search?location=Phoenix%2C%20AZ'
    ]
    crawl(query, 'urls.txt')
    #crawler.turo_crawl(keywords=query)
    scrape('urls.txt', 'sample-cars.json')


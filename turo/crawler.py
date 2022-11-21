from playwright.sync_api import sync_playwright
from playwright.sync_api import Page
from turo.settings import HEADLESS
import logging

logger = logging.getLogger('crawler')

def get_sitemap():
    """ Crawl Turo sitemap """
    pass

def turo_crawl(keywords:list) -> None:
    """ Crawl Turo by given url """
    with sync_playwright() as p:
        # open browser
        browser = p.firefox.launch(headless=HEADLESS)
        page = browser.new_page()
        for query in keywords:
            try:
                # browse the web
                page.goto(query, timeout=90000)
                logger.info(f'GET {query}')
                # initial values
                item_links = []
                items_count = 0
                scroll_down = True
                scroll_count = 0
                # crawl the page
                while scroll_down:
                    logger.debug('Scrolling...')
                    links = navigate_scroll_get_data(page)
                    for link in links:
                        if link not in item_links:
                            item_links.append(link)
                    scroll_count += 1
                    page.wait_for_timeout(2000)
                    if items_count != len(item_links):
                        items_count = len(item_links)
                        continue
                    else:
                        scroll_down = False
                        logger.debug(f'Scrolling done {str(scroll_count * 20)}x')
                        logger.debug(f'Items count {items_count} {query}')
                        # yield here
                        logger.info(f'{item_links}')
            except Exception as e:
                logger.error(f'Failed to reach {query}: {e}')
                continue

        # close browser
        browser.close()
    return

def navigate_scroll_get_data(page:Page, x=20, timeout=6000) -> list:
    """ Page scroll to load all the listing products
    Positive x is scrolling down, negative x is scrolling up
    """
    a = 1 if x >= 0 else -1
    data = []
    for i in range((x * a)): # make the range (x) as long as needed
        page.mouse.wheel(0, 15000) # h=0, v=15000
        page.wait_for_load_state()
        page.wait_for_timeout(timeout)
        items = page.query_selector_all('div.searchResult > a')
        for a in items:
            link = 'https://turo.com' + a.get_attribute('href').split('?')[0]
            if link not in data:
                data.append(link)
        i += 1
    return data

if __name__ == '__main__':
    pass

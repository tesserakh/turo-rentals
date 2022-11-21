from playwright.sync_api import sync_playwright
from playwright.sync_api import Page
from turo.settings import HEADLESS
from datetime import datetime
import logging
import re

logger = logging.getLogger('scraper')

def turo_scrape(urls:list) -> list:
    """ Scrape Turo rental details """
    with sync_playwright() as p:
        # open browser
        browser = p.firefox.launch(headless=HEADLESS)
        page = browser.new_page()
        data = []
        for url in urls:
            # browse the website
            try:
                page.goto(url, timeout=60000)
                logger.info(f"GET {url}")
                page.wait_for_load_state()
            except Exception as e:
                logger.error(f'Error {url}: str(e)')
                continue
            # parse website
            data.append(parse(page))
        # close browser
        browser.close()
    return data

def parse(page:Page) -> dict:
    """ Parse individual item page """
    # scrolling to load all content
    navigate_scroll(page)
    page.wait_for_load_state()

    # car type, make
    vehicle_category = {
        'car-rental': 'Sedan',
        'classic-rental': 'Classic',
        'electric-vehicle-rental': 'Electric',
        'convertible-rental': 'Convertible', 
        'exotic-luxury-rental': 'Exotic & luxury',    
        'minivan-rental': 'Minivan',
        'sports-rental': 'Sport',
        'suv-rental': 'SUV',
        'truck-rental': 'Truck',
        'van-rental': 'Van'
    }
    for item in page.url.split('?')[0].split('/'):
        if item in list(vehicle_category.keys()):
            car_type = vehicle_category[item]

    # car name, year, make, model, trim, trips
    page.wait_for_selector('div[class*=VehicleLabelContainer]')
    section_title = page.query_selector('div[class*=VehicleLabelContainer]')
    name = section_title.query_selector('h1').inner_text().replace('\n', ' ')
    year = int(re.findall(r'\d{4}', name)[0])
    make = page.url.split('?')[0].split('/')[8]
    if make in ['bmw', 'fiat', 'gmc', 'hummer']:
        make = make.upper()
    else:
        make = make.title()
    if make not in ['Mercedes-Benz', 'Rolls-Royce']:
        make = make.replace('-', ' ')
    model = name.replace(make, '').replace(str(year), '').strip()
    try:
        car_trim = section_title.query_selector('span > p > span').inner_text().strip()
    except:
        car_trim = None
    try:
        n_trip = section_title.query_selector('div[class*=StarRatingAndCountContainer] > div > p').inner_text()
        n_trip = int(re.findall(r'\d+', n_trip)[0])
    except:
        n_trip = None
    
    # details = mpg, doors, seats, fuel
    detail_items = {'seats': None, 'doors': None, 'mpg': None, 'fuel_type': None}
    other_items = []
    try:
        details = [item.inner_text() for item in page.query_selector_all('div[class*=TagContainer] > p')]
        for item in details:
            try:
                item_value = int(re.findall(r'\d+', item)[0])
                if re.findall(r'mpg', item.lower()):
                    detail_items.update({'mpg': item_value})
                elif re.findall(r'door', item.lower()):
                    detail_items.update({'doors': item_value})
                elif re.findall(r'seat', item.lower()):
                    detail_items.update({'seats': item_value})
                else:
                    pass
                    #other_items.append(item)
            except:
                if re.findall(r'gas', item.lower()):
                    detail_items.update({'fuel_type': item})
                elif re.findall(r'electric', item.lower()):
                    detail_items.update({'fuel_type': item})
                else:
                    pass
                    #other_items.append(item)
        #other_items = ', '.join(other_items)
        #detail_items.update({'others': other_items})
    except Exception as e:
        logger.warning(f"Failed in TAG seat, door, mpg, fuel: {e} ({page.url})")

    # number of pictures
    n_pic = len(page.query_selector_all('div[class*=ImageContainer]'))

    # distance included, additional price per mile
    try:
        section_sidebar = page.query_selector('div[class*=SideBarWrapper]')
        sidebar_items = section_sidebar.query_selector_all('div[class*=WrapperWithMarginBottom]')
        distance_service = {'daily_distance_included': None, 'price_per_miles': None}
        for item in sidebar_items:
            try:
                if item.query_selector('div > div > p').inner_text().lower() == 'distance included':
                    distance_included = item.query_selector_all('div > div > p')[-1].inner_text().strip()
                    if distance_included != 'Unlimited':
                        distance_addition = item.query_selector_all('div > p')[-1].inner_text()
                        distance_addition = distance_addition.replace('fee for additional miles driven','').strip()
                    else:
                        distance_addition = None
                    distance_service.update({
                        'daily_distance_included': distance_included,
                        'price_per_miles': distance_addition
                    })
                else:
                    pass
            except:
                pass
    except Exception as e:
        logger.warning(f"Failed in FEATURE delivery inc., price per miles: {e} ({page.url})")


    # daily rate, minimum age
    page.locator('button', has_text='est. total').first.click()
    page.wait_for_timeout(2500)
    price_feature = {'avg_daily_rate': None, 'discount': None, 'age_min': None}
    popup = page.query_selector('div[class*=ModalBody]')
    popup_price = popup.query_selector_all('span[class*=StyledText]')
    popup_price = [item.inner_text() for item in popup_price]
    #logger.debug(str(popup_price))
    for item in popup_price:
        price_item = item
        if re.findall(r'day', price_item) and not re.findall(r'discount', price_item):
            price_daily = re.findall(r'\$\d+', price_item)[0]
            price_feature.update({'avg_daily_rate': price_daily})
        elif re.findall(r'discount', price_item):
            discount = re.findall(r'\d+', price_item)[0]
            price_feature.update({'discount': price_item.replace('discount','').strip()})
        else:
            pass
    popup_info = popup.query_selector_all('p[class*=StyledText]')
    popup_info = [item.inner_text() for item in popup_info]
    #logger.debug(str(popup_info))
    for i in range(len(popup_info)):
        if popup_info[i] == 'Young driver fee': index_age_min = i + 1
    price_feature.update({'age_min': popup_info[index_age_min]})
    close_button = page.locator('button[data-testid=modal-base-close-button]')
    if close_button.is_visible(): close_button.click()

    # rating, reviews
    try:
        rating = float(page.query_selector('div[class*=StarRatingAndCountContainer] > div > div > p').inner_text())
    except:
        rating = None
    try:
        reviews = page.query_selector('div[class*=StarRatingAndCountContainer] > p').inner_text()
        reviews = int(re.findall(r'\d+', reviews)[0])
    except:
        reviews = None

    # delivery and pickup location
    try:
        section_location = page.query_selector('div[class*=MapWrapper]')
        map_items = section_location.query_selector_all('div > div > div')
        map_items = [item.inner_text() for item in map_items]
        #logger.debug(str(map_items))
        location_fee = []
        for item in map_items:
            map_value = item.split('\n')
            if len(map_value) == 2:
                location_fee.append(' '.join(map_value))
        location_pickup = location_fee[0].replace('FREE','').strip()
        location_delivery = ', '.join(location_fee[1:])
        pickup_delivery = {
            'location_pickup': location_pickup,
            'location_delivery': location_delivery
        }
    except Exception as e:
        logger.warning(f"Failed in LOCATION pickup, delivery: {e} ({page.url})")

    # amount of bookings per month
    calendar_info = {'days_booking_per_month': None}
    page.locator('input[name=reservationDates-dateRangePicker]').click()
    try:
        page.wait_for_selector('div.CalendarMonth')
        page.wait_for_timeout(2000)
        section_calendar = page.query_selector_all('div.CalendarMonth')
        days_booking_per_month = []
        for calendar in section_calendar[1:]: # from current month, not previous
            month = calendar.query_selector('div > p').inner_text()
            table = calendar.query_selector('table')
            rows = table.query_selector_all('tr')
            count_booked = 0
            for row in rows:
                date_button = row.query_selector_all('td[role=button]')
                for button in date_button:
                    date_string = button.query_selector('div.CalendarDay_content').inner_text().strip()
                    date_string = ' '.join([date_string, month])
                    date_date = datetime.strptime(date_string, '%d %B %Y')
                    if date_date > datetime.now(): # tomorrow, today is not counted
                        button_disabled = button.get_attribute('aria-disabled')
                        if button_disabled == 'true':
                            date_booked = True # disabled=yes (grey date) but not coret
                        else:
                            date_booked = False # disabled=no (can be selected)
                        if date_booked:
                            count_booked += 1
            days_booking_per_month.append(f"{month} = {count_booked}")
        days_booking_per_month = ', '.join(days_booking_per_month)
        calendar_info.update({'days_booking_per_month': days_booking_per_month})
    except Exception as e:
        logger.error(f'Failed in CALENDAR: {str(e)} ({page.url})')

    
    data = {
        'name': name,
        'car_type': car_type,
        'year': year,
        'make': make,
        'model': model,
        'trim': car_trim,
        'rating': rating,
        'reviews': reviews,
        'n_picture': n_pic,
        'trip': n_trip,
    }
    data.update(detail_items)
    data.update(price_feature)
    data.update(distance_service)
    data.update(pickup_delivery)
    data.update(calendar_info)
    data.update({
        'date_stamp': datetime.now().strftime('%Y-%m-%d'),
        'url': page.url.split('?')[0]
    })
    
    logger.info(data)
    
    return data

def navigate_scroll(page:Page, x=5, timeout=3000) -> None:
    """ Page scroll to get all the content of product page rendered
    Positive x is scrolling down, negative x is scrolling up
    """
    a = 1 if x >= 0 else -1
    for i in range((x * a)): # make the range (x) as long as needed
        page.mouse.wheel(0, 15000) # h=0, v=15000
        page.wait_for_timeout(timeout)
        i += 1
    return

if __name__ == '__main__':
    pass

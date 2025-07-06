import datetime
import logging
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, TimeoutException, ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyvirtualdisplay import Display

CHROME_EXECUTABLE_PATH_ENV = 'CHROME_EXECUTABLE_PATH'

PSC_EMAIL_ENV = 'PSC_EMAIL'
PSC_PASSWORD_ENV = 'PSC_PASSWORD'

# Login site constants.
PSC_LOGIN = 'https://picklesocialclub.playbypoint.com/users/sign_in'
EMAIL_XPATH = '//input[@id="user_email"]'
PASSWORD_XPATH = '//input[@id="user_password"]'
LOGIN_BUTTON_XPATH = '//input[@type="submit"]'

# Booking site constants.
BOOKING_SITE = "https://picklesocialclub.playbypoint.com/book/picklesocialclub"
DAY_SELECTION_XPATH = '//button[div[@class="day_number" and text()="{}"]]'
COVERED_TYPE_SELECTION_XPATH = '//button[text()="Covered Pickleball"]'
OUTDOOR_TYPE_SELECTION_XPATH = '//button[text()="Outdoor Pickleball"]'
TIME_SELECTION_1_XPATH = '//button[text()="8-9am"]'
TIME_SELECTION_2_XPATH = '//button[text()="9-10am"]'
CLUB_CREDITS_SELECTION_XPATH = '//a[text()="Club credits"]'
CLUB_CREDITS_ACTIVE_XPATH = '//a[@class="item active" and text()="Club credits"]'
BOOK_BUTTON_XPATH = '//button[text()="Book"]'
NEXT_BUTTON_XPATH = '//div[@class="content active"]//button[span[text()=" Next "]]'
SECTIONS_XPATH = '//div[@class="StepperItem StepperItemFluid "]'
CONTENT_ACTIVE_XPATH = '//div[@class="content active"]'
INNER_HTML_ATTRIBUTE = 'innerHTML'


logger = logging.getLogger(__name__)


class ElementNotFound(Exception):
  """Raised when an element cannot be found on the webpage."""


def login_to_coursite(driver, psc_email, psc_password):
  """Logs in to courtsite using email and password.
  
  Args:
    driver: Selenium webdriver used for interacting with the websites.
    psc_email: Login email for PSC booking site.
    psc_password: Login password for PSC booking site.
  """
  
  driver.get(PSC_LOGIN)

  email_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, EMAIL_XPATH))
  )
  password_element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, PASSWORD_XPATH))
  )

  email_element.send_keys(psc_email)
  password_element.send_keys(psc_password)

  driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH).click()

  # Wait 10 seconds to login.
  time.sleep(10)


def click_button_by_xpath(driver, button_xpath):
  """Waits for button to be present and clickable and clicks it.
  
  Args:
    driver: Selenium webdriver used for interacting with the websites.
    button_xpath: Xpath of the button element.

  Raises:
    TimeoutException: When element cannot be found or clicked.
  """
  for _ in range(2):
    try:
      element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, button_xpath))
      )
      logger.info(f'Clicking button: {element.get_attribute(INNER_HTML_ATTRIBUTE)}')
      element.click()
      time.sleep(5)
      break
    except (StaleElementReferenceException, ElementClickInterceptedException):
      logger.exception(f'Stale when trying to click button.')


def click_time_selection(driver, time_selection_xpath):
  for _ in range(2):
    try:
      time_selection_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, time_selection_xpath))
      )
      if 'red' in time_selection_element.get_attribute('class').split(' '):
        logger.error(f'Time selection not available: {time_selection_xpath}')
        return False
      if 'primary' in time_selection_element.get_attribute('class').split(' '):
        return True
      logger.info(f'time selection {time_selection_element.get_attribute(INNER_HTML_ATTRIBUTE)}')
      time_selection_element.click()
      time.sleep(5)
      # Verify time selected.
      time_selection_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, time_selection_xpath))
      )
      if 'primary' not in time_selection_element.get_attribute('class'):
        logger.error('Time available but did not click.')
        return False
      return True
    except StaleElementReferenceException as e:
      logger.exception('Stale reference exception.')
  return False


def contains_element(element, child_xpath):
  try:
    element.find_element(By.XPATH, child_xpath)
    return True
  except NoSuchElementException:
    return False


def book_court(driver, covered):
  """Books a court 7 days later.
  
  Args:
    driver: Selenium webdriver used for interacting with the websites.
    covered: Whether to book covered or outdoor court.

  Returns:
    Boolean for whether the booking was successful.
  """
  driver.get(BOOKING_SITE)

  booking_date = datetime.datetime.today() + datetime.timedelta(7)
  court_type_xpath = COVERED_TYPE_SELECTION_XPATH if covered else OUTDOOR_TYPE_SELECTION_XPATH
  day_number = str(booking_date.day) if booking_date.day >= 10 else f'0{booking_date.day}'
  logger.info(f'Trying to book for {day_number}, covered: {covered}.')
  try:
    click_button_by_xpath(driver, DAY_SELECTION_XPATH.format(day_number))
    click_button_by_xpath(driver, court_type_xpath)
    time_selection_1_result = click_time_selection(driver, TIME_SELECTION_1_XPATH)
    time_selection_2_result = click_time_selection(driver, TIME_SELECTION_2_XPATH)
    if not (time_selection_1_result or time_selection_2_result):
      logger.error(f'Both time selections not available.')
      return False
  except (TimeoutException, ElementNotInteractableException) as e:
    logger.exception(f'Failed to select time. Court may be unavailable.')
    return False

  try:
    sections = driver.find_elements(By.XPATH, SECTIONS_XPATH)
    if not contains_element(sections[0], CONTENT_ACTIVE_XPATH):
      logger.error('Wrong div active.')
    click_button_by_xpath(driver, NEXT_BUTTON_XPATH)
    # Verify next section active.
    if not contains_element(sections[1], CONTENT_ACTIVE_XPATH):
      logger.error('Wrong div active1.')
    time.sleep(3)
    click_button_by_xpath(driver, NEXT_BUTTON_XPATH)
    # Verify next section active.
    if not contains_element(sections[2], CONTENT_ACTIVE_XPATH):
      logger.error('Wrong div active2.')
    click_button_by_xpath(driver, CLUB_CREDITS_SELECTION_XPATH)
    # Wait for club credits to be selected.
    WebDriverWait(driver, 10).until(
      EC.presence_of_element_located((By.XPATH, CLUB_CREDITS_ACTIVE_XPATH))
    )
    click_button_by_xpath(driver, BOOK_BUTTON_XPATH)
    time.sleep(10)
  except (TimeoutException, ElementNotInteractableException) as e:
    logger.exception(f'Failed to complete booking.')
    return False
  logger.info('Booked court.')
  return True


def main():
  logging.basicConfig(
    # stream=sys.stdout,
    filename='pscbook.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

  try:
    display = Display(visible=0, size=(1920, 1080)) 
    display.start()
    chrome_options = Options()
    if CHROME_EXECUTABLE_PATH_ENV in os.environ:
      driver = webdriver.Chrome(
        service=webdriver.ChromeService(
          executable_path=os.environ[CHROME_EXECUTABLE_PATH_ENV]),
        options=chrome_options)
    else:
      driver = webdriver.Chrome(options=chrome_options)
  except Exception as e:
    logger.exception('Failed to start chrome.')
    return

  try:
    psc_email = os.environ[PSC_EMAIL_ENV]
    psc_password = os.environ[PSC_PASSWORD_ENV]
    login_to_coursite(driver, psc_email, psc_password)
    logger.info('Logged in.')
    covered = False
    for _ in range(3):
      booking_successful = book_court(driver, covered)
      if covered and not booking_successful:
        covered = False
        booking_successful = book_court(driver, covered)
      logger.info(f'Booking result: {booking_successful}')
  finally:
    logger.info('Completed bookings.')
    driver.quit()

if __name__ == '__main__':
  main()

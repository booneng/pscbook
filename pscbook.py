import datetime
import logging
import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
TYPE_SELECTION_XPATH = '//button[text()="Covered Pickleball"]'
TIME_SELECTION_1_XPATH = '//button[@class="ButtonOption ui button basic  " and text()="8-9am"]'
TIME_SELECTION_2_XPATH = '//button[@class="ButtonOption ui button basic  " and text()="9-10am"]'
BOOK_BUTTON_XPATH = '//button[text()="Book"]'
NEXT_BUTTON_XPATH = '//div[@class="content active"]//button[span[text()=" Next "]]'

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



def click_button(driver, button_xpath):
  """Waits for button to be present and clickable and clicks it.
  
  Args:
    driver: Selenium webdriver used for interacting with the websites.
    button_xpath: Xpath of the button element.

  Raises:
    TimeoutException: When element cannot be found or clicked.
  """
  element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.XPATH, button_xpath))
  )
  element = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable(element)
  )

  times = 0
  while (times < 2):
    try:
      element.click()
      break
    except (StaleElementReferenceException, ElementClickInterceptedException):
      times += 1


def book_court(driver):
  """Books a court 7 days later.
  
  Args:
    driver: Selenium webdriver used for interacting with the websites.
  """
  driver.get(BOOKING_SITE)

  booking_date = datetime.datetime.today() + datetime.timedelta(7)
  click_button(driver, DAY_SELECTION_XPATH.format(booking_date.day))
  click_button(driver, TYPE_SELECTION_XPATH)
  time.sleep(5)
  logger.info(f'Trying to book for {booking_date.day}.')
  try:
    click_button(driver, TIME_SELECTION_1_XPATH)
    time.sleep(2)
    click_button(driver, TIME_SELECTION_2_XPATH)
  except TimeoutException as e:
    logging.exception('Failed to select time. Court may be unavailable.')
    return
  click_button(driver, NEXT_BUTTON_XPATH)
  time.sleep(5)
  click_button(driver, NEXT_BUTTON_XPATH)
  click_button(driver, BOOK_BUTTON_XPATH)
  logger.info('Booked court.')
  time.sleep(10)  


def main():
  logging.basicConfig(
    filename='pscbook.log',
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')
  chrome_options = Options()
  chrome_options.add_argument('--no-sandbox')
  chrome_options.add_argument('--disable-dev-shm-usage')
  if CHROME_EXECUTABLE_PATH_ENV in os.environ:
    driver = webdriver.Chrome(
      service=webdriver.ChromeService(
        executable_path=os.environ[CHROME_EXECUTABLE_PATH_ENV]),
      options=chrome_options)
  else:
    driver = webdriver.Chrome(options=chrome_options)
  try:
    psc_email = os.environ[PSC_EMAIL_ENV]
    psc_password = os.environ[PSC_PASSWORD_ENV]
    login_to_coursite(driver, psc_email, psc_password)
    logger.info('Logged in.')
    for _ in range(2):
      book_court(driver)
  finally:
    driver.quit()

if __name__ == '__main__':
  main()

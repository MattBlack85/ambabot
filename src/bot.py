import asyncio
import logging
import os
import platform
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from telegram import Bot

load_dotenv()


def generate_user_agent():
    while True:
        u = UserAgent().random
        if "Linux; Android 10; K" in u:
            continue
        else:
            break
    return u


URL = "https://prenotami.esteri.it/"
EMAIL = os.environ["EMAIL"]
PASSWORD = os.environ["PASSWORD"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
USER_IDS = [264915836, 788778069]
USER_AGENT = generate_user_agent()
BUSY_MODAL_ID = "jconfirm-box53013"

logger = logging.getLogger("ambabot")
here = Path(__file__)
logfile_path = here.parent.parent / "ambabot.log"
# logging.basicConfig(
#     format="%(asctime)s %(message)s",
#     filename=logfile_path,
#     filemode="a",
#     encoding="utf-8",
#     level=logging.WARN,
# )


def generate_random_wait_times(min_secs: int, max_secs: int) -> float:
    return random.randint(min_secs, max_secs) + random.random()


class Driverfactory:
    def _setup_ff_driver():
        ff_opts = webdriver.FirefoxOptions()
        ff_opts.set_preference("general.useragent.override", USER_AGENT)
        # ff_opts.add_argument("--headless")

        if platform.machine() == "aarch64":
            service = webdriver.FirefoxService(executable_path="/usr/bin/geckodriver")
        else:
            service = None

        driver = webdriver.Firefox(ff_opts, service=service)

        return driver

    def _setup_chrome_driver():
        chrome_opts = webdriver.ChromeOptions()
        # chrome_opts.add_argument("--headless=new")
        chrome_opts.add_argument(f"--user-agent={USER_AGENT}")
        driver = webdriver.Chrome(chrome_opts)

        return driver

    @classmethod
    def pick_driver(cls):
        if platform.machine() == "aarch64":
            return cls._setup_ff_driver()

        match random.randint(0, 1):
            case 0:
                return cls._setup_ff_driver()
            case 1:
                return cls._setup_chrome_driver()


def main(driver, loop, bot: Bot):
    driver.get(URL)
    email = driver.find_element(By.ID, "login-email")
    passwd = driver.find_element(By.ID, "login-password")
    login = driver.find_element(By.CLASS_NAME, "button.primary.g-recaptcha")

    time.sleep(generate_random_wait_times(2, 4))
    email.send_keys(EMAIL)
    time.sleep(generate_random_wait_times(2, 4))
    passwd.send_keys(PASSWORD)
    time.sleep(generate_random_wait_times(2, 4))
    login.send_keys(Keys.ENTER)
    time.sleep(generate_random_wait_times(1, 2))

    book = driver.find_element(By.ID, "advanced")
    book.send_keys(Keys.ENTER)
    time.sleep(generate_random_wait_times(2, 7))

    # Click on PRENOTA and see what happens
    book_passport = driver.find_element(By.XPATH, '//a[@href="/Services/Booking/73"]')
    book_passport.send_keys(Keys.ENTER)

    if driver.name == "firefox":
        time.sleep(generate_random_wait_times(4, 6))
        wait = WebDriverWait(driver, 15)
    else:
        wait = WebDriverWait(driver, 1)

    try:
        wait.until(EC.presence_of_element_located((By.ID, BUSY_MODAL_ID)))
        for user_id in USER_IDS:
            loop.run_until_complete(bot.send_message(user_id, "Passports slots are available! Login and book one"))
        logger.warning("Passports slots are available! Login and book one")
    except TimeoutException:
        logger.warning("The page doesn't load")
    except Exception as e:  # NOQA
        logger.warning(f"No available passports slots - user-agent: {USER_AGENT} - driver: {driver.name}")

    try:
        logout = driver.find_element(By.XPATH, "//form[@id='logoutForm']/button[1]")
        logout.submit()
    except NoSuchElementException:
        pass

    driver.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Setup the telegram bot
    bot = Bot(TELEGRAM_TOKEN)
    loop.run_until_complete(bot.initialize())

    print(f"User agent: {USER_AGENT}")

    driver = Driverfactory.pick_driver()

    try:
        main(driver, loop, bot)
    except Exception as e:
        logger.error(
            f"Something wrong happened, likely the bot is blocked - user-agent: {USER_AGENT} - driver: {driver.name}"
        )
        driver.close()

    loop.close()

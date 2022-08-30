import sys
import requests


def check_internet_connection():
    try:
        url = 'https://www.google.com/'
        timeout = 2
        _ = requests.head(url, timeout = timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        print('\nNo internet connection available!')
        return False


if not check_internet_connection():
    sys.exit()
else:
    import time
    import numpy as np
    import datetime as dt
    from selenium.webdriver import Chrome, ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
    from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException


class AparatViewer:
    def __init__(self, url_list_path = 'url_list.txt',
                 chromedriver_path = 'chromedriver.exe',
                 num_of_views = 5,
                 view_duration = 30,
                 work_in_silence = True,
                 work_in_hidden = True):
        self.url_list = []
        with open(url_list_path, 'r') as _url_list:
            for _url in _url_list:
                self.url_list.append(_url.replace('\n', ''))
        self.url_list = np.asarray(self.url_list)[np.random.permutation(len(self.url_list))]
        self.num_of_views = num_of_views
        self.view_duration = view_duration
        self.work_in_silence = work_in_silence
        self.work_in_hidden = work_in_hidden
        on_off_mode = {True: 'On', False: 'Off'}
        print(f'--| Number of views you asked for each video is: {self.num_of_views}')
        print(f'--| Work in silence is: {on_off_mode[self.work_in_silence]}')
        print(f'--| Work in hidden is: {on_off_mode[self.work_in_hidden]}')
        print(f'--| Refresh is set to {self.view_duration} sec.')
        print(f'--| Number of videos: {len(self.url_list)}')

        self.chromedriver_path = chromedriver_path
        self.driver = None
        self.video_duration = 0

    def prepare_driver(self, _url, n_tries = 1):
        if not n_tries:
            return False
        print('---| Preparing ...')
        self.driver = Chrome(service = Service(self.chromedriver_path), options = ChromeOptions())
        self.driver.set_window_size(480, 480)
        self.driver.get(_url)
        print(f'----| Video link: {_url}')
        if not self.check_loading(self.driver):
            if not check_internet_connection():
                self.driver.close()
                sys.exit()
        self.play_first(self.driver)
        if self.work_in_hidden:
            self.driver.minimize_window()
        if self.work_in_silence:
            self.work_in_silence = self.mute(self.driver, self.work_in_silence)
        self.skip_ads(self.driver, n_tries = 1000)
        self.video_duration = self.find_duration(self.driver)
        if not self.video_duration:
            if not self.check_reachable(self.driver):
                self.driver.refresh()
            time.sleep(2)
            self.prepare_driver(_url, n_tries - 1)
        else:
            print(f'----| Video duration: {str(dt.timedelta(seconds = self.video_duration))}')
        return True

    def start_view(self):
        for state in range(self.num_of_views):
            skip_ads = False
            for i, _url in zip(range(len(self.url_list)), self.url_list):
                prepare_status = self.prepare_driver(_url)
                if not prepare_status:
                    print(f'---| Bot could not open url {_url}')
                    continue
                if not self.check_loading(self.driver):
                    if not check_internet_connection():
                        self.driver.close()
                        sys.exit()
                if not self.check_playing(self.driver):
                    self.driver.refresh()
                    time.sleep(1)
                    if not self.check_reachable(self.driver):
                        continue
                    skip_ads = True
                if skip_ads:
                    self.skip_ads(self.driver)
                time.sleep(self.view_duration-2)
                print(f'-----| State #{state + 1} - Video #{i + 1} (passed).')
        time.sleep(self.view_duration-2)
        self.driver.close()
        print('--| All done!')

    @staticmethod
    def check_playing(d, n_tries = 500):
        while True and n_tries:
            try:
                current_time = d.find_element(By.XPATH, '//div[@class="romeo-current-time"]//span[@role="presentation"]').get_attribute("textContent")
                return current_time
            except NoSuchElementException:
                pass
            n_tries -= 1
        if n_tries == 0:
            return False

    @staticmethod
    def check_reachable(d):
        try:
            WebDriverWait(d, 3).until(EC.presence_of_element_located((By.XPATH, '//*[@class="romeo-loading-spinner"]')))
            return False
        except (NoSuchElementException, TimeoutException):
            return True

    @staticmethod
    def find_duration(d, n_tries = 500):
        while True and n_tries:
            try:
                _time = d.find_element(By.XPATH, '//span[@class="romeo-duration"]').get_attribute("textContent")[3:]
                time_format = '%M:%S'
                if len(_time.split(':')) == 3:
                    time_format = '%H:%M:%S'
                return (dt.datetime.strptime(_time, time_format) - dt.datetime(1900, 1, 1)).seconds
            except NoSuchElementException:
                _time = False
                pass
            n_tries -= 1
        return False

    @staticmethod
    def skip_ads(d, n_tries = 500):
        while True and n_tries:
            try:
                if int(d.find_element(By.XPATH, '//span[@class="romeo-current "]').get_attribute("textContent").split(':')[1]) > 6:
                    WebDriverWait(d, 1).until(EC.element_to_be_clickable((By.CLASS_NAME, 'vast-skip-button'))).click()
                    print('----| Skip ads done.')
                    break
            except (NoSuchElementException, StaleElementReferenceException, TimeoutException):
                pass
            n_tries -= 1

    def play_first(self, d, n_tries = 200, check_play = 0):
        if check_play > 2:
            print('Failed to play video!')
            sys.exit()
        check_time_out = 0
        while True and n_tries:
            try:
                WebDriverWait(d, 3).until(EC.element_to_be_clickable((By.XPATH, '//video[@class="romeo-linearMode paused romeo-player-custom-control"]'))).click()
                break
            except ElementClickInterceptedException:
                pass
            except TimeoutException:
                check_time_out += 1
                pass
            if check_time_out > 5:
                if not self.check_playing(d):
                    d.refresh()
                    self.play_first(d, check_play = check_play + 1)
                    self.skip_ads(d)
                else:
                    break
            n_tries -= 1

    @staticmethod
    def mute(d, _mute_mode = False):
        if _mute_mode:
            try:
                WebDriverWait(d, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, 'romeo-volume-control'))).click()
            except TimeoutException:
                _mute_mode = False
                pass
        return _mute_mode

    def check_loading(self, d, n_tries = 500, check_internet = 0):
        if check_internet > 2:
            print('----| Connection failed!')
            return False
        while True and n_tries:
            try:
                d.find_element(By.XPATH, '//button[@class="romeo-button romeo-play-toggle "]')
                return True
            except NoSuchElementException:
                pass
            n_tries -= 1
        if n_tries == 0:
            if not self.check_reachable(d):
                print('----| Your internet connection is slow!')
                d.refresh()
            else:
                self.check_loading(d, check_internet = check_internet + 1)
        return False


if __name__ == '__main__':
    params = {
        'url_list_path':      './assets/url_list.txt',
        'chromedriver_path':  './assets/chromedriver.exe',
        'num_of_views':        1000,
        'view_duration':       10,
        'work_in_silence':     True,
        'work_in_hidden':      True
    }
    aparat_viewer_bot = AparatViewer(url_list_path = params['url_list_path'],
                                     chromedriver_path = params['chromedriver_path'],
                                     num_of_views = params['num_of_views'],
                                     view_duration = params['view_duration'],
                                     work_in_silence = params['work_in_silence'],
                                     work_in_hidden = params['work_in_hidden'])
    aparat_viewer_bot.start_view()

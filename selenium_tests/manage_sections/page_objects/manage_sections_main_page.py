"""
This file models the Manage Sections Main (Landing) Page
"""

from selenium.webdriver.common.by import By
from selenium_tests.manage_sections.page_objects\
    .manage_sections_base_page_object import ManageSectionsBasePageObject


class Locators(object):

    MANAGE_SECTIONS_TEXT = (By.XPATH, './/h3[contains(., "Manage Sections")]')


class MainPageObject(ManageSectionsBasePageObject):
    page_loaded_locator = Locators.MANAGE_SECTIONS_TEXT

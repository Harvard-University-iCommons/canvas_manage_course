"""
This file models the Manage Sections Main (Landing) Page
"""

from selenium.webdriver.common.by import By
from selenium_tests.manage_sections.page_objects\
    .manage_sections_base_page_object import ManageSectionsBasePageObject


class Locators(object):
    # this is the Section(s): header above the section list; the nav bar
    # 'Manage Sections' header appears on other pages in the manage sections
    # app/page flow, so not using that
    MANAGE_SECTIONS_TEXT = (By.XPATH, './/h3[contains(., "Section(s):")]')


class MainPageObject(ManageSectionsBasePageObject):
    page_loaded_locator = Locators.MANAGE_SECTIONS_TEXT

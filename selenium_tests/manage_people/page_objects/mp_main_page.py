"""
This page models the main (landing) page of the Manage People Tool
"""

from selenium.webdriver.common.by import By
from selenium_tests.manage_people.page_objects.mp_base_page_object \
    import ManagePeopleBasePageObject


class Locators(object):
    ADD_PEOPLE_TO_COURSE_LINK = (By.ID, 'add-people-to-course-id')


class MainPageObject(ManagePeopleBasePageObject):
    page_loaded_locator = Locators.ADD_PEOPLE_TO_COURSE_LINK

"""
This file models the Class Roster Main (Landing) Page
"""
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.class_roster.page_objects.class_roster_base_page_object \
    import ClassRosterBasePageObject


class Locators(object):
    # It's currently syntactically difficult to find an exact match for the
    # breadcrumb which would be more accurate ("Manage Course" link > Class
    # Roster".  There are currently no child pages for class roster, but just
    # note that we need to find a better location for when there are child
    # pages, as this locator will always be present in the breadcrumbs.
    CLASS_ROSTER_BREADCRUMB = (By.XPATH, './/h1[contains(., "Class Roster")]')

    @classmethod
    def FIND_LINK_TEXT(cls, text_value):
        """
        Locates the link based on partial link text, given the text value
        """
        return By.PARTIAL_LINK_TEXT, "{}".format(text_value)


class MainPageObject(ClassRosterBasePageObject):
    page_loaded_locator = Locators.CLASS_ROSTER_BREADCRUMB

    def get_link_url(self, text_value):
        """
        There are links that are displayed in the Roster Tool.  This method
        gets the actual URL based on the 'partial link text' match,
        and returns the URL. Because the URL links off to my.harvard (no
        access), the test checks the URL for parameters that match the
        course, such as course number and term ID.
        """
        try:
            link = self.find_element(*Locators.FIND_LINK_TEXT(text_value))
            # Get the URL of the link element
            link_url = link.get_attribute('href')
        except NoSuchElementException:
            return False
        return link_url

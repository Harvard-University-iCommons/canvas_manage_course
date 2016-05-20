"""
This file models some of the page objects on the Manage People Search Page.
(find_user.html)
"""
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_tests.manage_people.page_objects.mp_base_page_object \
    import ManagePeopleBasePageObject


class Locators(object):
    EMAIL_HUID_TEXTBOX = (By.ID, "emailHUID")
    SEARCH_BUTTON = (By.ID, "user_search_button")
    USER_NOT_FOUND_MSG_DIV = (By.ID, "msg-not-found")


class FindUserPageObject(ManagePeopleBasePageObject):
    """List of services offered on the Search page of Manage People tool"""
    page_loaded_locator = Locators.SEARCH_BUTTON

    def find_user(self, search_term):
        """
        This find_user function simulates the typing the search term (user) in
        the search page, looking for the search button and hitting submit to
        search
        """

        element_txt = self.find_element(*Locators.EMAIL_HUID_TEXTBOX)
        element_txt.clear()
        element_txt.send_keys(search_term)
        element_button = self.find_element(*Locators.SEARCH_BUTTON)
        element_button.submit()

    def user_not_found(self):
        """Returns True if the user not found message is visible on the page"""
        try:
            webelement = self.find_element(
                *Locators.USER_NOT_FOUND_MSG_DIV)
        except NoSuchElementException:
            return False

        return webelement.is_displayed()

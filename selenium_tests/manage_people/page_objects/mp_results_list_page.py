"""This file models the Manage People Results Page (results_list.html)"""

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium_common.webelements import Select
from selenium_tests.manage_people.page_objects.mp_base_page_object \
    import ManagePeopleBasePageObject


class Locators(object):
    ADD_TO_COURSE_BUTTON = (By.ID, "user_create_button")
    ADD_USERS_FORM = (By.ID, "add_users_form")
    CANCEL_BUTTON = (By.LINK_TEXT, "Cancel")
    GO_BACK_TO_MANAGE_PEOPLE_LINK = (By.LINK_TEXT, "Go back to manage people")
    SEARCH_FOR_DIFFERENT_PERSON = (By.LINK_TEXT,
                                   "Search for a different person")
    USER_CONFIRMATION = (By.ID, "enrollment_confirmations")

    @classmethod
    def USER_CHECKBOX(cls, sis_user_id):
        """ locates <select> for the given sis_user_id (univ_id) """
        return By.CSS_SELECTOR, \
               "input[type='checkbox'][id|='record'][value='{}']".format(
                   sis_user_id)

    @classmethod
    def USER_SELECT(cls, sis_user_id):
        """ locates <select> for the given sis_user_id (univ_id) """
        return By.CSS_SELECTOR, "select[data-selenium-user-id='{}']".format(
            sis_user_id)


class ResultsListPageObject(ManagePeopleBasePageObject):
    page_loaded_locator = Locators.ADD_USERS_FORM

    def add_id_to_course(self, user, role):
        """ This function selects the user and role and clicks to add user """

        # todo: how will this work for multiple IDs?
        self.mark_checkbox_for_user(user)
        self.select_role_for_user(user, role)

        # Click the Add to Course button
        add_user_button = self.find_element(*Locators.ADD_TO_COURSE_BUTTON)
        add_user_button.click()

    def cancel_and_return(self):
        """ Find the web element for Search for a different person link """
        cancel_link = self.find_element(*Locators.CANCEL_BUTTON)
        cancel_link.click()

    def mark_checkbox_for_user(self, user_id):
        """
        This function selects the checkbox for the selected user in the search
        results page.
        """

        user_id_checkbox = self.find_element(*Locators.USER_CHECKBOX(user_id))

        # if we have only a single result, the checkbox is hidden and checked
        # automatically; if not, we have to explicitly check it
        if user_id_checkbox.is_displayed():
            user_id_checkbox.click()

    def return_to_manage_people(self):
        """ Find the web element for Go back to Manage People link """
        go_back_link = self.find_element(
            *Locators.GO_BACK_TO_MANAGE_PEOPLE_LINK)
        go_back_link.click()

    def search_for_different_person(self):
        """ Find the web element for Search for a different person link"""
        search_for_different_person_link = self.find_element(
            *Locators.SEARCH_FOR_DIFFERENT_PERSON)
        search_for_different_person_link.click()

    def select_role_for_user(self, user_id, role):
        """ Select role for user, return true if visible, else return false """

        user_role_select = self.find_element(*Locators.USER_SELECT(user_id))
        selenium_select = Select(user_role_select)
        selenium_select.select_by_visible_text(role)

    def user_confirmation_visible(self):
        """ Confirms that the user confirmation box is showing on page """
        try:
            element = self.find_element(*Locators.USER_CONFIRMATION)
        except NoSuchElementException:
            return False
        return element.is_displayed()

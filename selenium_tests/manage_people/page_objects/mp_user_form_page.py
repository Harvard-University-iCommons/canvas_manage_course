"""
This file models the Manage People User List Page (user_form.html)
"""

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium_tests.manage_people.page_objects.mp_base_page_object \
    import ManagePeopleBasePageObject


class Locators(object):
    ADD_PEOPLE_LINK = (By.LINK_TEXT, "Add People to course")
    CONFIRM_REMOVE_BUTTON = (By.ID, "confirm-remove-user-button")
    PEOPLE_ADDED_LIST = (By.ID, "people-added")

    @classmethod
    def DELETE_USER_ICON(cls, sis_user_id, role_id):
        """
        locates delete person icon for the given sis_user_id (univ_id) and
        role
        """
        return By.CSS_SELECTOR, "li[data-sisid='{}'][data-user-role-id='{}'] " \
                                "a.delete-icon".format(sis_user_id, role_id)


    @classmethod
    def USER_LI(cls, sis_user_id, role_id):
        """ locates <li> for the given sis_user_id (univ_id) and role """
        return By.CSS_SELECTOR, "li[data-sisid='{}']" \
                                "[data-user-role-id='{}']".format(
                                                        sis_user_id, role_id)


class UserListPageObject(ManagePeopleBasePageObject):
    page_loaded_locator = Locators.PEOPLE_ADDED_LIST

    def add_user(self):
        """ Go to the search page (follow add people to course link) """
        add_people_link = self.find_element(*Locators.ADD_PEOPLE_LINK)
        add_people_link.click()

    def delete_user(self, univ_id, role_id):
        """
        Actions taken to remove a user from the Remove list
        Step 1: Find given user with given canvas_role on page
        Step 2: Find Delete button for that enrollment and click it
        Step 3: Click on confirmation
        """
        # locate the WebElement for the delete icon for a specific user
        delete_user_element = self.find_element(
            *Locators.DELETE_USER_ICON(univ_id, role_id))
        delete_user_element.click()

        # Clicking on the confirm delete button in the modal window...
        self.find_element(*Locators.CONFIRM_REMOVE_BUTTON).click()

    def user_present_with_role(self, univ_id, role_id):
        """
        Looks for a user row on the page by univ_id (SIS ID) and role name.
        """
        try:
            self.find_element(*Locators.USER_LI(univ_id, role_id))
        except NoSuchElementException:
            return False
        return True

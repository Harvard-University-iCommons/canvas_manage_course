from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from selenium_tests.course_admin.page_objects.course_admin_base_page_object \
    import CourseAdminBasePage


class Locators(object):
    CLASS_ROSTER_BUTTON = (By.ID, "course-roster")
    MANAGE_PEOPLE_BUTTON = (By.ID, "manage-people")
    # if PAGE_TITLE uses contains() it will match for sub-pages as well, so
    # use text() for exact match (should only match on dashboard page)
    PAGE_TITLE = (By.XPATH, './/h3[normalize-space(text())="Manage Course"]')


class CourseAdminDashboardPage(CourseAdminBasePage):
    page_loaded_locator = Locators.PAGE_TITLE

    def manage_people_button_is_displayed(self):
        """
        Verifies that the Manage People button is displayed
        """
        try:
            self.focus_on_tool_frame()
            self.find_element(*Locators.MANAGE_PEOPLE_BUTTON)
        except NoSuchElementException:
            return False
        return True

    def class_roster_button_is_displayed(self):
        """
        Verifies that the Class Roster button is displayed
        """
        try:
            self.focus_on_tool_frame()
            self.find_element(*Locators.CLASS_ROSTER_BUTTON).is_displayed()
        except NoSuchElementException:
            return False
        return True

    def select_manage_people_link(self):
        """
        Finds the manage people button element and clicks it
        """
        self.focus_on_tool_frame()
        self.find_element(*Locators.MANAGE_PEOPLE_BUTTON).click()

    def select_class_roster_link(self):
        """
        Finds the class roster button element and clicks it
        """
        self.focus_on_tool_frame()
        self.find_element(*Locators.CLASS_ROSTER_BUTTON).click()
        # Focus on frame after clicking into Class Roster Tool
        self.focus_on_tool_frame()


from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from selenium_tests.course_admin.page_objects.course_admin_base_page_object \
    import CourseAdminBasePage


class Locators(object):
    CLASS_ROSTER_BUTTON = (By.ID, "course-roster")
    MANAGE_PEOPLE_BUTTON = (By.ID, "manage-people")
    MANAGE_SECTIONS_BUTTON = (By.ID, "manage-sections")
    # if PAGE_TITLE uses contains() it will match for sub-pages as well, so
    # use text() for exact match (should only match on dashboard page)
    PAGE_TITLE = (By.XPATH, './/h3[normalize-space(text())="Manage Course"]')


class CourseAdminDashboardPage(CourseAdminBasePage):
    page_loaded_locator = Locators.PAGE_TITLE

    def class_roster_button_is_displayed(self):
        return self._element_is_displayed(Locators.CLASS_ROSTER_BUTTON)

    def manage_people_button_is_displayed(self):
        return self._element_is_displayed(Locators.MANAGE_PEOPLE_BUTTON)

    def manage_sections_button_is_displayed(self):
        return self._element_is_displayed(Locators.MANAGE_SECTIONS_BUTTON)

    def _element_is_displayed(self, element_locator):
        try:
            self.focus_on_tool_frame()
            self.find_element(*element_locator).is_displayed()
        except NoSuchElementException:
            return False
        return True

    def _click_element(self, element_locator):
        self.focus_on_tool_frame()
        self.find_element(*element_locator).click()

    def select_manage_people_link(self):
        """
        Finds the manage people button element and clicks it
        """
        self._click_element(Locators.MANAGE_PEOPLE_BUTTON)

    def select_class_roster_link(self):
        """
        Finds the class roster button element and clicks it
        """
        self._click_element(Locators.CLASS_ROSTER_BUTTON)
        # todo: remove this?
        # Focus on frame after clicking into Class Roster Tool
        # self.focus_on_tool_frame()

    def select_manage_sections_link(self):
        """
        Finds the manage sections link card and clicks it
        """
        self._click_element(Locators.MANAGE_SECTIONS_BUTTON)
        # Focus on frame after clicking into Manage Sections Tool
        # self.focus_on_tool_frame()


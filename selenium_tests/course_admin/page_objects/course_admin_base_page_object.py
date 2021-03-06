from selenium_common.base_page_object import BasePageObject
from selenium.common.exceptions import NoSuchElementException


class CourseAdminBasePage(BasePageObject):
    """
    This is the base page object class that all course admin pages can inherit
    from. Locators and Services would be common to all pages on  this tool
    """
    def __init__(self, driver):
        super(CourseAdminBasePage, self).__init__(driver)
        try:
            self._driver.switch_to.frame(
                self._driver.find_element_by_id("tool_content"))
        except NoSuchElementException:
            pass

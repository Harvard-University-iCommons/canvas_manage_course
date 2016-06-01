from selenium_common.base_page_object import BasePageObject
from selenium.common.exceptions import NoSuchElementException


class ManagePeopleBasePageObject(BasePageObject):

    def __init__(self, driver):
        super(ManagePeopleBasePageObject, self).__init__(driver)
        self.focus_on_tool_frame()

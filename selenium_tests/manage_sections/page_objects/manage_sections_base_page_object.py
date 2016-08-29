from selenium_common.base_page_object import BasePageObject


class ManageSectionsBasePageObject(BasePageObject):

    def __init__(self, driver):
        super(ManageSectionsBasePageObject, self).__init__(driver)
        self.focus_on_tool_frame()

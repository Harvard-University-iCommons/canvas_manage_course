from django.conf import settings
from os.path import abspath, dirname, join
from urlparse import urljoin

from selenium_common.base_test_case import BaseSeleniumTestCase
from selenium_common.pin.page_objects.pin_login_page_object \
    import PinLoginPageObject

# Common files used for all Manage People test cases
MP_TEST_USERS_WITH_ROLES = join(
    dirname(abspath(__file__)),
    'test_data', 'mp_test_users_with_roles.xlsx')


class ManagePeopleBaseTestCase(BaseSeleniumTestCase):

    @classmethod
    def setUpClass(cls):
        """
        Redirects browser to test course URL and login to PIN using
        specified credentials.
        """
        super(ManagePeopleBaseTestCase, cls).setUpClass()
        cls.username = settings.SELENIUM_CONFIG['selenium_username']
        cls.password = settings.SELENIUM_CONFIG['selenium_password']
        cls.canvas_base_url = settings.SELENIUM_CONFIG['canvas_base_url']
        cls.test_settings = settings.SELENIUM_CONFIG['manage_people']
        cls.tool_relative_url = cls.test_settings['url']
        cls.base_url = urljoin(cls.canvas_base_url, cls.tool_relative_url)

        cls.driver.get(cls.base_url)

        login_page = PinLoginPageObject(cls.driver)
        if login_page.is_loaded():
            print "Logging in XID user {}".format(cls.username)
            login_page.login_xid(cls.username, cls.password)
        else:
            print '(XID user {} already logged in)'.format(cls.username)

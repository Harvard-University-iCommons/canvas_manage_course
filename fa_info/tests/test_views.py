from django.test import RequestFactory, TestCase
from icommons_common.models import Course, CourseInstance, Term
from mock import Mock

class FaInfoTestCase(TestCase):
    def setUp(self):
        self.resource_link_id = uuid.uuid4().hex
        self.user_id = uuid.uuid4().hex
        self.request = Mock(session={}, method='GET',
                            resource_link_id=self.resource_link_id)
        elf.request.user = Mock(is_authenticated=Mock(return_value=True))            
        self.request.LTI = {
            'lis_course_offering_sourcedid': self.course_instance_id,
            'lis_person_sourcedid': self.user_id,
            # 'resource_link_id': self.resource_link_id,
        }

        term = Term.objects.create(cs_strm=1234)
        course = Course.objects.create(registrar_code='56k78')
        CourseInstance.objects.create(course=course, term=term, course_instance_id=1)

    def test_index_redirect(self):
        pass

    def test_index_redirect_fail(self):
        pass

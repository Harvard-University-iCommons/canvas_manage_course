import logging

from canvas_sdk.methods import (accounts, sections, enrollments)
from canvas_sdk.utils import get_all_list_data
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from django.utils.encoding import smart_text
from icommons_common.canvas_utils import SessionInactivityExpirationRC
from icommons_common.models import (Section, SectionMember, CourseInstance)

SDK_CONTEXT = SessionInactivityExpirationRC(**settings.CANVAS_SDK_SETTINGS)

logger = logging.getLogger(__name__)


class Command(NoArgsCommand):
    """
    sync canvas sections and section members to the coursemanager.section 
    and coursemanager.section_member tables
    """
    help = ('sync canvas sections and section members to the coursemanager.section'
            'and coursemanager.section_member tables')
    
    def handle_noargs(self, **options):
        """
        sync canvas sections and section members to the coursemanager.section 
        and coursemanager.section_member tables. Note this process works by
        getting all active courses for the given account_id. The method 
        get_account_list_from_canvas get a list of all the sub-accounts of 
        the ROOT_ACCOUNT.
        """
        account_list = get_account_list_from_canvas()
        for account_id in account_list:
            course_list = get_course_list_from_canvas(account_id)    

            for course in course_list:
                sis_course_id = course.get('sis_course_id')
                canvas_course_id = course.get('id')
                
                if sis_course_id and sis_course_id.isdigit() and canvas_course_id: 
                    
                    try:
                        ci = CourseInstance.objects.get(pk=sis_course_id)
                    except ObjectDoesNotExist:
                        """
                        if the course instance id in canvas does not exists in the coursemanager
                        course_instance table. This is ok as some of the early canvas courses don't have
                        course instance records in the coursemanager db, log the exception and continue
                        """
                        ci = None
                        logger.info('course_instance {} does not exist for canvas_course_id {}'.format(sis_course_id,
                                                                                                   canvas_course_id))
                        continue

                    """
                    get the list of sections associated with the canvas_course_id
                    """
                    canvas_course_sections_set = set(get_canvas_sections_list(canvas_course_id))
                    
                    """
                    get the list of sections associated with the course_instance
                    """
                    cm_section_set = set(get_cm_sections_list(ci))

                    """
                    convert the lists to sets so we can perform set operations:
                             a = set('1','2','3')
                             b = set('2','3','4')
                             c = a - b = ('1') items in a but not in b
                             d = b - a = ('4') items in b but not in a

                    this tells us what sections we need to add and remove
                    """
                    sections_to_remove = cm_section_set - canvas_course_sections_set
                  
                    """
                    If a section was deleted from Canvas we want to also delete the
                    section from the section table. 
                    """
                    remove_sections_from_cm(sections_to_remove, sis_course_id)
                   
                    """
                    Now process the sections that need to be created or updated. 
                    """
                    for canvas_section_id in canvas_course_sections_set:
                        section = get_canvas_section(canvas_section_id)
                        section_name = section.get('name')
                        if section_name:
                            cm_section_id = create_or_update_section(ci, sis_course_id, canvas_section_id,
                                                                     smart_text(section_name))
                        
                            """
                            get the list of sis_user_id's of the section from canvas
                            """       
                            canvas_section_member_set = set(get_enrollments_from_canvas_section(canvas_section_id))
                            
                            """
                            get the list of user_id's from the section_member table 
                            """
                            cm_section_member_set = set(get_enrollments_from_cm_section(cm_section_id))
                            
                            add_user_set = canvas_section_member_set - cm_section_member_set
                            remove_user_set = cm_section_member_set - canvas_section_member_set
     
                            if len(remove_user_set) > 0:
                                remove_user_list_from_section(remove_user_set, cm_section_id)

                            if len(add_user_set) > 0:
                                add_user_list_to_section(add_user_set, cm_section_id)

        logger.info('process complete')


def remove_user_list_from_section(users, section_id):
    """
    remove all users in the users list from the section
    """
    SectionMember.objects.filter(user_id__in=users, section_id=section_id).delete()


def remove_all_users_from_section(section_id):
    """
    remove all users from a section
    """
    users = SectionMember.objects.filter(section_id=section_id).exclude(user_id='')
    remove_user_list_from_section(users, section_id)


def add_user_list_to_section(users, section_id):
    """
    add's a list of users to the section
    """

    members = [SectionMember(section_id=section_id, user_id=user_id, role_id=0, source='Canvas') for user_id in users]
    SectionMember.objects.bulk_create(members)


def create_or_update_section(course_instance, sis_course_id, canvas_section_id, section_name):
    """
    create or update a section in the coursemanager database. The method
    checks to see if a section already exists with the canvas_section_id.
    If one does exist, it will update the section name if needed. If one
    does not exist, it will create a new section.
    """
    try:
        """
        get will throw an ObjectDoesNotExist exception if a record does not
        exist for the current section. In that case we catch it and do an 
        insert vs an update. Since we are manually creating the primary key
        for the section, we can't use the nicer django method update_or_create
        """
        cm_section = Section.objects.get(canvas_section_id=canvas_section_id)
        cm_section_id = cm_section.section_id
        
        """
        update the section name if it is different
        """
        if cm_section.name != section_name:
            cm_section.name = section_name
            cm_section.save()

    except ObjectDoesNotExist:
        """
        the section did not exist in the coursemanager section table so
        we create a new section.
        """        
        cm_section = Section(course_instance=course_instance, name=section_name, canvas_section_id=canvas_section_id)
        new_section_list = [cm_section]
        Section.objects.bulk_create(new_section_list)
        cm_section = Section.objects.get(canvas_section_id=canvas_section_id)
        cm_section_id = cm_section.section_id
        logger.info('created new section \'{}\' in course {} with section_id {}'.format(section_name,
                                                                                        sis_course_id,
                                                                                        cm_section_id))

    return cm_section_id


def remove_sections_from_cm(sections_to_remove, sis_course_id):
    """
    remove sections and section members from the sections and section_member tables
    """
    for canvas_section_id in sections_to_remove:
        try:
            cm_section = Section.objects.get(canvas_section_id=canvas_section_id)
            section_id = cm_section.section_id
            remove_all_users_from_section(section_id)
            logger.info('removing section {} from course {}'.format(section_id, sis_course_id))
            cm_section.delete()
        except ObjectDoesNotExist:
            """
            It's possible that the coursemanager and canvas are not completely in sync. 
            If the canvas_section_id does not exist in the coursemanager.section table, it may have been
            removed by some other means. Log the exception and continue processing sections.
            """
            logger.info('section with canvas_section_id {} does not exist'.format(canvas_section_id))
            continue


def get_enrollments_from_cm_section(section_id):
    """
    get the list of enrollments for the coursemanager section
    """
    section_members = SectionMember.objects.filter(section=section_id).values_list('user_id',
                                                                                   flat=True).exclude(user_id='')
    return section_members


def get_enrollments_from_canvas_section(canvas_section_id):
    """
    get the list of enrollments for the canvas section
    """
    enrollment_list = get_all_list_data(SDK_CONTEXT, enrollments.list_enrollments_sections, canvas_section_id)
    sis_user_id_list = []
    for enrollment in enrollment_list:
        sis_user_id = enrollment['user'].get('sis_user_id')
        if sis_user_id:
            sis_user_id_list.append(sis_user_id)
    return sis_user_id_list


def get_canvas_section(section_id):
    """
    Get a single canvas section from the given section_id
    """
    section = sections.get_section_information_sections(SDK_CONTEXT, section_id).json()
    return section


def get_cm_sections_list(course_instance):
    """
    get the list of sections associated with the coursemanager.sections table
    """
    course_sections = Section.objects.filter(
        course_instance=course_instance).values_list('canvas_section_id',
                                                     flat=True).exclude(canvas_section_id=None)
    return course_sections


def get_canvas_sections_list(canvas_course_id):
    """
    Get a list of the sections exluding the primary section for the given canvas_course_id. 
    We don't want primary sections. Primary sections are ones where the
    there exists an sis_section_id that the same as the sis_course_id. We 
    also don't want sections with no name.  
    """
    canvas_course_sections = get_all_list_data(SDK_CONTEXT, sections.list_course_sections, canvas_course_id)
    canvas_course_sections_list = []
    for canvas_section in canvas_course_sections:
        canvas_section_id = canvas_section.get('id')
        canvas_section_name = canvas_section.get('name')
        sis_course_id = canvas_section.get('sis_course_id')
        sis_section_id = canvas_section.get('sis_section_id')
        if canvas_section_id and (sis_course_id != sis_section_id) and canvas_section_name:
            canvas_course_sections_list.append(canvas_section_id)
    return canvas_course_sections_list


def get_course_list_from_canvas(account_id):
    """
    Get a list of all the active courses for the give account_id.
    """
    course_list = get_all_list_data(SDK_CONTEXT, accounts.list_active_courses_in_account,
                                    account_id, with_enrollments=True)
    return course_list


def get_account_list_from_canvas():
    """
    Get the list of all sub-accounts of the Harvard root account 
    and build a list of the account id's.  
    """
    sub_account_list = get_all_list_data(SDK_CONTEXT, accounts.get_sub_accounts_of_account,
                                         settings.MANAGE_SECTIONS.get('ROOT_ACCOUNT', 1), recursive=True)
    sub_list = []
    for a in sub_account_list:
        sub_account_id = a.get('id')
        if sub_account_id:
            sub_list.append(sub_account_id)
    return sorted(sub_list)

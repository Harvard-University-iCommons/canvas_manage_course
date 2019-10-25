from django.db import models


class ManagePeopleRole(models.Model):
    '''
    Defines the default set of roles available for adding, and whether those
    roles are available for users with only an XID.

    NOTE: This table is needed to look up user_role_id values by canvas
    role_label, so it must always be a superset of all roles referenced
    by SchoolAllowedRole.
    '''
    user_role_id = models.IntegerField(primary_key=True)  # logically an fk on
                                                          # cm.user_role.role_id
    xid_allowed = models.BooleanField(default=False)

    class Meta:
        app_label = 'manage_people'
        db_table = 'manage_people_role'

    def __unicode__(self):
        return 'user role id:{}, xid:{}allowed'.format(
            self.user_role_id, '' if self.xid_allowed else 'not ')


class SchoolAllowedRole(models.Model):
    '''
    If a school so chooses, they can override the set of roles available to
    their liaisons, and/or whether a given role is available to a user with
    only an XID.

    NOTE: A school may remove roles provided in the default set, but they may
    not add roles not present in ManagePeopleRole.
    '''
    school_id = models.CharField(max_length=10)  # logically an fk on
                                                 # cm.school.school_id
    user_role = models.ForeignKey('ManagePeopleRole', on_delete=models.CASCADE)
    xid_allowed = models.BooleanField(default=False)

    class Meta:
        app_label = 'manage_people'
        db_table = 'school_allowed_role'
        unique_together = ('school_id', 'user_role')

    def __unicode__(self):
        return 'school:{}, manage people role id:{}, xid:{}allowed'.format(
            self.school_id,
            self.user_role.user_role_id,
            '' if self.xid_allowed else 'not '
        )

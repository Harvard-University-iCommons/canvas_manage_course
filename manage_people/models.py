from django.db import models


class ManagePeopleRole(models.Model):
    '''
    Defines the default set of roles available for adding, whether those
    roles are available for users with only an XID, and a mapping between
    Canvas role labels and our user_role.user_role_id values.

    NOTE: This table is needed to look up user_role_id values by canvas
    role_label, so it must always be a superset of all roles referenced
    by SchoolAllowedRole.
    '''
    user_role_id = models.IntegerField(primary_key=True)  # logically an fk on
                                                          # cm.user_role.role_id
    canvas_role_label = models.CharField(max_length=30, unique=True)
    xid_allowed = models.BooleanField(default=False)

    class Meta:
        db_table = u'manage_people_role'

    def __unicode__(self):
        return u'user role id {}, canvas role {},  xid {}allowed'.format(
            self.user_role_id, self.canvas_role_label,
            u'' if self.xid_allowed else u'not ')


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
    user_role = models.ForeignKey('ManagePeopleRole')
    xid_allowed = models.BooleanField(default=False)

    class Meta:
        db_table = u'school_allowed_role'
        unique_together = ('school_id', 'user_role')

    def __unicode__(self):
        return u'school {}, role {}, xid {}allowed'.format(
            self.school_id,
            self.canvas_role_id,
            '' if self.xid_allowed else 'not '
        )

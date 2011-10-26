"""
    Authentication backend that sends all of the permissions checks
    to a remote service.
"""
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType

from slumber import client


class ImproperlyConfigured(Exception):
    """Raised if the authentication is not configured as it should be.
    """
    pass


def _assert_properly_configured():
    """Make sure that the authentication backend is properly configured.
    """
    if not hasattr(client, 'auth'):
        raise ImproperlyConfigured("If using the Slumber client's "
            "authentication backend then you must also use the full "
            "service based Slumber confiuration and include a service "
            "called 'auth' which points to the service which will "
            "handle all authentication and authorization.")


class Backend(object):
    """An authentication backend which delegates user permissions to another
    Slumber service.

    Currently this backend does not support object permissions.
    """

    def authenticate(self, x_fost_user=None):
        """Authenticate the user when the middleware passes it in.
        """
        return self.get_user(x_fost_user)


    # Django defines the following as methods
    # pylint: disable=R0201


    def get_user(self, user_id):
        """Return the user associated with the user_id specified.
        """
        _assert_properly_configured()
        try:
            remote_user = client.auth.django.contrib.auth.User.get(
                username=user_id)
        except AssertionError:
            return None
        user, created = User.objects.get_or_create(username=user_id)
        if created:
            for attr in ['is_active', 'is_staff', 'date_joined', 'is_superuser',
                    'first_name', 'last_name', 'email']:
                v = getattr(remote_user, attr)
                setattr(user, attr, v)
            user.save()
        user.remote_user = remote_user
        return user

    def get_group_permissions(self, user_obj, _obj=None):
        """Returns all of the permissions the user has through their groups.
        """
        return user_obj.remote_user.get_group_permissions()

    def get_all_permissions(self, user_obj, _obj=None):
        """Return all of the permission names that this user has.
        """
        return user_obj.remote_user.get_all_permissions()

    def has_module_perms(self, user_obj, package_name):
        """Return True if the user has any permission within the
        module/application
        """
        return user_obj.remote_user.has_module_perms(package_name)

    def has_perm(self, user_obj, perm, _obj=None):
        """Return True if the user has the specified permission.
        """
        try:
            app, code = perm.split('.')
            # Pylint can't work out that objects exists on Permission
            # pylint: disable = E1101
            if Permission.objects.filter(codename=code,
                    content_type__app_label=app).count() == 0:
                content_type, _ = ContentType.objects.get_or_create(
                    app_label=app, model='unknown')
                Permission(codename=code, name=code,
                    content_type=content_type).save()
        except ValueError:
            pass
        return user_obj.remote_user.has_perm(perm)


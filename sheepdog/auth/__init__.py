"""
This module will depend on the downstream authutils dependency.

eg:
``pip install git+https://git@github.com/NCI-GDC/authutils.git@1.2.3#egg=authutils``
or
``pip install git+https://git@github.com/uc-cdis/authutils.git@1.2.3#egg=authutils``
"""

import functools

from cdislogging import get_logger
import flask

import authutils
from authutils import dbgap
from authutils import ROLES
from authutils.user import AuthError, current_user, set_global_user

from sheepdog import models

LOGGER = get_logger('sheepdog_auth')


def _log_import_error(module_name):
    """
    Log which module cannot be imported.

    Just in case this currently short list grows, make it a function.
    """
    LOGGER.info('Unable to import %s, assuming it is not there', module_name)


# planx only modules (for now)

# Separate try blocks in case one gets brought into gdc authutils.
# This is done with try blocks because when sheepdog.api imports
# sheepdog.auth you can't use flask.current_app. It hasn't been
# instantiated yet (application out of context error)

try:
    from authutils import require_auth
except ImportError:
    _log_import_error('require_auth')


def _role_error_msg(user_name, roles, project):
    role_names = [
        role if role != '_member_' else 'read (_member_)' for role in roles
    ]
    return (
        "User {} doesn't have {} access in {}".format(
            user_name, ' or '.join(role_names), project
        )
    )


def authorize_for_project(*required_roles):
    """
    Wrap a function to allow access to the handler iff the user has at least
    one of the roles requested on the given project.
    """

    def wrapper(func):

        @functools.wraps(func)
        def authorize_and_call(program, project, *args, **kwargs):
            user_roles = set()
            with flask.current_app.db.session_scope():
                program_node = (
                    flask.current_app.db
                    .nodes(models.Program)
                    .props(name=program)
                    .scalar()
                )
                if program_node:
                    program_id = program_node.dbgap_accession_number
                    roles = current_user.projects.get(program_id, set())
                    user_roles.update(set(roles))
                project_node = (
                    flask.current_app.db
                    .nodes(models.Project)
                    .props(code=project)
                    .scalar()
                )
                if project_node:
                    project_id = project_node.dbgap_accession_number
                    roles = current_user.projects.get(project_id, set())
                    user_roles.update(set(roles))
                import pdb; pdb.set_trace()
                print()

            if not user_roles & set(required_roles):
                raise AuthError(_role_error_msg(
                    current_user.username, required_roles, project_id
                ))
            return func(program, project, *args, **kwargs)

        return authorize_and_call

    return wrapper

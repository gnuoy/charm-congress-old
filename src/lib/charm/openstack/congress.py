# The Congress handlers class

# bare functions are provided to the reactive handlers to perform the functions
# needed on the class.

import charmhelpers.contrib.openstack.utils as ch_utils

import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip


def install():
    """Use the singleton from the CongressCharm to install the packages on the
    unit
    """
    CongressCharm.singleton.install()


def restart_all():
    """Use the singleton from the CongressCharm to restart services on the
    unit
    """
    CongressCharm.singleton.restart_all()


def db_sync():
    """Use the singleton from the CongressCharm to run db migration
    """
    CongressCharm.singleton.db_sync()


def setup_endpoint(keystone):
    """When the keystone interface connects, register this unit in the keystone
    catalogue.
    """
    charm = CongressCharm.singleton
    keystone.register_endpoints(charm.service_name,
                                charm.region,
                                charm.public_url,
                                charm.internal_url,
                                charm.admin_url)


def render_configs(interfaces_list):
    """Using a list of interfaces, render the configs and, if they have
    changes, restart the services on the unit.
    """
    CongressCharm.singleton.render_with_interfaces(interfaces_list)


class CongressCharm(charms_openstack.charm.OpenStackCharm):

    service_name = 'congress'
    release = 'mitaka'
     
    # Packages the service needs installed
    packages = ['congress-server', 'congress-common', 'python-antlr3',
                'python-pymysql']

    # Init services the charm manages
    services = ['congress-server']

    # Standard interface adapters class to use.
    adapters_class = charms_openstack.adapters.OpenStackRelationAdapters

    # Ports that need exposing.
    default_service = 'congress-api'
    api_ports = {
        'congress-api': {
            os_ip.PUBLIC: 1789,
            os_ip.ADMIN: 1789,
            os_ip.INTERNAL: 1789,
        }
    }

    # Database sync command used to initalise the schema.
    sync_cmd = ['congress-db-manage', '--config-file',
                '/etc/congress/congress.conf', 'upgrade', 'head']

    # The restart map defines which services should be restarted when a given
    # file changes
    restart_map = {
        '/etc/congress/congress.conf': ['congress-server'],
        '/etc/congress/api-paste.ini': ['congress-server'],
        '/etc/congress/policy.json': ['congress-server'],
    }

    def __init__(self, release=None, **kwargs):
        """Custom initialiser for class
        If no release is passed, then the charm determines the release from the
        ch_utils.os_release() function.
        """
        if release is None:
            release = ch_utils.os_release('python-keystonemiddleware')
        super(CongressCharm, self).__init__(release=release, **kwargs)

    def install(self):
        """Customise the installation, configure the source and then call the
        parent install() method to install the packages
        """
        self.configure_source()
        # and do the actual install
        super(CongressCharm, self).install()

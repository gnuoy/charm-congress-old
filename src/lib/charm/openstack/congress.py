# The Congress handlers class

# bare functions are provided to the reactive handlers to perform the functions
# needed on the class.

import charmhelpers.contrib.openstack.utils as ch_utils
import charmhelpers.core.hookenv as hookenv
import charms_openstack.charm
import charms_openstack.adapters
import charms_openstack.ip as os_ip

import subprocess

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

    deploy_from_src_packages = ['python-pip', 'default-jre', 'apg', 'git',
                                'gcc', 'python-dev', 'libxml2', 'libxslt1-dev',
                                'libzip-dev', 'python-virtualenv',
                                'python-setuptools', 'python-pbr',
                                'python-tox', 'libffi-dev', 'openssl',
                                'libssl-dev', 'python-mysqldb']

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
        self.src_branch = hookenv.config('source-branch')
        if self.src_branch:
            self.install_dir = "/home/ubuntu/congress"
            init_script = '/etc/init/congress-server.conf'
            self.restart_map[init_script] = ['congress-server']
        if release is None:
            if self.src_branch:
                release = self.src_branch.split('/')[1]
            else:
                release = ch_utils.os_release('python-keystonemiddleware')
        super(CongressCharm, self).__init__(release=release, **kwargs)

    def install(self):
        """Customise the installation, configure the source and then call the
        parent install() method to install the packages
        """
        self.configure_source()
        # and do the actual install
        
        if self.src_branch:
            self.packages = self.deploy_from_src_packages
        
        super(CongressCharm, self).install()
        if self.src_branch:
            self.src_install()

    def src_install(self):
        subprocess.check_call(['apt-get', 'build-dep', 'python-mysqldb', '-y'])
        subprocess.check_call(['pip', 'install', '--upgrade', 'pip',
                               'virtualenv', 'setuptools' ,'pbr', 'tox'])
        subprocess.check_call(['git', '-C', '/home/ubuntu', 'clone',
                               'https://github.com/openstack/congress.git'])
        subprocess.check_call(['git', '-C', self.install_dir, 'checkout',
                               '{}'.format(self.src_branch)])
        subprocess.check_call(['virtualenv', '--python=python2.7',
                              self.install_dir])
        subprocess.check_call(['bin/pip', 'install' ,'-r', 'requirements.txt'],
                              cwd=self.install_dir)
        subprocess.check_call(['bin/pip', 'install', '.'],
                              cwd=self.install_dir)
        subprocess.check_call(['bin/pip', 'install', 'tox'],
                              cwd=self.install_dir)
        subprocess.check_call(['bin/pip', 'install', 'MySQL-python'],
                              cwd=self.install_dir)
        subprocess.check_call(['bin/tox', '-egenconfig'], cwd=self.install_dir)
        subprocess.check_call(['chown', '-R', 'ubuntu', self.install_dir])

    def db_sync(self):
        if self.src_branch:
            self.sync_cmd[0] = 'bin/congress-db-manage'
            subprocess.check_call(self.sync_cmd, cwd=self.install_dir)
        else:
            super(CongressCharm, self).db_sync()

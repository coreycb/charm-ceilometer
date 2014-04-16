from mock import patch, MagicMock

import ceilometer_utils
# Patch out register_configs for import of hooks
_register_configs = ceilometer_utils.register_configs
ceilometer_utils.register_configs = MagicMock()

import ceilometer_hooks as hooks

# Renable old function
ceilometer_utils.register_configs = _register_configs

from test_utils import CharmTestCase

TO_PATCH = [
    'relation_set',
    'configure_installation_source',
    'openstack_upgrade_available',
    'do_openstack_upgrade',
    'apt_install',
    'apt_update',
    'open_port',
    'config',
    'log',
    'relation_ids',
    'filter_installed_packages',
    'CONFIGS',
    'unit_get',
    'get_ceilometer_context',
    'lsb_release',
    'get_packages'
]


class CeilometerHooksTest(CharmTestCase):

    def setUp(self):
        super(CeilometerHooksTest, self).setUp(hooks, TO_PATCH)
        self.config.side_effect = self.test_config.get
        self.get_packages.return_value = ceilometer_utils.CEILOMETER_PACKAGES
        self.filter_installed_packages.return_value = \
            ceilometer_utils.CEILOMETER_PACKAGES
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'precise'}

    def test_configure_source(self):
        self.test_config.set('openstack-origin', 'cloud:precise-havana')
        hooks.hooks.execute(['hooks/install'])
        self.configure_installation_source.\
            assert_called_with('cloud:precise-havana')

    def test_install_hook_precise(self):
        hooks.hooks.execute(['hooks/install'])
        self.configure_installation_source.\
            assert_called_with('cloud:precise-grizzly')
        self.open_port.assert_called_with(hooks.CEILOMETER_PORT)
        self.apt_update.assert_called_with(fatal=True)
        self.apt_install.assert_called_with(
            ceilometer_utils.CEILOMETER_PACKAGES,
            fatal=True
        )

    def test_install_hook_distro(self):
        self.lsb_release.return_value = {'DISTRIB_CODENAME': 'saucy'}
        hooks.hooks.execute(['hooks/install'])
        self.configure_installation_source.\
            assert_called_with('distro')
        self.open_port.assert_called_with(hooks.CEILOMETER_PORT)
        self.apt_update.assert_called_with(fatal=True)
        self.apt_install.assert_called_with(
            ceilometer_utils.CEILOMETER_PACKAGES,
            fatal=True
        )

    def test_amqp_joined(self):
        hooks.hooks.execute(['hooks/amqp-relation-joined'])
        self.relation_set.assert_called_with(
            username=self.test_config.get('rabbit-user'),
            vhost=self.test_config.get('rabbit-vhost'))

    def test_db_joined(self):
        hooks.hooks.execute(['hooks/shared-db-relation-joined'])
        self.relation_set.assert_called_with(
            ceilometer_database='ceilometer')

    @patch.object(hooks, 'ceilometer_joined')
    def test_any_changed(self, joined):
        hooks.hooks.execute(['hooks/shared-db-relation-changed'])
        self.assertTrue(self.CONFIGS.write_all.called)
        self.assertTrue(joined.called)

    @patch.object(hooks, 'install')
    @patch.object(hooks, 'any_changed')
    def test_upgrade_charm(self, changed, install):
        hooks.hooks.execute(['hooks/upgrade-charm'])
        self.assertTrue(changed.called)
        self.assertTrue(install.called)

    @patch.object(hooks, 'ceilometer_joined')
    def test_config_changed_no_upgrade(self, joined):
        self.openstack_upgrade_available.return_value = False
        hooks.hooks.execute(['hooks/config-changed'])
        self.openstack_upgrade_available.\
            assert_called_with('ceilometer-common')
        self.assertFalse(self.do_openstack_upgrade.called)
        self.assertTrue(self.CONFIGS.write_all.called)
        self.assertTrue(joined.called)

    @patch.object(hooks, 'ceilometer_joined')
    def test_config_changed_upgrade(self, joined):
        self.openstack_upgrade_available.return_value = True
        hooks.hooks.execute(['hooks/config-changed'])
        self.openstack_upgrade_available.\
            assert_called_with('ceilometer-common')
        self.assertTrue(self.do_openstack_upgrade.called)
        self.assertTrue(self.CONFIGS.write_all.called)
        self.assertTrue(joined.called)

    def test_keystone_joined(self):
        self.unit_get.return_value = 'thishost'
        self.test_config.set('region', 'myregion')
        hooks.hooks.execute(['hooks/identity-service-relation-joined'])
        url = "http://{}:{}".format('thishost', hooks.CEILOMETER_PORT)
        self.relation_set.assert_called_with(
            service=hooks.CEILOMETER_SERVICE,
            public_url=url, admin_url=url, internal_url=url,
            requested_roles=hooks.CEILOMETER_ROLE,
            region='myregion')

    def test_ceilometer_joined(self):
        self.relation_ids.return_value = ['ceilometer:0']
        self.get_ceilometer_context.return_value = {'test': 'data'}
        hooks.hooks.execute(['hooks/ceilometer-service-relation-joined'])
        self.relation_set.assert_called_with('ceilometer:0',
                                             {'test': 'data'})

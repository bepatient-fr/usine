# -*- coding: UTF-8 -*-
# Copyright (C) 2009-2010 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from os.path import expanduser

# Import from pygobject
from glib import GError

# Import from itools
from itools.core import freeze, lazy
from itools.fs import lfs, vfs

# Import from usine
from config import config
from hosts import local, get_remote_host
from modules import module, register_module



cmd_vhosts = """
from itools.database import Catalog, get_register_fields
catalog = Catalog('./%s/catalog', get_register_fields(), read_only=True)
vhosts = list(catalog.get_unique_values('vhosts'))
vhosts.sort()
for vhost in vhosts:
    print vhost
"""


class instance(module):

    @lazy
    def location(self):
        location = self.options['location']
        if location[:10] == 'localhost:':
            # Case 1: local
            user, server, path = None, 'localhost', location[10:]
        else:
            # Case 2: remote
            user, location = location.split('@', 1)
            server, path = location.split(':', 1)
        if path[0] != '/':
            path = '~/%s' % path
        return user, server, path


    @lazy
    def bin_python(self):
        return '%s/bin/python' % self.location[2]


    def get_host(self):
        user, server, path = self.location
        if server == 'localhost':
            return local

        if config.options.offline:
            print 'Error: this action is not available in offline mode'
            exit(1)

        server = config.get_section('server', server)
        host = server.options['host']
        shell = bool(int(self.options.get('shell', '0')))
        return get_remote_host(host, user, shell)


    def get_source(self, name):
        source = config.get_section('pysrc', name)
        if source:
            return source

        raise ValueError, 'the source "%s" is not found' % name



class pyenv(instance):

    class_title = u'Manage Python environments'


    def get_actions(self):
        if self.location[1] == 'localhost':
            return ['build', 'install', 'restart', 'deploy', 'deploy_reindex',
                    'reindex']
        return ['build', 'upload', 'install', 'restart', 'deploy',
                'deploy_reindex', 'test', 'vhosts', 'reindex']


    def get_action(self, name):
        if self.location[1] == 'localhost':
            if name == 'install':
                return self.action_install_local
            elif name == 'upload':
                return None
        return super(pyenv, self).get_action(name)


    def get_packages(self):
        packages = self.options['packages'].split()
        return [ x.split(':') for x in packages ]


    build_title = u'Build the source code this Python environment requires'
    def action_build(self):
        """Make a source distribution for every required Python package.
        """
        path = expanduser('~/.usine/cache')
        if not lfs.exists(path):
            lfs.make_folder(path)

        print '**********************************************************'
        print ' BUILD'
        print '**********************************************************'
        for name, version in self.get_packages():
            config.options.version = version
            source = self.get_source(name)
            source.action_dist()


    upload_title = u'Upload the source code to the remote server'
    def action_upload(self):
        """Upload every required package to the remote host.
        """
        host = self.get_host()
        print '**********************************************************'
        print ' UPLOAD'
        print '**********************************************************'
        for name, version in self.get_packages():
            source = self.get_source(name)
            # Upload
            pkgname = source.get_pkgname()
            l_path = '%s/dist/%s.tar.gz' % (source.get_path(), pkgname)
            host.put(l_path, '/tmp')


    install_title = u'Install the source code into the Python environment'
    def action_install(self):
        """Installs every required package into the remote virtual
        environment.
        """
        host = self.get_host()
        print '**********************************************************'
        print ' INSTALL'
        print '**********************************************************'
        command = '%s setup.py --quiet install --force' % self.bin_python
        prefix = self.options.get('prefix')
        if prefix:
            command += ' --prefix=%s' % prefix
        for name, version in self.get_packages():
            source = self.get_source(name)
            pkgname = source.get_pkgname()
            # Untar
            host.run('tar xzf %s.tar.gz' % pkgname, '/tmp')
            pkg_path = '/tmp/%s' % pkgname
            # Install
            host.run(command, pkg_path)
            # Clean
            host.run('rm -rf %s' % pkg_path, '/tmp')


    def action_install_local(self):
        print '**********************************************************'
        print ' INSTALL'
        print '**********************************************************'
        bin_python = expanduser(self.bin_python)
        command = [bin_python, 'setup.py', 'install', '--force']
        for name, version in self.get_packages():
            source = self.get_source(name)
            cwd = source.get_path()
            local.run(command, cwd=cwd)


    restart_title = u'Restart the ikaaro instances that use this environment'
    def action_restart(self):
        """Restarts every ikaaro instance.
        """
        print '**********************************************************'
        print ' RESTART'
        print '**********************************************************'
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.stop()
                ikaaro.start()


    reindex_title = u'Reindex the ikaaro instances that use this environment'
    def action_reindex(self):
        """Reindex every ikaaro instance.
        """
        print '**********************************************************'
        print ' REINDEX'
        print '**********************************************************'
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.stop()
                ikaaro.update_catalog()
                ikaaro.start()


    deploy_title = u'All of the above'
    def action_deploy(self):
        """Deploy (build, upload, install, restart) the required Python
        packages in the remote virtual environment, and restart all the ikaaro
        instances.
        """
        actions = ['build', 'upload', 'install', 'restart']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


    deploy_reindex_title = (
        u'Build, upload, install, reindex and start the ikaaro instances')
    def action_deploy_reindex(self):
        """
        Build, upload, install the required Python packages
        in the remote virtual environment and stop, reindex and start all the
        ikaaro instances.
        """
        actions = ['build', 'upload', 'install', 'stop', 'reindex', 'start']
        for name in actions:
            action = self.get_action(name)
            if action:
                action()


    test_title = (
        u'Test if ikaaro instances of this Python environment are alive')
    def action_test(self):
        """ Test if ikaaro instances of this Python environment are alive"""
        print '**********************************************************'
        print ' TEST'
        print '**********************************************************'
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                uri = ikaaro.options['uri']
                try:
                    vfs.open('%s/;_ctrl' % uri)
                except GError:
                    print '[ERROR] ', uri
                else:
                    print '[OK]', uri


    vhosts_title = (
        u'List vhosts of all ikaaro instances of this Python environment')
    def action_vhosts(self):
        """List vhosts of all ikaaro instances of this Python environment"""
        print '**********************************************************'
        print ' LIST VHOSTS'
        print '**********************************************************'
        for ikaaro in config.get_sections_by_type('ikaaro'):
            if ikaaro.options['pyenv'] == self.name:
                ikaaro.vhosts()



class ikaaro(instance):

    class_title = u'Manage Ikaaro instances'
    class_actions = freeze(['start', 'stop', 'restart', 'reindex', 'vhosts'])


    @lazy
    def pyenv(self):
        pyenv = self.options['pyenv']
        return config.get_section('pyenv', pyenv)


    @lazy
    def bin_icms(self):
        pyenv = self.pyenv
        prefix = pyenv.options.get('prefix') or pyenv.location[2]
        return '%s/bin' % prefix


    def get_host(self):
        pyenv = self.pyenv
        host = pyenv.get_host()
        cwd = pyenv.location[2]
        host.chdir(cwd)
        return host


    def stop(self):
        path = self.options['path']
        host = self.get_host()
        host.run('%s/icms-stop.py %s' % (self.bin_icms, path))
        host.run('%s/icms-stop.py --force %s' % (self.bin_icms, path))


    def start(self, readonly=False):
        path = self.options['path']
        cmd = '%s/icms-start.py -d %s' % (self.bin_icms, path)
        readonly = readonly or self.options.get('readonly', False)
        if readonly:
            cmd = cmd + ' -r'
        host = self.get_host()
        host.run(cmd)


    def update_catalog(self):
        path = self.options['path']
        cmd = '{0}/icms-update-catalog.py -y {1} --quiet'.format(self.bin_icms, path)
        host = self.get_host()
        host.run(cmd)


    def vhosts(self):
        path = self.options['path']
        host = self.get_host()
        cmd = cmd_vhosts % path
        host.run('./bin/python -c "%s"' % cmd, quiet=True)


    start_title = u'Start an ikaaro instance'
    def action_start(self):
        print '**********************************************************'
        print ' START'
        print '**********************************************************'
        self.start()


    stop_title = u'Stop an ikaaro instance'
    def action_stop(self):
        print '**********************************************************'
        print ' STOP'
        print '**********************************************************'
        self.stop()


    restart_title = u'(Re)Start an ikaaro instance'
    def action_restart(self):
        print '**********************************************************'
        print ' RESTART'
        print '**********************************************************'
        self.stop()
        self.start()


    reindex_title = u'Update catalog of an ikaaro instance'
    def action_reindex(self):
        print '**********************************************************'
        print ' REINDEX'
        print '**********************************************************'
        self.stop()
        self.update_catalog()
        self.start()


    vhosts_title = u'List vhosts of ikaaro instance'
    def action_vhosts(self):
        print '**********************************************************'
        print ' List Vhosts'
        print '**********************************************************'
        self.vhosts()



# Register
register_module('ikaaro', ikaaro)
register_module('pyenv', pyenv)

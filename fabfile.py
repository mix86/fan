from fabric.api import run, hosts, settings
from fabric.contrib.project import rsync_project

host_list = [
    'obmen01f6.dev.tools.yandex.net',
    # 'obmen02f6.dev.tools.yandex.net',
    # 'obmen03f6.dev.tools.yandex.net'
]

project_path = '/Users/mixael/dev/yandex/fan'
remote_path = '~/dev/fan'

def _rsync():
    rsync_project(remote_dir=remote_path + '/../',
                  local_dir=project_path,
                  delete=False,
                  exclude=['.*', '*.pyc'],
                  extra_opts='--delete-excluded --force')


@hosts(host_list)
def deploy():
    _rsync()

@hosts(host_list)
def restart():
    with settings(warn_only=True):
        run('pkill twistd && sleep 1')
    run('twistd -y dev/fan/src/fan/main.py')

@hosts(host_list)
def install(package):
    run('sudo apt-get update')
    run('sudo apt-get install %s' % package)


# pkill twistd && sleep 1 && twistd -y dev/fan/src/fan/main.py

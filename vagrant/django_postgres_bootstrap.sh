#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/canvas_admin_tools -r /home/vagrant/canvas_admin_tools/canvas_admin_tools/requirements/local.txt canvas_admin_tools
workon canvas_admin_tools
python manage.py init_db --force
python manage.py migrate

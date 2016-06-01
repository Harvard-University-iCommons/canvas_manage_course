#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/canvas_manage_course -r /home/vagrant/canvas_manage_course/canvas_manage_course/requirements/local.txt canvas_manage_course

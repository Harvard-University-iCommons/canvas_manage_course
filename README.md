# Canvas Manage Course
![Static Badge](https://img.shields.io/badge/Python-v3.10-lavender?logo=python)
![GitHub tag (with filter)](https://img.shields.io/github/v/tag/Harvard-University-iCommons/canvas_manage_course?label=Latest%20tag)

This project provides a collection of utilies used to administer Harvard Academic Technology's instance of Canvas at the course level. The project is an LTI tool, i.e. installed via LTI.

## Deploying

Uses the [standard Django ECS Fargate deployment process](https://wiki.harvard.edu/confluence/display/k459/Standard+Django+ECS+Deployment+Process).

## Running locally

### Install requirements

```sh
pip install -r canvas_manage_course/requirements/local.txt
```

Particular difficulties are sometimes found when installing the following directly on Mac OS X in a python environment:

* [psycopg2](https://wiki.harvard.edu/confluence/display/k459/Installing+psycopg2%3E%3D2.8+on+macos) (at install time)
* [cx_Oracle](https://wiki.harvard.edu/confluence/display/k459/Using+cx_Oracle+on+mac+OS+X) (at run time, if oracle instant client is not available or configured properly)

### Run

Run, and ensure the ENV environment var will be able to point the django-ssm-parameter-store library to appropriate SSM params (either locally, via a file, or on SSM, in which case ensure your local default AWS profile is authenticated to the correct environment and that you're on VPN so you can connect to non-local databases and caches).

Note that the runserver_plus default server and port is 127.0.0.1:8000. If your LTI configuration was set up with a different port, e.g. 8443, you'll need to specify it as in the snippet below.

```sh
export ENV=dev
export DJANGO_SETTINGS_MODULE=canvas_manage_course.settings.local
# ensure you're connected to VPN
python manage.py runserver_plus --cert-file cert.crt
# to use a different port:
python manage.py runserver_plus 127.0.0.1:8443 --cert-file cert.crt
```

Access at https://local.tlt.harvard.edu:(port)/.

### Authorize

This tool uses the django-canvas-lti-school-permissions library, which authorizes LTI launches against a database of permissions. The permissions are based on the subaccount that a course belongs to. So when launching from a test course in the AcTS (Academic Technology) subaccount in Canvas, an authorization row should be present for school `acts` or `*` and the main tool, `canvas_manage_course`, along with any specific utilities present in the dashboard, e.g. The tool uses the database name `canvas_course_admin_tools` and the appropriate permissions table is `lti_school_permissions_schoolpermission`.

For example:

| id | permission | canvas\_role | school\_id |
| :--- | :--- | :--- | :--- |
| 1 | canvas\_manage\_course | Account Admin | acts |
| 22 | class\_roster | Account Admin | acts |
| 64 | manage\_people | Account Admin | acts |
| 1050 | manage\_school\_permissions | Account Admin | acts |
| 85 | manage\_sections | Account Admin | acts |

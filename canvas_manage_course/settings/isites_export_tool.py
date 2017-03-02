from .aws import *

INSTALLED_APPS = (
    'async',
    'icommons_common',
    'isites_migration',
    'lti_school_permissions',
    'manage_people',
    'manage_sections',
)

# Settings specifically for the isite_migration LTI app
AWS_EXPORT_BUCKET_ISITES_FILES = SECURE_SETTINGS.get(
    'aws_export_bucket_isites_files',
    'isites-exports-prod')
AWS_EXPORT_BUCKET_SLIDE_TOOL = 'isites-slide-data'
AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS = 60
AWS_SOURCE_BUCKET_ISITES_FILES = SECURE_SETTINGS.get(
    'aws_source_bucket_isites_files',
    'uw-isites-fsdocs-archive')

# local directory where export files are temporarily stored
EXPORT_DIR = os.path.join(BASE_DIR, 'isites_export_tool')
EXPORT_FILES_EXCLUDED_TOOL_IDS = []
EXPORT_FILES_EXCLUDED_TOPIC_TITLES = []

from .aws import *

INSTALLED_APPS = (
    'async',
    'django_rq',
    'icommons_common',
    'isites_migration',
    'lti_school_permissions',
    'manage_people',
    'manage_sections',
)

# Settings specifically for the isite_migration LTI app
AWS_EXPORT_BUCKET_ISITES_FILES = 'isites-slide-data'
AWS_EXPORT_BUCKET_SLIDE_TOOL = 'isites-slide-data'
AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS = 60
AWS_SOURCE_BUCKET_ISITES_FILES = SECURE_SETTINGS.get('aws_source_bucket_isites_files', 'uw-isites-fsdocs-archive')

# local directory where export files are stored
EXPORT_DIR = os.path.join(BASE_DIR, 'export')
EXPORT_FILES_README_FILENAME = '_ReadMe_About_Your_iSites_Archive.html'
EXPORT_FILES_EXCLUDED_TOOL_IDS = SECURE_SETTINGS.get(
    'export_files_excluded_tool_ids', [])
EXPORT_FILES_EXCLUDED_TOPIC_TITLES = [
    'Syllabus Template (Hidden)',
    'About Course iSites, About the Library Resources Page'
]

SLIDE_TOOL_ID = 10864  # PROD tool ID

from .aws import *

INSTALLED_APPS = (
    'icommons_common',
    'async',
    'django_rq',
    'isites_migration',
)

# Settings specifically for the isite_migration LTI app
AWS_EXPORT_BUCKET_ISITES_FILES = 'isites-slide-data'
AWS_EXPORT_BUCKET_SLIDE_TOOL = 'isites-slide-data'
AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS = 60
AWS_PROFILE = 'isites_migration'

EXPORT_DIR = os.path.join(BASE_DIR, 'export')  # local directory where export files are stored
EXPORT_FILES_README_FILENAME = '_ReadMe_About_Your_iSites_Archive.html'
EXPORT_ARCHIVE_FILENAME_PREFIX = 'unpublished_isites_archive_'
EXPORT_FILES_EXCLUDED_TOOL_IDS = SECURE_SETTINGS.get('export_files_excluded_tool_ids', [])
EXPORT_FILES_EXCLUDED_TOPIC_TITLES = [
    'Syllabus Template (Hidden)',
    'About Course iSites, About the Library Resources Page'
]

SLIDE_TOOL_ID = 10864  # PROD tool ID

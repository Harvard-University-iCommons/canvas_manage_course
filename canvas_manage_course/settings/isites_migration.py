"""
These settings are used for:
- isites_migration.management.commands.export_slide_tool (just exporting slide
    tool data; uses e.g.
- jobs put on the RQ isites_export queue (which run
    isites_migration.jobs.migrate_files)
"""
from .aws import *

INSTALLED_APPS = (
    'async',
    'django_rq',
    'icommons_common',
    'isites_migration',
)

# Settings specifically for the isites_migration LTI app
AWS_EXPORT_BUCKET_ISITES_FILES = SECURE_SETTINGS.get(
    'aws_export_bucket_isites_files',
    'isites-exports-prod')
AWS_EXPORT_BUCKET_SLIDE_TOOL = 'isites-slide-data'
AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS = 60

AWS_SOURCE_BUCKET_ISITES_FILES = SECURE_SETTINGS.get(
    'aws_source_bucket_isites_files',
    'uw-isites-fsdocs-archive')

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

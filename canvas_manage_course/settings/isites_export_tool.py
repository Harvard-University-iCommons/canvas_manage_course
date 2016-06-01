from .aws import *

INSTALLED_APPS = (
    'icommons_common',
    'isites_migration',
)

# Settings specifically for the isite_migration LTI app
AWS_EXPORT_BUCKET_ISITES_FILES = 'isites-exports-prod'
AWS_EXPORT_BUCKET_SLIDE_TOOL = 'isites-slide-data'
AWS_EXPORT_DOWNLOAD_TIMEOUT_SECONDS = 60
AWS_PROFILE = 'isites_export_tool'
# local directory where export files are temporarily stored
EXPORT_DIR = os.path.join(BASE_DIR, 'isites_export_tool')
EXPORT_FILES_EXCLUDED_TOOL_IDS = []
EXPORT_FILES_EXCLUDED_TOPIC_TITLES = []

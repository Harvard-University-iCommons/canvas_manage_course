"""
These settings are used for:
- icommons_tools.isites_export_tool (which invokes
    isites_migration.management.commands.export_files to push all files
    for a keyword to AWS_EXPORT_BUCKET_ISITES_FILES)
"""
from .isites_migration import *

EXPORT_FILES_EXCLUDED_TOOL_IDS = []
EXPORT_FILES_EXCLUDED_TOPIC_TITLES = []

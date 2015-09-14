import logging

from async.models import Process

from isites_migration.utils import export_files, import_files


logger = logging.getLogger(__name__)


def migrate_files(keyword, canvas_course_id, process_id=None):
    logger.info("Starting migrate_files job for keyword %s and canvas_course_id %s", keyword, canvas_course_id)

    process = Process.objects.get(id=process_id)
    process.state = Process.ACTIVE
    process.save()

    try:
        export_files(keyword)
        process.status = import_files(keyword, canvas_course_id)
        if process.status == 'failed':
            process.details['error'] = 'Canvas content migration failed'
    except RuntimeError as e:
        process.status = 'failed'
        process.details['error'] = str(e)

    process.state = Process.COMPLETE
    process.save()

    logger.info(
        "Finished migrate_files job for keyword %s and canvas_course_id %s with details %s",
        keyword, canvas_course_id, process.details
    )
    return {
        'state': process.state,
        'status': process.status,
        'details': process.details
    }

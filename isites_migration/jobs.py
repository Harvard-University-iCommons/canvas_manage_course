import logging

from django.utils import timezone
from rq import get_current_job

from async.models import Process
from isites_migration.utils import export_files, import_files


logger = logging.getLogger(__name__)


def migrate_files(process_id, keyword, canvas_course_id, term, title):
    logger.info(
        "Starting migrate_files job for keyword %s, canvas_course_id %s, term %s, and title %s",
        keyword, canvas_course_id, term, title
    )

    job = None

    try:
        job = get_current_job()
        job.meta['process_id'] = process_id
        job.save()
        logger.debug("RQ job details: {}".format(job.to_dict()))
    except Exception as e:
        logger.exception(
            "Failed to get current job information from RQ for process_id: {}. "
            "(Possibly running migrate_files() outside of an RQ "
            "worker?)".format(process_id))

    try:
        process = Process.objects.get(id=process_id)
    except Process.DoesNotExist:
        logger.exception("Failed to find Process with id %d", process_id)
        raise

    process.state = Process.ACTIVE
    process.details['rq_job_id'] = getattr(job, 'id', 'None')
    process.date_active = timezone.now()
    process.save(update_fields=['state', 'details', 'date_active'])

    try:
        export_files(keyword)
        process.status = import_files(keyword, canvas_course_id)
        if process.status == 'failed':
            process.details['error'] = 'Canvas content migration failed'
    except Exception as e:
        logger.exception("Failed to complete content migration for keyword %s",
                         keyword)
        process.status = 'failed'
        process.details['error'] = str(e)

    process.state = Process.COMPLETE
    process.date_complete = timezone.now()
    process.save(update_fields=['state', 'status', 'date_complete'])

    logger.info(
        "Finished migrate_files job for keyword %s and canvas_course_id %s with details %s",
        keyword, canvas_course_id, process.details
    )
    return {
        'state': process.state,
        'status': process.status,
        'details': process.details
    }

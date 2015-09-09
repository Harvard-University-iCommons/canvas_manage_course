import logging

from async.models import Process


logger = logging.getLogger(__name__)


def migrate_files(keyword, canvas_course_id, process=None):
    logger.info("Starting migrate_files process for keyword %s and canvas_course_id %s", keyword, canvas_course_id)
    process.details = {'keyword': keyword, 'canvas_course_id': canvas_course_id}
    process.state = Process.ACTIVE
    process.save()
    logger.info("Finished migrate_files process for keyword %s and canvas_course_id %s", keyword, canvas_course_id)

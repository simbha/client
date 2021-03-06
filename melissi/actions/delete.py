# Contains
# DeleteObject
# DeleteDir
# DeleteFile
# DeleteObjectId
# DeleteObjectIdDroplet
# DeleteObjectIdCell

# standard modules
import shutil
import os
import logging
log = logging.getLogger("melissilogger")

# melissi modules
from melissi.actions import *

class DeleteObject(WorkerAction):
    """
    To avoid racing conditions, where you delete a file and instantly
    move / create another file into position, when the file / dir
    still exists we issue a ModifyFile / ModifyDir and do nothing
    more.

    For example when firefox downloads a file follows the following
    file creation pattern which is causing a racing condition.

    For example let say that we download 'test.pdf'.

    1. Firefox creates both test.pdf and test.pdf.part' in the
    directory the file is to be saved

    2. When download finishes, firefox deletes 'test.pdf' and moves
    'test.pdf.part' to the new filename 'test.pdf'

    3. Because of the deletion, notifier queues a DeleteFile action,
    which probably doesn't get executed before the 'test.pdf.part' is
    already named 'test.pdf'. As a result we delete the new 'test.pdf'
    file and no 'test.pdf' or 'test.pdf.part' exists thereafter in the
    folder
    """

    def __init__(self, hub, filename, watchpath):
        super(DeleteObject, self).__init__(hub)

        self.filename = filename
        self.watchpath = watchpath
        self._record = False

    @property
    def unique_id(self):
        if self._record:
            return self._record.id
        else:
            return self.filename

    def exists(self):
        # return record if item exists in the database
        # else return False
        return self._fetch_file_record(File__filename=self.filename,
                                       WatchPath__path=self.watchpath
                                       )

    def _execute(self):
        self._record = self.exists()
        if not self._record:
            # file not watched, ignoring
            # TODO maybe should look into the queue for pending actions
            # regarding this file
            log.debug("No record for [%s]" % self.unique_id)
            return

        if os.path.exists(pathjoin(self.watchpath, self.filename)):
            if self._record.directory:
                self._hub.queue.put(ModifyDir(self._hub,
                                              self.filename,
                                              self.watchpath)
                                    )
            else:
                self._hub.queue.put(ModifyFile(self._hub,
                                               self.filename,
                                               self.watchpath)
                                    )
        else:
            # delete from database
            self._delete_from_db()

            # notify server
            return self._post_to_server()

    def _failure(self, result):
        log.error("Failure in delete %s" % result)

        raise RetryLater

class DeleteDir(DeleteObject):
    def __init__(self, hub, filename, watchpath):
        super(DeleteDir, self).__init__(hub, filename, watchpath)

    def _delete_from_db(self):
        # delete all children
        for entry in self._dms.find(db.File,
                                    db.File.filename.like(u'%s/%%' % self.filename),
                                    db.File.directory == True,
                                    db.WatchPath.path == self.watchpath,
                                    db.WatchPath.id == db.File.watchpath_id
                                    ):
            self._dms.remove(entry)

        # delete self
        self._dms.remove(self._record)

    def _delete_from_fs(self):
        # required when deleting recursivelly folders
        fullpath = pathjoin(self.watchpath, self._record.filename)
        try:
            shutil.rmtree(fullpath)
        except OSError, error_message:
            # ah, ignore
            pass

    def _post_to_server(self):
        uri = '%s/api/cell/%s/' % (self._hub.config_manager.get_server(),
                               self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d

class DeleteFile(DeleteObject):
    def __init__(self, hub, filename, watchpath):
        super(DeleteFile, self).__init__(hub, filename, watchpath)

    def _delete_from_db(self):
        # delete self
        self._dms.remove(self._record)

    def _delete_from_fs(self):
        # required when deleting recursivelly folders
        fullpath = pathjoin(self.watchpath, self._record.filename)
        try:
            os.unlink(fullpath)
        except OSError, error_message:
            # ah, ignore
            pass

    def _post_to_server(self):
        uri = '%s/api/droplet/%s/' % (self._hub.config_manager.get_server(),
                                  self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d


class DeleteObjectId(WorkerAction):
    def __init__(self, hub, objectid):
        super(DeleteObjectId, self).__init__(hub)

        self._objectid = objectid
        self._record = False

    @property
    def unique_id(self):
        return self._objectid

    def _execute(self):
        self._record = self.exists()
        if not self._record:
            log.debug("No record with id [%s]" % self.unique_id)
            return

        self._delete_from_db()
        self._post_to_server()

    def _failure(self, result):
        log.error("Failure in delete objectid %s" % result)

        raise RetryLater

class DeleteObjectIdCell(DeleteObjectId):
    def _delete_from_db(self):
        # delete all children
        for entry in self._dms.find(db.File,
                                    db.File.filename.like(u'%s/%%' % self._record.filename),
                                    db.WatchPath.id == self._record.watchpath_id,
                                    db.WatchPath.id == db.File.watchpath_id
                                    ):
            self._dms.remove(entry)

        # delete self
        self._dms.remove(self._record)


    def exists(self):
        return self._fetch_file_record(File__id=self._objectid,
                                       File__directory=True
                                       )

    def _post_to_server(self):
        uri = '%s/api/cell/%s/' % (self._hub.config_manager.get_server(),
                               self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d


class DeleteObjectIdDroplet(DeleteObjectId):
    def _delete_from_db(self):
        # delete self
        self._dms.remove(self._record)

    def exists(self):
        return self._fetch_file_record(File__id=self._objectid,
                                       File__directory=False
                                       )

    def _post_to_server(self):
        uri = '%s/api/droplet/%s/' % (self._hub.config_manager.get_server(),
                                  self._record.id)
        d = self._hub.rest_client.delete(str(uri))
        d.addErrback(self._failure)

        return d

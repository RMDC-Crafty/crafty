import bleach
import asyncio
import logging
import tornado.web
import tornado.iostream
from app.classes.handlers.base_handler import BaseHandler
from app.classes.backupmgr import backupmgr
from app.classes.models import *

logger = logging.getLogger(__name__)

class DownloadHandler(BaseHandler):

    @tornado.web.authenticated
    async def get(self):

        name = tornado.escape.json_decode(self.current_user)
        user_data = get_perms_for_user(name)

        if not check_role_permission(user_data['username'], 'backups'):
            self.redirect('/admin/unauthorized')

        chunk_size = 1024 * 1024 * 5 # 5 MiB
        path = bleach.clean(self.get_argument("file", None, True))
        server_id = bleach.clean(self.get_argument("id", None, True))

        # only allow zip files
        if path[-3:] != "zip":
            self.redirect("/admin/backups?id={}".format(server_id))

        backup_folder = backupmgr.get_backup_folder_for_server(server_id)

        # Grab our backup path from the DB
        backup_list = Backups.get(Backups.server_id == int(server_id))
        base_folder = backup_list.storage_location

        # get full path of our backups
        server_backup_folder = os.path.join(base_folder, backup_folder)
        server_backup_file = os.path.join(server_backup_folder, path)

        if helper.check_file_exists(server_backup_file):
            file_name = os.path.basename(server_backup_file)
            file_size = os.path.getsize(server_backup_file)
            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', 'attachment; filename=' + file_name)
            self.set_header('Accept-Ranges', 'bytes')

            # Gather information for partial file downloads (resume basically)
            if 'Range' in self.request.headers:
                partial = True
                # The only valid format of this header currently is
                # bytes=1-123
                start_offset,end_offset = self.request.headers['Range'].split("=")[1].split('-')
                start_offset = int(start_offset)
                end_offset = int(end_offset)
                self.set_header('Content-Length', end_offset - start_offset)
                self.set_header('Content-Range', "{}-{}/{}".format(start_offset, end_offset, file_size))
                self.set_status(206)
            else:
                # Set the range to the full file so we don't have to 
                # do a ton of if statements
                partial = False
                start_offset = 0
                end_offset = file_size
                self.set_header('Content-Length', file_size)

            logger.info("Serving file {} with a range of {} to {}".format(
                file_name, start_offset, end_offset
            ))

            with open(server_backup_file, 'rb') as f:
                position = 0
                if partial:
                    # Seek to the start of the requested byte range
                    # Mark our position
                    f.seek(start_offset)
                    position = start_offset
                while 1:
                    # If the number of bytes left are less than the chunk
                    # size, reset the chunk size to the remaining bytes
                    # Do this early for ranges smaller than chunks to prevent
                    # tornado error writting more than content length
                    # bytes.
                    if end_offset - position < chunk_size:
                        chunk_size = end_offset - position

                    # Read in chunk
                    data = f.read(chunk_size)
                    
                    # EOF
                    if not data:
                        break

                    try: 
                        self.write(data)
                        # wait for socket to flush
                        await self.flush()
                    except tornado.iostream.StreamClosedError:
                        # The client has closed the connection.
                        logger.info('Client terminated stream')
                        break
                    finally:
                        # Doing this explicitly prevents ballooning memory
                        # usage when multiple clients are downloading by
                        # deallocating before we release back to the event
                        # loop
                        del data

                    # Move position forward
                    position += chunk_size

                    # If we are at or past the end offset, we're done.
                    if position >= end_offset:
                        break

                    # relinquish control to the event loop once.
                    await asyncio.sleep(0)
                self.finish()
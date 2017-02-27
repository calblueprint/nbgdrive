
import json
from subprocess import Popen, PIPE
from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler

# This nbextension makes a few assumptions that may need to be handled at a later time.
# They are stated below:

# 1. When running on each singleuser, there is a config variable called JPY_USER with their unique identification
# 2. We will allow this extension to create a sync directory from the single user's home directory to data8/$JPY_USER
# 3. File deleted locally are not syncable to the sync directory, this is a bug we must fix
# 4. The /home directory contains just one folder, called `jovyan`, which is the standard student working directory

HOME_SUBFOLDER_NAME = "jovyan"

def make_gdrive_directory():
    drive_authenticated = check_gdrive_authenticated()
    sync_status = 'Could not create sync Directory.'

    if drive_authenticated['authentication'] == "authenticated":
        command = 'STORED_DIR="data8/$JPY_USER"; \
                    echo "Creating Google Drive Directory named $STORED_DIR."; \
                    DIR_EXISTS="$(gdrive list | grep -i $STORED_DIR | wc -l)"; \
                    [ $DIR_EXISTS -lt 1 ] && (RESULT=$(gdrive mkdir $STORED_DIR) && ID="$(echo $RESULT | cut -d " " -f 2)" && gdrive sync upload /home/' + HOME_SUBFOLDER_NAME + ' $ID) || echo "Directory already exists."; \
                    LOAD_DIRECTORY="$(gdrive list | grep -i $STORED_DIR | cut -c 1-28 | head -n 1)"; \
                    gdrive sync upload /home/' + HOME_SUBFOLDER_NAME + ' $LOAD_DIRECTORY'
        p = Popen(command, stdout=PIPE, shell=True)
        output, err = p.communicate()
        sync_status = 'Created Sync Directory'

    return {
        'status': sync_status
    }

def verify_gdrive_user(auth_code):
    p = Popen(['gdrive', 'about'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate(auth_code)
    return output

def sync_gdrive_directory():
    drive_authenticated = check_gdrive_authenticated()
    sync_status = 'Could not sync data to Google Drive'

    if drive_authenticated['authentication'] == "authenticated":
        command = 'STORED_DIR="data8/$JPY_USER"; \
                    LOAD_DIRECTORY="$(gdrive sync list | grep -i $STORED_DIR | cut -c 1-28 | head -n 1)"; \
                    gdrive sync upload /home/' + HOME_SUBFOLDER_NAME + ' $LOAD_DIRECTORY; \
                    echo "Syncing directory now."'
        p = Popen(command, stdout=PIPE, shell=True)
        output, err = p.communicate()
        sync_status = 'Successfully synced data to Google Drive'

    return {
        'status': sync_status
    }

def check_gdrive_authenticated():
    p = Popen(['gdrive', 'about'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate('')

    drive_authentication_url = str(output, 'utf-8').split('\n')[2]

    if 'http' not in drive_authentication_url:
        drive_authentication_url = "authenticated"

    return {
        'authentication': drive_authentication_url
    }

def check_gdrive_last_sync_time():
    lastSyncTime = "Drive has never been synced"

    command = 'STORED_DIR="data8/$JPY_USER"; \
               LOAD_DIRECTORY="$(gdrive sync list | grep -i $STORED_DIR | cut -c 1-28 | head -n 1)"; \
               gdrive info $LOAD_DIRECTORY | grep "Modified" | cut -c 11-20'
    p = Popen(command, stdout=PIPE, shell=True)
    output, err = p.communicate()
    lastSyncTime = str(output, 'utf-8').split('\n')[0]

    return {
        'lastSyncTime': lastSyncTime
    }

class SyncHandler(IPythonHandler):
    def get(self):
        self.finish(json.dumps(sync_gdrive_directory()))

class DriveHandler(IPythonHandler):
    def get(self):
        self.finish(json.dumps(make_gdrive_directory()))

class ResponseHandler(IPythonHandler):
    def get(self):
        self.finish(json.dumps(check_gdrive_authenticated()))

    def post(self):
        success = verify_gdrive_user(self.get_body_argument("message").encode('utf-8'))
        self.finish(success)

class LastSyncHandler(IPythonHandler):
    def get(self):
        self.finish(json.dumps(check_gdrive_last_sync_time()))

def setup_handlers(web_app):
    dir_route_pattern = url_path_join(web_app.settings['base_url'], '/createDrive')
    sync_route_pattern = url_path_join(web_app.settings['base_url'], '/syncDrive')
    response_route_pattern = url_path_join(web_app.settings['base_url'], '/authenticateDrive')
    lastSync_route_pattern = url_path_join(web_app.settings['base_url'], '/lastSyncTime')

    web_app.add_handlers('.*', [
        (dir_route_pattern, DriveHandler),
        (sync_route_pattern, SyncHandler),
        (response_route_pattern, ResponseHandler),
        (lastSync_route_pattern, LastSyncHandler)
    ])

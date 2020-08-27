import subprocess

from encyc import config


def push(local_paths, remote_dest, timeout=config.RSYNC_TIMEOUT):
    """Sync a list of local files to a remote dir
    
    @param local_paths: list Absolute paths for local files to transfer
    @param remote_dest: str Remote user, host, and destination dir
    """
    if not local_paths:
        return 'No local_paths: %s' % local_paths
    local = ' '.join(local_paths)
    # create the rsync command
    command = '/usr/bin/rsync --timeout=%s -va %s %s' % (str(timeout), local, remote_dest)
    print(command)
    # Run the commands.
    # shell=True is used bc escaped characters would cause failures.
    return subprocess.Popen(command, shell=True).wait()

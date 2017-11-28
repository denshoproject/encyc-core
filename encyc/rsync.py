import subprocess


def push(local_paths, remote_dest):
    """Sync a list of local files to a remote dir
    
    @param local_paths: list Absolute paths for local files to transfer
    @param remote_dest: str Remote user, host, and destination dir
    """
    if not local_paths:
        return 'No local_paths: %s' % local_paths
    local = ' '.join(local_paths)
    # create the rsync command
    rsync_cmd = '/usr/bin/rsync -va %s %s' % (local, remote_dest)
    # Run the commands.
    # shell=True is used bc escaped characters would cause failures.
    return subprocess.Popen(rsync_cmd, shell=True).wait()

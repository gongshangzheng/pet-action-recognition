"""Transfer comparison artifacts using a password prompt; never persist credentials."""
import argparse
import getpass
from pathlib import Path
import posixpath
import stat
import paramiko

p=argparse.ArgumentParser()
p.add_argument('operation',choices=['upload','download'])
p.add_argument('--host',default='115.154.235.243');p.add_argument('--port',type=int,default=22108)
p.add_argument('--user',default='wyy');p.add_argument('--remote',required=True);p.add_argument('--local',required=True)
a=p.parse_args()
client=paramiko.SSHClient()
# Session-only trust, matching the SSH connection already used for this server.
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(a.host,port=a.port,username=a.user,password=getpass.getpass('SSH password: '),
               look_for_keys=False,allow_agent=False,timeout=20)
sftp=client.open_sftp()

def mkdir(path):
    try: sftp.stat(path)
    except FileNotFoundError:
        mkdir(posixpath.dirname(path));sftp.mkdir(path)

def download(remote,local):
    local.mkdir(parents=True,exist_ok=True)
    for item in sftp.listdir_attr(remote):
        rp=posixpath.join(remote,item.filename);lp=local/item.filename
        if stat.S_ISDIR(item.st_mode): download(rp,lp)
        elif stat.S_ISREG(item.st_mode): sftp.get(rp,str(lp))

def upload(local,remote):
    if local.is_dir():
        mkdir(remote)
        for child in local.iterdir():
            upload(child,posixpath.join(remote,child.name))
    else:
        mkdir(posixpath.dirname(remote))
        sftp.put(str(local),remote)

try:
    if a.operation=='upload':
        source=Path(a.local)
        upload(source,a.remote)
        print('Uploaded',source,'to',a.remote)
    else:
        download(a.remote,Path(a.local))
        print('Downloaded',a.remote,'to',a.local)
finally:
    sftp.close();client.close()

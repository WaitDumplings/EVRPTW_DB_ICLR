"""Verify delivery checksums and safe archive members without extracting files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import zipfile


def safe_name(name):
    p=PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '..' not in p.parts and '\\' not in name


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('delivery',type=Path);a=p.parse_args()
    checked=[]
    for line in (a.delivery/'SHA256SUMS').read_text().splitlines():
        digest,name=line.split('  ',1)
        if not safe_name(name) or len(PurePosixPath(name).parts)!=1:raise ValueError('Unsafe checksum filename')
        archive=a.delivery/name
        with archive.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=digest:raise ValueError(f'Checksum mismatch: {name}')
        count=0
        if name.endswith('.zip'):
            with zipfile.ZipFile(archive) as z:
                if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate ZIP member')
                for m in z.infolist():
                    if not safe_name(m.filename) or stat.S_ISLNK(m.external_attr>>16):raise ValueError('Unsafe ZIP member')
                    if '.git' in PurePosixPath(m.filename).parts:raise ValueError('Git history in archive')
                    count+=1
                if z.testzip() is not None:raise ValueError('ZIP CRC mismatch')
        elif name.endswith('.tar.gz'):
            with tarfile.open(archive,'r:gz') as t:
                seen=set()
                for m in t:
                    if not safe_name(m.name) or not (m.isfile() or m.isdir()) or m.name in seen:raise ValueError('Unsafe or duplicate tar member')
                    if m.uid!=0 or m.gid!=0 or m.uname or m.gname:raise ValueError('Owner metadata in archive')
                    if '.git' in PurePosixPath(m.name).parts:raise ValueError('Git history in archive')
                    seen.add(m.name);count+=1
        else:raise ValueError('Unexpected archive format')
        checked.append({'archive':name,'members':count,'sha256':actual})
    print(json.dumps({'status':'PASS','archives':checked},indent=2))
if __name__=='__main__':main()

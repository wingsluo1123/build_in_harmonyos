"""Select a genuinely owned private test directory, not a projected parent UID."""
import os,stat,tempfile
from pathlib import Path

def private_test_parent(explicit,platform):
    uid=os.getuid()
    values=[explicit] if explicit else [os.environ.get('TMPDIR','')]
    if not explicit:
        try:values.append(tempfile.gettempdir())
        except OSError:pass
        if platform=='OHOS':values.append('/data/storage/el2/base/cache')
    rejected=[]
    for value in dict.fromkeys(values):
        if not value:continue
        parent=Path(value).absolute();leaf=None;identity=None
        try:
            for path in (parent,*parent.parents):
                if path.is_symlink():raise RuntimeError('Symlink in private temporary ancestry')
            if not parent.is_dir() or not os.access(parent,os.W_OK|os.X_OK):
                raise RuntimeError('Private temporary parent is not writable/traversable')
            if explicit:
                if parent.stat().st_uid!=uid:raise RuntimeError('Explicit private parent UID mismatch')
                return parent.resolve(strict=True)
            # Creating on HMDFS does not imply process ownership. Verify the
            # actual leaf inode instead of assuming mkdtemp grants that identity.
            leaf=Path(tempfile.mkdtemp(prefix='d',dir=parent));identity=leaf.lstat()
            if (not stat.S_ISDIR(identity.st_mode) or identity.st_uid!=uid
                    or stat.S_IMODE(identity.st_mode)!=0o700 or leaf.is_symlink()):
                raise RuntimeError('New private leaf lacks actual UID/0700 isolation')
            if len(str(leaf).encode())>=59:raise RuntimeError('Private leaf too long for UNIX test sockets')
            return leaf.resolve(strict=True)
        except (OSError,RuntimeError) as error:
            rejected.append(str(parent)+': '+str(error))
            if leaf is not None and identity is not None:
                # Only our just-created, still-identical empty inode; never
                # recurse, alter owner/mode, or remove a substituted path.
                current=leaf.lstat()
                if (current.st_dev,current.st_ino)==(identity.st_dev,identity.st_ino) and stat.S_ISDIR(current.st_mode):
                    leaf.rmdir()
    raise RuntimeError('No actual-owned private test directory: '+'; '.join(rejected))

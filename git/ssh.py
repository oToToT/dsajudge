import os, errno, re
import logging

log = logging.getLogger('gitosis.ssh')

_ACCEPTABLE_USER_RE = re.compile(r'^[a-zA-Z0-9_.-]+(@[a-zA-Z][a-zA-Z0-9.-]*)?$')

def isSafeUsername(user):
    match = _ACCEPTABLE_USER_RE.match(user)
    return (match is not None)

def readKeys(keydir):
    """
    Read SSH public keys from ``keydir/*.pub``
    """
    for filename in os.listdir(keydir):
        if filename.startswith('.'):
            continue
        basename, ext = os.path.splitext(filename)
        if ext != '.pub':
            continue

        if not isSafeUsername(basename):
            log.warn('Unsafe SSH username in keyfile: %r', filename)
            continue

        path = os.path.join(keydir, filename)
        f = file(path)
        for line in f:
            line = line.rstrip('\n')
            yield (basename, line)
        f.close()

COMMENT = '### autogenerated by gitosis, DO NOT EDIT'

def generateAuthorizedKeys(keys):
    TEMPLATE=('command="gitosis-serve %(user)s",no-port-forwarding,'
              +'no-X11-forwarding,no-agent-forwarding,no-pty %(key)s')

    yield COMMENT
    for (user, key) in keys:
        yield TEMPLATE % dict(user=user, key=key)

_COMMAND_RE = re.compile('^command="(/[^ "]+/)?gitosis-serve [^"]+",no-port-forw'
                         +'arding,no-X11-forwarding,no-agent-forwardi'
                         +'ng,no-pty .*')

def filterAuthorizedKeys(fp):
    """
    Read lines from ``fp``, filter out autogenerated ones.

    Note removes newlines.
    """

    for line in fp:
        line = line.rstrip('\n')
        if line == COMMENT:
            continue
        if _COMMAND_RE.match(line):
            continue
        yield line

def writeAuthorizedKeys(path, keydir):
    tmp = '%s.%d.tmp' % (path, os.getpid())
    try:
        in_ = file(path)
    except IOError, e:
        if e.errno == errno.ENOENT:
            in_ = None
        else:
            raise

    try:
        out = file(tmp, 'w')
        try:
            if in_ is not None:
                for line in filterAuthorizedKeys(in_):
                    print >>out, line

            keygen = readKeys(keydir)
            for line in generateAuthorizedKeys(keygen):
                print >>out, line

            os.fsync(out)
        finally:
            out.close()
    finally:
        if in_ is not None:
            in_.close()
    os.rename(tmp, path)

import codecs
import os


def read_text(path, utf8_strict=False):
    """Read text file; make sure text is in UTF-8.
    
    @param path: str Absolute path to file.
    @param utf8_strict: boolean
    @returns: unicode
    """
    if not os.path.exists(path):
        raise IOError('File is missing or unreadable: %s' % path)
    if utf8_strict:
        try:
            with codecs.open(path, 'rU', 'utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            bad = []
            with open(path, 'r') as f:
                for n,line in enumerate(f.readlines()):
                    try:
                        utf8 = line.decode('utf8', 'strict')
                    except UnicodeDecodeError:
                        bad.append(str(n))
            raise Exception(
                'Unicode decoding errors in line(s) %s.' % ','.join(bad)
            )
    else:
        with open(path, 'r') as f:
            return f.read()

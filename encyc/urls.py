PATTERNS = {
    'wikiprox-author': '/authors/%s/',
    'wikiprox-source': '/sources/%s/',
    'wikiprox-page': '/%s/',
}

def reverse(title, args=[]):
    return PATTERNS[title] % args

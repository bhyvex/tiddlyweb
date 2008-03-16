from tiddlyweb.web.http import HTTP415

def get_serialize_type(environ, serializers):
    # Use the accept headers to look up how we should serialize.
    # If we don't do that, and we had an extension, throw a 415,
    # otherwise, just do a default, this is needed to deal with
    # browsers promiscuiously asking for random stuff like text/xml.
    # It would be better if the info in tiddlyweb.accept was a 
    # list which we traverse until a hit. Will FIXME to do that
    # soonish.
    accept = environ.get('tiddlyweb.accept')
    ext = environ.get('tiddlyweb.extension')

    try:
        serialize_type, mime_type = serializers[accept]
    except KeyError:
        if ext and ext != accept:
            raise HTTP415, '%s type unsupported' % ext
        serialize_type, mime_type = serializers['default']
    return serialize_type, mime_type
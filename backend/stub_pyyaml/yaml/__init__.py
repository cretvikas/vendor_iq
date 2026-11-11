"""Pure-Python YAML stub. The C extension is not available on this platform."""
import json as _json

class YAMLError(Exception): pass
class MarkedYAMLError(YAMLError): pass
class SafeLoader: pass
class FullLoader: pass
class UnsafeLoader: pass
class Loader: pass
class Dumper: pass
class SafeDumper: pass

def safe_load(stream):
    if hasattr(stream, 'read'):
        return {}
    return {}

def safe_load_all(stream):
    return iter([])

def load(stream, Loader=None):
    return safe_load(stream)

def load_all(stream, Loader=None):
    return iter([])

def safe_dump(data, stream=None, **kwargs):
    result = ''
    if stream is not None:
        stream.write(result)
    return result

def dump(data, stream=None, Dumper=None, **kwargs):
    return safe_dump(data, stream=stream, **kwargs)

def dump_all(documents, stream=None, Dumper=None, **kwargs):
    return ''

def add_representer(*args, **kwargs): pass
def add_constructor(*args, **kwargs): pass

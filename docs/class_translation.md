# Class Translation

The library supports an *"automatic"* class translation process, although it
is turned off by default.
This can be devastatingly slow if improperly used, so the following is just a
short list of things to keep in mind when using it.

- Keep It (the object) Simple Stupid. (for exceptions, keep reading)
- Do not require init params (for exceptions, keep reading)
- Getter properties without setters could be dangerous (read: not tested)

If any of the above are issues, use the `_serialize` method (see usage below).
The server and client must **BOTH** have `use_jsonclass` configuration
item on and they must both have access to the same libraries used by the
objects for this to work.

If you have excessively nested arguments, it would be better to turn off the
translation and manually invoke it on specific objects using
`jsonrpclib.jsonclass.dump` / `jsonrpclib.jsonclass.load` (since the default
behavior recursively goes through attributes and lists / dicts / tuples).

* Sample file: `test_obj.py`

```python
# This object is /very/ simple, and the system will look through the
# attributes and serialize what it can.
class TestObj(object):
    foo = 'bar'

# This object requires __init__ params, so it uses the _serialize
# method and returns a tuple of init params and attribute values
# (the init params can be a dict or a list, but the attribute
# values must be a dict.)
class TestSerial(object):
    foo = 'bar'
    def __init__(self, *args):
        self.args = args
    def _serialize(self):
        return (self.args, {'foo':self.foo,})
```

* Sample usage:

```python
>>> import jsonrpclib
>>> import test_obj

# History is used only to print the serialized form of beans
>>> history = jsonrpclib.history.History()
>>> testobj1 = test_obj.TestObj()
>>> testobj2 = test_obj.TestSerial()
>>> server = jsonrpclib.Server(
...     'http://localhost:8080', history=history)

# The 'ping' just returns whatever is sent
>>> ping1 = server.ping(testobj1)
>>> ping2 = server.ping(testobj2)

>>> print(history.request)
{"id": "7805f1f9-9abd-49c6-81dc-dbd47229fe13", "jsonrpc": "2.0",
 "method": "ping", "params": [
    {"__jsonclass__": ["test_obj.TestSerial", []], "foo": "bar"}
 ]}
>>> print(history.response)
{"id": "7805f1f9-9abd-49c6-81dc-dbd47229fe13", "jsonrpc": "2.0",
 "result": {
    "__jsonclass__": ["test_obj.TestSerial", []],
    "foo": "bar"
 }}
```

This behavior is turned on by default.
To deactivate it, just set the `use_jsonclass` member of a server `Config`
to `False`.
If you want to use a per-class serialization method, set its name in the
`serialize_method` member of a server `Config`.
Finally, if you are using classes that you have defined in the implementation
(as in, not a separate library), you'll need to add those
(on **BOTH** the server and the client) using the `config.classes.add()`
method.

Feedback on this "feature" is very, VERY much appreciated.

## Declaring the accepted classes

```{versionchanged} 1.2
A `__jsonclass__` entry can only be converted back into an object if the class
it names has been declared: the library doesn't import the classes named by the
peer anymore.
```

An unknown class raises a `TranslationError`, which is reported to the peer as
an invalid request.
Declare the classes you accept with `config.classes.add()`, on **BOTH** the
server and the client:

```python
import jsonrpclib.config
from jsonrpclib import ServerProxy

config = jsonrpclib.config.Config()
config.classes.add(TestSerial)                   # as "TestSerial"
config.classes.add(TestObj, "test_obj.TestObj")  # by full name

server = ServerProxy("http://localhost:8080", config=config)
```

Classes are looked for using the full name written in the payload
(`test_obj.TestSerial`), then using their short name (`TestSerial`): both
registrations above work.
`decimal.Decimal` is always accepted, as it is a value type the library
serializes itself.

The previous behaviour, where any importable class named by the peer was
imported then instantiated with the arguments it chose, is still available as
an explicit opt-in:

```python
# Only when both ends are trusted: this lets the peer instantiate
# any importable class with the arguments of its choice
config = jsonrpclib.config.Config(allow_dynamic_classes=True)
```

```{warning}
Do not set `allow_dynamic_classes` across a trust boundary: it is the
equivalent of calling `pickle.loads()` on data controlled by the peer.
```

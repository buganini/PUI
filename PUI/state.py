from .view import *
from collections import defaultdict

class StateMutationInViewBuilderError(Exception):
    pass

class DummyBinding():
    def __init__(self, value):
        self.value = value

class BaseBinding():
    pass

class AttrBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except:
            pass
        self.state = state
        self.key = key
        dt = type(getattr(self.state, self.key))
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        return getattr(self.state, self.key)

    @value.setter
    def value(self, value):
        try: # skip validation error
            setattr(self.state, self.key, self.func(value))
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateObject__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateObject__binders")[self.key] = None
        setattr(getattr(self.state, "_StateObject__values"), self.key, getter())
        getattr(self.state, "_StateObject__binders")[self.key] = (getter, setter)

    def emit(self):
        listeners = set()
        for l in getattr(self.state, "_StateObject__listeners").values():
            listeners.update(l)
        _notify(getattr(self.state, "_StateObject__pending"), listeners)

class ListBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except PuiViewNotFoundError:
            pass
        self.state = state
        self.key = key
        dt = type(self.state[self.key])
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        try: # skip validation error
            return self.state[self.key]
        except:
            pass

    @value.setter
    def value(self, value):
        self.state[self.key] = self.func(value)

    def change(self, callback):
        getattr(self.state, "_StateList__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateList__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateList__binders")[self.key] = (getter, setter)

    def emit(self):
        _notify(getattr(self.state, "_StateList__pending"), getattr(self.state, "_StateList__listeners"))

class DictBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except PuiViewNotFoundError:
            pass
        self.state = state
        self.key = key
        dt = type(self.state[self.key])
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        return self.state[self.key]

    @value.setter
    def value(self, value):
        try: # skip validation error
            self.state[self.key] = self.func(value)
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateDict__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateDict__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateDict__binders")[self.key] = (getter, setter)

    def emit(self):
        _notify(getattr(self.state, "_StateDict__pending"), getattr(self.state, "_StateDict__listeners"))

def _notify(pending, listeners):
    if pending is None:
        tbd = []
        for l in listeners:
            if l.retired_by:
                tbd.append(l)
        for l in tbd:
            listeners.remove(l)
        for l in list(listeners):
            l.redraw()
    else:
        pending.update(listeners)

class BaseState():
    pass

def State(data=None):
    if data is None:
        return StateObject()
    if isinstance(data, list):
        return StateList(data)
    if isinstance(data, dict):
        return StateDict(data)
    return StateObject(data)

class StateObject(BaseState):
    def __init__(self, values=None):
        self.__listeners = defaultdict(set)
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        self.__pending = None
        if values is None:
            self.__values = BaseState()
        else:
            self.__values = values

    def __call__(self, key=None):
        if key is None:
            listeners = set()
            for l in self.__listeners.values():
                listeners.update(l)
            _notify(self.__pending, listeners)
            return
        try:
            view = find_puiview()
            self.__listeners[key].add(view)
        except PuiViewNotFoundError:
            pass
        return AttrBinding(self, key)

    def __enter__(self):
        self.__pending = set()
        return self

    def __exit__(self, ex_type, value, traceback):
        pending = self.__pending
        self.__pending = None
        _notify(self.__pending, pending)

        if ex_type is None: # don't consume exception
            return self

    # getter
    def __getattr__(self, key):
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners[key].add(view)
            except PuiViewNotFoundError:
                view = None
        ret = getattr(self.__values, key)
        if view:
            if isinstance(ret, StateObject):
                ret.__listeners[key].add(view)
            elif isinstance(ret, StateList):
                ret._StateList__listeners.add(view)
            elif isinstance(ret, StateDict):
                ret._StateDict__listeners.add(view)
        return ret

    # setter
    def __setattr__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)

            if type(value) is list:
                value = StateList(value)
            elif type(value) is dict:
                value = StateDict(value)
            if not hasattr(self.__values, key) or getattr(self.__values, key) != value:
                setattr(self.__values, key, value)
                _notify(self.__pending, self.__listeners[key])
                for cb in self.__callbacks[key]:
                    cb(value)

    # getter
    def __repr__(self):
        return f"StateObject({self.__values.__repr__()})"

class StateList(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        self.__pending = None
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def __call__(self, key=None):
        if key is None:
            _notify(self.__pending, self.__listeners)
            return
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return ListBinding(self, key)

    def __enter__(self):
        self.__pending = set()
        return self

    def __exit__(self, ex_type, value, traceback):
        pending = self.__pending
        self.__pending = None
        _notify(self.__pending, pending)

        if ex_type is None: # don't consume exception
            return self

    # getter
    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            view = None

        ret = self.__values[key]
        if view:
            if isinstance(ret, StateObject):
                ret._StateObject__listeners.add(view)
            elif isinstance(ret, StateList):
                ret.__listeners.add(view)
            elif isinstance(ret, StateDict):
                ret._StateDict__listeners.add(view)
        return ret
    # setter
    def __setitem__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if self.__binders.get(key):
            self.__binders[key][1](value)
        new = key >= len(self.__values)
        if new or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__pending, self.__listeners)
            for cb in self.__callbacks[key]:
                cb(value)
            if new:
                for cb in self.__callbacks[None]:
                    cb(value)

    # getter
    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    # getter
    def __len__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return len(self.__values)

    # getter
    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    # getter
    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    # setter
    def append(self, obj):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.append(obj)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # setter
    def clear(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.clear()
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter
    def count(self, value):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.count(value)

    # setter
    def extend(self, iterable):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.extend(iterable)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter
    def index(self, value, *args, **kwargs):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.index(value, *args, **kwargs)

    # setter
    def insert(self, index, object):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.insert(index, object)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[index]:
            cb(object)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter/setter
    def pop(self, index=-1):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(index)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[index]:
            cb(self.__values)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    # setter
    def remove(self, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.remove(value)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # setter
    def reverse(self, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.reverse(value)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)


    # setter
    def sort(self, *args, **kwargs):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.sort(*args, **kwargs)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter
    def get(self, index, default=None):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        if index >= 0 and index < len(self.__values):
            return self.__values[index]
        else:
            return default

    # getter
    def range(self):
        return range(len(self.__values))

class StateDict(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        self.__pending = None
        if values is None:
            self.__values = {}
        else:
            self.__values = values

    def __call__(self, key=None):
        if key is None:
            _notify(self.__pending, self.__listeners)
            return
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return DictBinding(self, key)

    def __enter__(self):
        self.__pending = set()
        return self

    def __exit__(self, ex_type, value, traceback):
        pending = self.__pending
        self.__pending = None
        _notify(self.__pending, pending)

        if ex_type is None: # don't consume exception
            return self

    # setter
    def __delitem__(self, key):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.__delitem__(key)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter
    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            view = None
        ret = self.__values[key]
        if view:
            if isinstance(ret, StateObject):
                ret._StateObject__listeners.add(view)
            elif isinstance(ret, StateList):
                ret._StateList__listeners.add(view)
            elif isinstance(ret, StateDict):
                ret.__listeners.add(view)
        return ret

    # getter
    def __getattr__(self, key):
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners.add(view)
            except PuiViewNotFoundError:
                view = None
        ret = getattr(self.__values, key)
        if view:
            if isinstance(ret, StateObject):
                ret._StateObject__listeners.add(view)
            elif isinstance(ret, StateList):
                ret._StateList__listeners.add(view)
            elif isinstance(ret, StateDict):
                ret.__listeners.add(view)
        return ret

    # setter
    def __setattr__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)
            _notify(self.__pending, self.__listeners)
            return setattr(self.__values, key, value)

    # getter
    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    # getter
    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    # getter
    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    # setter
    def __setitem__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if self.__binders.get(key):
            self.__binders[key][1](value)
        if not key in self.__values or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[key]:
            cb(value)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # setter
    def clear(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.clear()
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    # getter
    def get(self, key, default=None):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.get(key, default)

    # getter
    def items(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.items()

    # getter
    def keys(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.keys()

    # getter/setter
    def pop(self, key, default=None):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(key, default)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    # setter
    def setdefault(self, key, default=None):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.setdefault(key, default)
        _notify(self.__pending, self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    # getter
    def values(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.values()

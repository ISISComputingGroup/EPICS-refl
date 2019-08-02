"""
Useful items that allow the observable pattern to be implemented on a class.
"""


class _ListenerInfo:
    """
    Information on listeners.
    Listeners is the set of listeners which should be informed on trigger.
    last_value: the last value that was sent to the listeners
    """
    def __init__(self):
        self.listeners = set()
        self.last_value = None


def observable(*allowed_listener_types):
    """
    Makes a class observable, i.e. can have listeners added to it. Will create 2 methods in the class called
        add_listener: which allows you to add a listener to the class, you must pass in the type you want to listen for
        trigger_listeners: which allows you to trigger the listeners you should pass the new value to this method
            when you trigger it in your class
    Args:
        allowed_listener_types: the listeners types that you can trigger on

    Returns:class with methods added
    """
    def _wrapper(cls):
        """
        Wrapper to allow arguments to be set in this wrapper
        Args:
            cls: class being wrapped
        Returns: class
        """

        def _add_listener(self, listener_type, listener):
            """
            Add a listener of the given type to this class
            Args:
                self: instance of the class
                listener: listener to add
            """
            _get_listeners_info(self, listener_type).listeners.add(listener)

        def _get_listeners_info(self, listener_type):
            """
            Get the listeners for a given type
            Args:
                self: class instance
                listener_type: type of the listener set to get

            Returns:
                (_ListenerInfo): set of listeners for this type
            Raises: KeyError of type is not something that can be observed
            """
            try:
                try:
                    return self._listeners_info[listener_type.__name__]
                except AttributeError:
                    self._listeners_info = {allowed_type.__name__: _ListenerInfo()
                                            for allowed_type in allowed_listener_types}
                    return self._listeners_info[listener_type.__name__]
            except KeyError:
                raise TypeError("Trigger or add listener called with non observer type {}".format(
                    listener_type.__name__))

        def _trigger_listeners(self, new_value):
            """
            Trigger all the listeners with the new value.
            Args:
                self: instance of the class
                new_value: the new value that the listeners should be informed of
            """
            listeners_and_value = _get_listeners_info(self, type(new_value))
            listeners_and_value.last_value = new_value
            for listener in listeners_and_value.listeners:
                listener(new_value)

        def _listener_last_value(self, listener_type):
            listeners_and_value = _get_listeners_info(self, listener_type)
            return listeners_and_value.last_value

        # add the method which allows observers of the class to add their listeners to it
        setattr(cls, "add_listener", _add_listener)

        # add the method which triggers all the listeners
        setattr(cls, "trigger_listeners", _trigger_listeners)

        setattr(cls, "listener_last_value", _listener_last_value)

        return cls
    return _wrapper

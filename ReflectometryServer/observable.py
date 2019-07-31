"""
Useful items that allow the observable pattern to be implemented on a class.
"""


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
            _get_listeners(self, listener_type).add(listener)

        def _get_listeners(self, listener_type):
            """
            Get the listeners for a given type
            Args:
                self: class instance
                listener_type: type of the listener set to get

            Returns: set of listeners for this type
            Raises: KeyError of type is not something that can be observed
            """
            try:
                return self._listeners[listener_type.__name__]

            except AttributeError:
                listeners = {allowed_listener_type.__name__: set() for allowed_listener_type in allowed_listener_types}
                self._listeners = listeners
                return self._listeners[listener_type.__name__]

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
            listeners = _get_listeners(self, type(new_value))
            for listener in listeners:
                listener(new_value)

        # add the method which allows observers of the class to add their listeners to it
        setattr(cls, "add_listener", _add_listener)

        # add the method which triggers all the listeners
        setattr(cls, "trigger_listeners", _trigger_listeners)

        return cls
    return _wrapper

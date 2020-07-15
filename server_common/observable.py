"""
Useful items that allow the observable pattern to be implemented on a class.
"""


class _ListenerInfo:
    """
    Information on listeners.
    Listeners is the set of listeners which should be informed on trigger.
    last_value: the last value that was sent to the listeners
    pre_trigger_function: an optional piece of code to execute before triggering updates for this listener type.
    """
    def __init__(self):
        self.listeners = set()
        self.last_value = None
        self.pre_trigger_function = None


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

        def _add_listener(self, listener_type, listener, run_listener=False):
            """
            Add a listener of the given type to this class
            Args:
                self: instance of the class
                listener_type: the type of listener
                listener: listener to add
                run_listener: if the last value is set then run the listener just added with it
            """
            info = _get_listeners_info(self, listener_type)
            info.listeners.add(listener)
            if run_listener and info.last_value is not None:
                listener(info.last_value)

        def _remove_listener(self, listener_type, listener):
            """
            Remove a listener of the given type from this class
            Args:
                self: instance of the class
                listener_type: the type of listener
                listener: listener to remove
            """
            _get_listeners_info(self, listener_type).listeners.remove(listener)

        def _add_pre_trigger_function(self, listener_type, pre_trigger_function):
            """
            Add a function to be executed before triggering the listeners for a given type.
            Args:
                self: instance of the class
                listener_type: the type of listener
                pre_trigger_function: the function to execute before triggering listeners
            """
            _get_listeners_info(self, listener_type).pre_trigger_function = pre_trigger_function

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
            listeners_info = _get_listeners_info(self, type(new_value))

            if listeners_info.pre_trigger_function is not None:
                listeners_info.pre_trigger_function()

            listeners_info.last_value = new_value
            for listener in listeners_info.listeners:
                listener(new_value)

        def _listener_last_value(self, listener_type):
            """
            Get the last triggered value of the listener for the given type.
            Args:
                self: instance of class
                listener_type: type of the listener set to get

            Returns: The last value that was triggered; None if this has not yet ben triggered.

            """
            listeners_info = _get_listeners_info(self, listener_type)
            return listeners_info.last_value

        # add the method which allows the observable to add a custom pre-trigger function to be executed on an event for
        # the given listener type.
        setattr(cls, "_add_pre_trigger_function", _add_pre_trigger_function)

        # add the method which allows observers of the class to add their listeners to it
        setattr(cls, "add_listener", _add_listener)

        # add the method which allows observers of the class to remove their listeners
        setattr(cls, "remove_listener", _remove_listener)

        # add the method which triggers all the listeners
        setattr(cls, "trigger_listeners", _trigger_listeners)

        setattr(cls, "listener_last_value", _listener_last_value)

        return cls
    return _wrapper

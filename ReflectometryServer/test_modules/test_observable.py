from collections import namedtuple

from hamcrest import *

import unittest

from ReflectometryServer import observable

ValueUpdate = namedtuple("ValueUpdate", ["value"])
NotValueUpdate = namedtuple("NotValueUpdate", ["value"])


@observable(ValueUpdate)
class Test:
    def set_value(self, new_value):
        self.trigger_listeners(ValueUpdate(new_value))

class TestObservable(unittest.TestCase):


    def setUp(self):
        self.value = None
        self.value2 = None

    def listener(self, value_update):
        self.value = value_update.value

    def listener2(self, value_update):
        self.value2 = value_update.value

    def test_GIVEN_class_with_observed_type_WHEN_add_listener_and_trigger_THEN_listners_triggers(self):
        expected_value = 1
        test = Test()
        test.add_listener(ValueUpdate, self.listener)

        test.set_value(expected_value)

        assert_that(self.value, is_(expected_value))

    def test_GIVEN_class_with_observed_type_WHEN_not_add_listener_and_trigger_THEN_nothing_triggered(self):
        expected_value = 0
        self.value = expected_value

        test = Test()

        test.set_value(1)

        assert_that(self.value, is_(expected_value))

    def test_GIVEN_class_with_observed_type_WHEN_call_trigger_of_wrong_type_THEN_error(self):
        @observable(ValueUpdate)
        class Test:
            def set_value(self, new_value):
                self.trigger_listeners(NotValueUpdate(new_value))

        test = Test()

        assert_that(calling(test.set_value).with_args(1), raises(TypeError))

    def test_GIVEN_class_with_observed_type_WHEN_call_add_listener_of_wrong_type_THEN_error(self):
        test = Test()

        assert_that(calling(test.add_listener).with_args(NotValueUpdate, self.listener), raises(TypeError))

    def test_GIVEN_class_with_observed_type_WHEN_add_2_listeners_and_trigger_THEN_both_triggers_happen(self):
        expected_value = 1
        test = Test()
        test.add_listener(ValueUpdate, self.listener)
        test.add_listener(ValueUpdate, self.listener2)

        test.set_value(1)

        assert_that(self.value, is_(expected_value))
        assert_that(self.value2, is_(expected_value))

    def test_GIVEN_class_with_observed_type_WHEN_add_listener_and_trigger_twice_THEN_listners_triggers_twice(self):
        expected_value = 1

        test = Test()
        test.add_listener(ValueUpdate, self.listener)

        test.set_value(0)
        test.set_value(expected_value)

        assert_that(self.value, is_(expected_value))

    def test_GIVEN_two_class_with_observed_type_WHEN_add_listeners_and_triggers_THEN_listners_triggers_correctly_for_correct_class(self):
        expected_value1 = 1
        expected_value2 = 2

        test = Test()
        test.add_listener(ValueUpdate, self.listener)
        test2 = Test()
        test2.add_listener(ValueUpdate, self.listener2)

        test.set_value(expected_value1)
        test2.set_value(expected_value2)

        assert_that(self.value, is_(expected_value1))
        assert_that(self.value2, is_(expected_value2))

    def test_GIVEN_one_class_with_2_observed_type_WHEN_add_listeners_and_triggers_THEN_listners_triggers_correctly_for_correct_class(self):
        expected_value1 = 1
        expected_value2 = 2

        @observable(ValueUpdate, NotValueUpdate)
        class Test:
            def set_value1(self, new_value):
                self.trigger_listeners(ValueUpdate(new_value))

            def set_value2(self, new_value):
                self.trigger_listeners(NotValueUpdate(new_value))

        test = Test()
        test.add_listener(ValueUpdate, self.listener)
        test.add_listener(NotValueUpdate, self.listener2)

        test.set_value1(expected_value1)
        test.set_value2(expected_value2)

        assert_that(self.value, is_(expected_value1))
        assert_that(self.value2, is_(expected_value2))

    def test_GIVEN_one_class_observed_type_float_WHEN_add_listeners_and_triggers_THEN_listners_triggers_correctly_for_correct_class(self):
        expected_value1 = 1.0

        @observable(float)
        class Test:
            def set_value(self, new_value):
                self.trigger_listeners(new_value)

        def listener(value_update):
            self.value = value_update

        test = Test()
        test.add_listener(float, listener)

        test.set_value(expected_value1)

        assert_that(self.value, is_(expected_value1))

    def test_GIVEN_class_with_cached_observed_type_WHEN_get_cache_THEN_default_returned(self):
        test = Test()

        assert_that(test.listener_last_value(ValueUpdate), is_(None))

    def test_GIVEN_class_with_cached_observed_type_WHEN_set_and_get_cache_THEN_set_value_returned(self):
        expected_value = 123
        test = Test()
        test.set_value(expected_value)

        assert_that(test.listener_last_value(ValueUpdate).value, is_(expected_value))

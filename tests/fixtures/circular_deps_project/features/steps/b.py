from behave import when
from a import helper_a


def helper_b():
    pass


@when("step b")
def step_b():
    helper_a()

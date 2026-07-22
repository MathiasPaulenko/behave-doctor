from behave import given
from b import helper_b


def helper_a():
    pass


@given("step a")
def step_a():
    helper_b()

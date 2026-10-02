import behave
from behave import given, step, then, use_step_matcher, when


@given("the user is logged in")
def given_user_logged_in():
    pass


@when("the user enters {text}")
def when_user_enters(text):
    pass


@then("the cart should contain {n} items")
def then_cart_contains(n):
    pass


use_step_matcher("re")


@step("the order (is|is not) confirmed")
def step_order_confirmed():
    pass


use_step_matcher("cfparse")


@given("a product with {amount:Number} converters")
def given_product_with_converter():
    pass


use_step_matcher("parse")


@behave.given("the user is on the login page")
def behave_given_login_page():
    pass

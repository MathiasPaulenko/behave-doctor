import behave
from behave import given, when, then, step


@given("the user is logged in")
def given_user_logged_in():
    pass


@when("the user enters {text}")
def when_user_enters(text):
    pass


@then("the cart should contain {n} items")
def then_cart_contains(n):
    pass


@step("re:the order (is|is not) confirmed")
def step_order_confirmed():
    pass


@given("a product with converter", converter=int)
def given_product_with_converter():
    pass


@behave.given("the user is on the login page")
def behave_given_login_page():
    pass

from behave import given, when, then


@given("the cart is empty")
def given_cart_empty():
    pass


@given("the cart has items")
def given_cart_has_items():
    pass


@when("the user adds an item to the cart")
def when_user_adds_item():
    pass


@when("the user proceeds to checkout")
def when_user_proceeds_to_checkout():
    pass


@then("the cart should contain one item")
def then_cart_contains_one():
    pass


@then("the order should be confirmed")
def then_order_confirmed():
    pass

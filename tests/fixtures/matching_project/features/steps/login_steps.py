from behave import given, when, then


@given("the user is logged in")
def given_user_logged_in():
    pass


@when("the user enters {credentials}")
def when_user_enters(credentials):
    pass


@then("the user should be logged in")
def then_user_logged_in():
    pass


@then("the user should be logged in")
def then_user_logged_in_duplicate():
    pass

from behave import given, when, then


@given("the user is on the login page")
def given_user_on_login_page():
    pass


@when("the user enters {credentials} credentials")
def when_user_enters_credentials(credentials):
    pass


@then("the user should be logged in")
def then_user_logged_in():
    pass


@then("the user should see an error message")
def then_user_sees_error():
    pass

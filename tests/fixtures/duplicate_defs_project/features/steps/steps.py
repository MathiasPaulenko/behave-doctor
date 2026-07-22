from behave import given


@given("the user is logged in")
def given_user_logged_in():
    pass


@given("THE USER IS LOGGED IN")
def given_user_logged_in_dup():
    pass

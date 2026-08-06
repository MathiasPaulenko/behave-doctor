from behave import given, when, then, step


@given('a user named "{name}"')
def given_user_named(context, name):
    pass


@step('a user named "{name}"')
def step_user_named(context, name):
    pass


@when("the user logs in")
def when_user_logs_in(context):
    pass


@then("the response should be successful")
def then_response_successful(context):
    pass

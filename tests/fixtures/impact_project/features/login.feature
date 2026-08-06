Feature: Login

  Scenario: Successful login
    Given the user is on the login page
    When the user enters valid credentials
    Then the user should be logged in

  Scenario: Failed login
    Given the user is on the login page
    When the user enters invalid credentials
    Then the user should see an error message

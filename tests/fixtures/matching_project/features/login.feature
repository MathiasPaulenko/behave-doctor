Feature: Login

  Scenario: Successful login
    Given the user is logged in
    When the user enters valid credentials
    Then the user should be logged in
    And an undefined step here

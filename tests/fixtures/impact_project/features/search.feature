Feature: Search

  Background:
    Given the user is on the login page

  Scenario: Search by keyword
    When the user enters valid credentials
    Then the user should be logged in

  Scenario: Search with filter
    When the user enters invalid credentials
    Then the user should see an error message

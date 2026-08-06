Feature: Ambiguous Match

  @smoke
  Scenario: Step matches multiple definitions
    Given a user named "Alice"
    When the user logs in
    Then the response should be successful

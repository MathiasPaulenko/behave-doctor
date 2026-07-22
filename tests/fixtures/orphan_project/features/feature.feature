Feature: Orphan

  @shared
  Scenario: Shared tag scenario one
    Given a step

  @shared
  Scenario: Shared tag scenario two
    Given a step

  @uniqueonly
  Scenario: Unique tag scenario
    Given a step

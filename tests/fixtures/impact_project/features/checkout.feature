Feature: Checkout

  Scenario: Add item to cart
    Given the cart is empty
    When the user adds an item to the cart
    Then the cart should contain one item

  Scenario: Complete checkout
    Given the cart has items
    When the user proceeds to checkout
    And the user enters shipping details
    Then the order should be confirmed

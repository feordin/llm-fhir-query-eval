Invariant: us-core-21
Description: "requester SHALL be present if intent is \"order\""
* severity = #error
* expression = "(intent='order' or intent='original-order' or intent='reflex-order'or intent='filler-order' or intent='instance-order') implies requester.exists()"
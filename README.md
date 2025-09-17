# BuildingTools Utilities

This repository contains helper functions for working with Maya instance-based workflows.

## Sorting instances by transform position

`instanceUtilities.sort_selected_by_position` reorders selected transforms in the Outliner.

* `axis`: Specify the axis to sort by (`"x"`, `"y"`, `"z"`, or `"auto"`).
* `descending`: Reverse the result order when `True`.
* `space`: Choose the coordinate space used to evaluate positions. Pass `"world"` (default) to match the previous behaviour, or `"local"` to evaluate positions relative to each parent.

```python
import instanceUtilities as utils

# Sort using local space coordinates for each parent
utils.sort_selected_by_position(axis="auto", space="local")
```

Values for `space` are case-insensitive and any other value raises a descriptive Maya error.

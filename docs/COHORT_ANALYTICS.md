# Customer Cohort Analytics

## Acquisition event

A customer enters a pilot acquisition cohort on their **first delivered order** inside the pilot scope.

A user who already had a delivered order before the pilot is not counted as newly acquired.

## Cohort week

```text
cohort_week = floor((first_delivery_date - pilot_start_date) / 7) + 1
```

## Retention cells

For each cohort Baytna reports:

```text
W0, W1, W2 ...
```

A customer is active in a retention week only when they have a delivered order in that week.

No login, view, favorite, cart, or notification-open event is substituted for a retained purchaser.

## Post-pilot summary

The post-pilot report calculates weighted W1 and W4 retention across cohorts that have reached those observation windows.

A cohort that has not yet reached W4 is not falsely treated as churned at W4.

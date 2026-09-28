# Money plus: budgets, savings, debts and friends

These build on the money log (payslips and spending you tell Alfred about). Amounts are in your own currency
(`JARVIS_CURRENCY`, GBP by default). Everything is saved as small `finance-*.json` files in your memory folder
on this PC. The only thing that goes online is the exchange rate for trips (the free European Central Bank rate,
and only the currency codes and total are sent).

Most answers also pop a window up on the Alfred screen. Bars turn amber when you go over. Clicking a bar or a
list item asks Alfred about it for you.

## Budgets and reports

1. **Set a budget**: "Set a food budget of 300 pounds a month." (Say "remove my fun budget" to drop one; Alfred
   checks first.)
2. **How much is left**: "How much have I got left for food?" Pops up bars of spent vs budget for every category.
3. **Over-budget warnings**: "Am I over budget anywhere?" Pops up a list of budgets that are over or nearly over.
4. **Spending trends**: "How has my spending changed over the last six months?" Pops up a chart of monthly totals,
   a table by category and the biggest changes. Add a category ("my food spending trend") for a chart of just that.
5. **Find hidden subscriptions**: "Do I have any subscriptions in my spending?" Pops up repeated payments with
   similar amounts; click one to add it to your subscriptions list.
6. **Monthly money report**: "Give me my money report for August." Pops up income, spending by category (chart),
   budget bars and what went in or out of your savings pots.
7. **Tax year summary**: "Summarise this tax year." (6 April to 5 April) Pops up take-home, spending, savings and
   a chart of take-home per month. "Summarise the 2025 tax year" for last year.
8. **Export to a spreadsheet**: "Export my money data to CSV." Saves `money export <date>.csv` in your Personal
   folder (or say another folder) and pops it up as a table.

## Savings, envelopes, net worth and receipts

9. **Savings pots**: "Make a holiday pot with a target of 1,500." / "Put 200 in the holiday pot." / "Take 50 out
   of the holiday pot." / "How are my savings pots doing?" Pops up progress bars towards each target.
10. **Cash envelopes**: "Put 200 in a groceries envelope." / "Spend 35 from the groceries envelope on the market." /
    "What's left in my envelopes?" Pops up how much is left in each.
11. **Net worth**: "My net worth today: savings 6,000, pension 20,000; credit card 500 owed." / "Show my net worth."
    Pops up the latest totals, a line chart over time and the latest breakdown.
12. **Receipts**: "Save a receipt: Argos, 39.99 for a kettle, two-year warranty, photo kettle.jpg in Shopping." /
    "Find my kettle receipt." Pops up the receipt photo when there's one, or a table of matching receipts with
    warranty end dates.

## Planning

13. **Debt payoff plan**: "Add my credit card: 2,000 at 24% APR, minimum 60 a month." then "How fast can I clear my
    debts paying an extra 100 a month?" Compares snowball (smallest first) with avalanche (highest interest
    first): payoff dates, total interest, a chart of what you owe over time for each, and the order they clear.
14. **Payday countdown**: "I get paid on the last working day of the month." (or "on the 25th", or "every 4 weeks
    from the 10th of September") then "How long till payday? I've got 400 left." Pops up a live countdown and says
    how much you can spend a day. Paydays on a weekend move to the Friday before (bank holidays aren't counted).
15. **Can I afford it?**: "Can I afford a 120 pound jacket? I've got 1,200 in the bank." Takes off bills due before
    payday (from your household bills) and what's left in your budgets. Pops up the sums.
16. **Cost per use and habits**: "What's the cost per use of a 120 pound coat I'll wear 300 times?" /
    "What does a 3.50 coffee five days a week cost me?" The habit one pops up the cost per week, month, year
    and five years.
17. **Trip budget**: "Set up a Spain trip with 800 euros." / "Spent 60 euros on tapas in Spain." /
    "How much have I spent in Spain?" Pops up spent vs budget, what you bought, and the total in pounds.

## Friends and IOUs

18. **Who owes whom**: "Sam owes me 20 for the taxi." / "I paid 90 for dinner split with Sam and Alex." /
    "Who owes me money?" Pops up everyone's balance and the simplest way to settle.
19. **Settle up**: "Sam paid me back." / "Alex gave me 10." Records the payment.
20. **Simplify a group's debts**: "Simplify the debts between my friends." Pops up the fewest payments that clear
    everyone; click one when it's been paid.

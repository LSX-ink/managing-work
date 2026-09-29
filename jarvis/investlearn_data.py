"""Plain-words teaching content for investing basics: glossary, myths, scam warnings, UK wrappers, risk categories.

General education only. Nothing here says what to buy, and rules and limits change: check GOV.UK for the current ones.
"""

GLOSSARY = {
    "asset": "Something you own that has value, such as cash, shares, a bond or property.",
    "share": "A small slice of ownership in a company. Its price goes up and down. Also called a stock or an equity.",
    "equity": "Another word for a share in a company, or for the part of something you own outright.",
    "bond": "A loan you make to a company or government. It pays interest and is repaid at the end, if the borrower can pay.",
    "gilt": "A bond issued by the UK government.",
    "fund": "A pot of many investments pooled together and run by a manager, so one purchase spreads across lots of holdings.",
    "index": "A list that measures a market, for example the biggest 100 UK companies. It is a measuring stick, not something you buy.",
    "index fund": "A fund that simply copies an index instead of trying to beat it. Also called a tracker.",
    "tracker": "A fund that follows an index automatically. Usually cheaper than a fund run by a manager picking holdings.",
    "etf": "Exchange-traded fund: a fund whose shares are bought and sold on a stock exchange during the day.",
    "unit trust": "A type of fund where you buy units. Priced once a day.",
    "oeic": "Open-ended investment company: a fund structure similar to a unit trust, common in the UK.",
    "active fund": "A fund where a manager picks investments trying to beat the market. Usually costs more.",
    "passive fund": "A fund that copies a market instead of picking. Usually costs less.",
    "ocf": "Ongoing charges figure: the yearly cost of running a fund, shown as a percentage of what you hold in it.",
    "platform fee": "What an investing website or app charges to hold your investments, often a yearly percentage or a flat sum.",
    "dealing fee": "A charge some platforms make each time you buy or sell.",
    "spread": "The gap between the buying price and the selling price of something. It is a small hidden cost of trading.",
    "dividend": "A share of a company's profit paid to its shareholders. Not guaranteed; companies can cut or stop it.",
    "yield": "Income from an investment as a percentage of its price, for example a 3% dividend yield.",
    "capital gain": "Profit when something sells for more than you paid. A capital loss is the opposite.",
    "total return": "Growth in price plus income such as dividends, over a period.",
    "compound growth": "Growth on your growth: each year's gain is added and then earns its own gain.",
    "inflation": "The general rise in prices over time, which makes each pound buy a little less.",
    "real return": "Return after taking off inflation. It shows the change in what your money can actually buy.",
    "nominal return": "Return before inflation is taken off, the headline number.",
    "diversification": "Spreading money across many different things so one bad one hurts less. It does not remove risk.",
    "asset allocation": "How your money is split between kinds of investment, such as shares, bonds and cash.",
    "rebalancing": "Nudging a mix back to its planned split after some parts have grown faster than others.",
    "volatility": "How much and how fast a price swings up and down. Higher swings mean a bumpier ride.",
    "bull market": "A long period when prices are rising broadly.",
    "bear market": "A long period when prices fall broadly, often described as a fall of 20% or more.",
    "correction": "A shorter, smaller fall in prices, often described as around 10%.",
    "risk": "The chance that things turn out worse than hoped, including losing some or all of what you put in.",
    "risk tolerance": "How much ups and downs you can stomach without panicking. It is about feelings.",
    "capacity for loss": "How much you could actually afford to lose without real harm to your life. It is about your circumstances.",
    "time horizon": "How long until you need the money. Longer usually means more time to ride out falls.",
    "liquidity": "How quickly something can be turned into cash without losing value. Cash is very liquid; property is not.",
    "portfolio": "All your investments taken together.",
    "isa": "Individual Savings Account: a UK tax-free wrapper with a yearly allowance. Check GOV.UK for the current limit.",
    "stocks and shares isa": "An ISA that holds investments. Growth and income inside it are free of UK income and capital gains tax.",
    "cash isa": "An ISA that holds cash savings and pays tax-free interest.",
    "lifetime isa": "LISA: for ages 18 to 39 to open, government adds 25% of what you pay in (yearly limit applies), for a first home or age 60. Withdrawing otherwise carries a penalty.",
    "sipp": "Self-invested personal pension: a pension you choose the investments for yourself.",
    "workplace pension": "A pension arranged through your employer, usually with contributions from both of you.",
    "auto-enrolment": "UK rule that employers must put eligible workers into a workplace pension unless they opt out.",
    "defined contribution": "A pension whose value depends on what was paid in and how it grew. Most modern ones are like this.",
    "defined benefit": "A pension that pays a set income based on salary and years of service, often called final salary.",
    "state pension": "The UK government pension paid from state pension age. Depends on your National Insurance record.",
    "tax relief": "Pension contributions get tax help: the government tops up or you pay less tax. Check GOV.UK for the details.",
    "salary sacrifice": "Agreeing with your employer to take less pay in exchange for a pension contribution, which can save tax and National Insurance.",
    "gia": "General investment account: a normal investing account with no tax wrapper, so gains and income may be taxable.",
    "capital gains tax": "Tax on profit when you sell some assets above a yearly tax-free amount. Check GOV.UK for the current rules.",
    "fscs": "Financial Services Compensation Scheme: protects eligible money if an authorised firm fails, up to limits. It does not cover falls in value.",
    "fca": "Financial Conduct Authority: the UK regulator of financial firms. Its Register shows who is authorised.",
    "pound-cost averaging": "Investing a fixed amount at regular times, so you buy more when prices are low and less when high.",
    "lump sum": "Investing a large amount all at once.",
    "drawdown": "Taking money out of your pension or investments bit by bit while the rest stays invested.",
    "annuity": "A product that swaps a pot for a guaranteed income, usually for life.",
    "fire": "Financial independence, retire early: saving hard so your investments can cover your living costs.",
    "safe withdrawal rate": "The yearly percentage of a pot people have taken in the past without running out. The 4% rule is one rule of thumb, not a promise.",
    "sequence of returns risk": "The danger of bad market years arriving just as you start taking money out, which hurts far more than the same bad years later.",
    "emergency fund": "Easy-access cash kept for surprises such as a broken boiler or lost job, usually a few months of essentials.",
    "market cap": "Market capitalisation: a company's share price multiplied by the number of shares, showing how big it is.",
    "p/e ratio": "Price-to-earnings ratio: the share price divided by profit per share. A rough gauge of how expensive a share is.",
    "benchmark": "A measuring stick, often an index, to compare how an investment did.",
    "hedge": "A move meant to reduce a risk, like insurance, which usually costs something.",
    "leverage": "Investing with borrowed money. It magnifies gains and losses and can lose more than you put in.",
    "short selling": "Betting that a price will fall. It can lose more than you put in. Not a beginner topic.",
    "cryptoasset": "A digital token with no guaranteed value. Very volatile and largely unregulated, so treat as very high risk.",
    "ponzi scheme": "A fraud paying early investors with new investors' money until it collapses.",
}

MYTHS = [
    ("You need lots of money to start investing.", "Many platforms let you start with small regular amounts. Costs matter more at small sizes, so compare them."),
    ("Investing is the same as gambling.", "Gambling has a house edge against you. Investing in a broad spread has historically been rewarded over long periods, but with no guarantees and real risk of loss."),
    ("You can time the market by getting out before falls.", "Even professionals rarely call the highs and lows, and missing a few of the best days can cost a lot. There is no sure timing method."),
    ("Past performance shows what will happen next.", "It does not. Every legitimate ad says so, because it is true."),
    ("Cash is completely safe.", "It is safe from price swings, but inflation quietly eats what it can buy. Cash is right for short-term needs and emergencies."),
    ("A higher return is always better.", "Higher possible returns come with higher risk. If a return looks far above the rest, ask what is being hidden."),
    ("Fees of 1% are tiny.", "Over 30 years a 1% yearly charge can take a big bite because it compounds too. Try the fees calculator to see."),
    ("You should pay off all debt before saving anything.", "Expensive debt like credit cards usually comes first, but a small emergency fund stops new debt when surprises arrive. It depends on your situation."),
    ("A pension is only for old people.", "The earlier money goes in, the longer it has to compound, and tax relief and employer money can boost it."),
    ("You lose everything if the market crashes.", "Prices can fall a lot but they are not gone unless a company fails. A broad fund holds many, though falls can still be painful."),
    ("Diversification guarantees no losses.", "It reduces the damage from one thing failing. In a big market fall, most things can drop together."),
    ("Someone recommended it online, so it must be good.", "Social media tips are a common route for scams and pump-and-dump schemes. Check the FCA Register and be sceptical."),
]

SCAMS = [
    ("Guaranteed returns", "No genuine investment can guarantee profit. Promises like 'risk-free 20% a month' are a classic scam sign."),
    ("Pressure to act now", "Limited-time deals, countdowns and calls saying you will miss out. Real firms give you time to think."),
    ("Cold calls, texts or DMs", "Unsolicited investment offers by phone, message or social media are a big red flag. Be wary of anyone who contacts you first."),
    ("Not on the FCA Register", "Check the firm on the FCA Register (register.fca.org.uk) using contact details you find yourself, not the ones you were given."),
    ("Clone firms", "Scammers copy real, authorised firms' names, addresses and websites. Phone the real firm on a number from the FCA Register to check."),
    ("Celebrity or influencer endorsements", "Fake adverts use famous faces. If a famous person seems to be recommending a scheme, assume it is fake until proved otherwise."),
    ("Crypto and forex 'trading bots'", "Promises of automatic profits are typical of scams. Being unregulated means little or no protection."),
    ("Romance and friendship investing", "Someone you have only met online steering you toward investing. Never send money to someone you have not met in person."),
    ("Recovery scams", "After a loss, someone offers to get your money back for a fee. Real help never asks for money upfront."),
    ("Secrecy and unusual payments", "Being told to keep it quiet, lie to your bank, or pay by transfer to a personal account or in gift cards."),
]

SCAM_CHECKS = [
    "Did they contact you first, by phone, text, email or social media?",
    "Do they promise guaranteed or unusually high returns?",
    "Are you being pushed to decide quickly?",
    "Is the firm missing from the FCA Register, or do you only have contact details they gave you?",
    "Were you asked to keep it secret or to pay by transfer, crypto or gift cards?",
    "Did you find it through an ad with a famous person or a stranger online?",
]

WRAPPERS = {
    "stocks and shares isa": "A tax wrapper for investments. Growth and income inside are free of UK income tax and capital gains tax. There is a yearly allowance shared across all your ISAs, and the value can go down as well as up.",
    "cash isa": "A savings account inside the ISA wrapper, so interest is tax-free. It counts toward the same yearly ISA allowance.",
    "lifetime isa": "For 18 to 39 year olds to open. The government adds a 25% bonus on what you pay in, up to a yearly limit. Money is for a first home or from age 60. Taking it out for anything else means a 25% charge, which is more than the bonus and can leave you with less than you put in.",
    "innovative finance isa": "A higher-risk ISA for peer-to-peer style lending. Not covered by the FSCS in the same way. Only for those who understand the risks.",
    "junior isa": "A tax-free account for a child, opened by a parent or guardian. Money belongs to the child and is locked until 18. Has its own yearly limit.",
    "workplace pension": "Set up through your job. You pay in, your employer usually pays in too, and you get tax relief. Money is locked until minimum pension age. Many employers match higher contributions.",
    "sipp": "A pension you manage yourself, with more choice of investments. Same tax relief and locking rules as other pensions.",
    "state pension": "Paid by the government from state pension age based on your National Insurance record. Check your forecast on GOV.UK.",
    "general investment account": "A normal investing account with no tax wrapper. No limit, but gains above the tax-free amount and dividends above the allowance may be taxable.",
    "premium bonds": "NS&I savings where interest is replaced by monthly prize draws. Backed by the government and the prizes are tax-free, but you might win nothing.",
}

RISK_LEVELS = {
    "cautious": "Prefers steadier values and worries about falls. Money mostly sits in cash and lower-risk things, which can lag inflation. Suits short time horizons.",
    "balanced": "Accepts some ups and downs for the chance of growth. Usually a mix of shares and steadier assets. Suits medium time horizons.",
    "adventurous": "Can handle big swings for the chance of higher growth over a long time. Mostly shares. Suits long horizons and needs a strong emergency fund. Falls of 30% or more can happen.",
}

RISK_QUESTIONS = [
    ("When do you need this money?", ["Within 3 years", "In 3 to 10 years", "More than 10 years away"]),
    ("Your money falls 20% in a year. What is your gut reaction?", ["Sell to stop the fall", "Worry, but wait", "Fine, or even keep adding"]),
    ("How would losing a quarter of it affect your life?", ["Seriously", "It would hurt but I'd cope", "Hardly at all"]),
    ("Do you have 3 to 6 months of essentials saved separately?", ["No", "Some", "Yes"]),
    ("How much investing experience do you have?", ["None yet", "A little", "Quite a lot"]),
    ("Which sounds best?", ["Small steady growth, tiny falls", "Medium growth, some falls", "Higher growth, big falls possible"]),
]

EXPLAINERS = {
    "pound_cost_averaging": ("Pound-cost averaging", [
        "You invest the same amount on a regular schedule, say 100 pounds a month.",
        "When prices are low your 100 buys more units; when high, fewer. Your average cost ends up between the extremes.",
        "It does not guarantee a profit or beat investing a lump sum straight away. If markets rise on average, a lump sum has often done better. Its main benefit is that it is a habit and it removes the worry of picking one moment.",
        "Try the pound_cost_averaging calculator with made-up prices to see it."]),
    "four_percent": ("The 4% rule", [
        "A rule of thumb from US research: if you take 4% of your pot in the first year and then raise that by inflation, the money lasted 30 years in past US data.",
        "So the pot needed is about 25 times your yearly spending.",
        "Caveats: it is not a promise. It came from past US markets, not the future, and not the UK. Longer retirements need a lower rate. Fees, taxes and bad early years (sequence of returns risk) matter. Many people prefer 3 to 3.5% for early retirement or a flexible approach."]),
    "diversification": ("Diversification", [
        "Do not put all your eggs in one basket: spread money across many companies, industries, countries and asset types.",
        "If one company collapses, it hurts less. A broad fund does this in a single purchase.",
        "It reduces the risk of one thing going wrong; it cannot remove the risk that markets as a whole fall, and holding lots of similar things is not real diversification."]),
    "risk": ("Risk and reward", [
        "Risk is the chance of a worse result than you hoped, including losing money. Reward is the extra return that has historically come from taking it, but never guaranteed.",
        "Cash has low price risk but inflation risk. Bonds sit in the middle. Shares swing most but have grown most over long periods.",
        "Your time horizon and capacity for loss matter more than what feels exciting."]),
    "compound": ("Compound growth", [
        "Growth earns growth. 1,000 pounds at 5% becomes 1,050 after one year, then the next 5% is on 1,050, and so on.",
        "Time is the strongest ingredient. Starting earlier matters more than starting bigger.",
        "It works in reverse on fees and debts. Real returns vary year to year and can be negative."]),
    "inflation": ("Inflation", [
        "Prices rise over time. At 2.5% a year, prices double in about 29 years.",
        "Money in a cash account paying less than inflation buys less each year even though the number looks safe.",
        "Real return is your return minus inflation."]),
    "fees": ("Fees and charges", [
        "Fees come off your money every year whether it grows or not, and they compound like returns do.",
        "A 1% yearly charge versus 0.2% can mean tens of thousands of pounds less over decades.",
        "Look at the fund charge (OCF), the platform fee, dealing fees and the spread. Compare total cost."]),
    "emergency_fund": ("Emergency fund first", [
        "Before investing money you might need, build easy-access savings for surprises, often three to six months of essential spending.",
        "Investments can be down just when you need cash, forcing a sale at a bad time.",
        "Also weigh expensive debt: interest on a credit card is usually more than savings earn. It is your call, and it depends on your situation."]),
    "time_horizon": ("Time horizon", [
        "The date you need the money decides how much risk makes sense.",
        "Needed within about five years: falls could hit at the wrong time, so steadier places suit better.",
        "Ten or more years away: there is more time to recover from falls, though nothing is certain."]),
    "pensions": ("Pension basics", [
        "A pension is a long-term pot you cannot normally touch until minimum pension age (check GOV.UK).",
        "Tax relief: basic-rate relief is added to what you pay in, and higher-rate taxpayers can claim more through their tax return. Check GOV.UK for the details.",
        "Workplace pensions add employer money. Contributing at least enough to get any employer match is often called free money, but check your own scheme's terms.",
        "Later you can take it via drawdown, an annuity or lump sums, each with tax rules."]),
}

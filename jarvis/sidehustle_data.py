"""Built-in facts for the side-hustle abilities: about 40 common UK-friendly hustles, 30-day launch plan steps and
scam explanations. General information only, never a promise of income; costs and times are rough typical ranges."""

# id, name, category, start cost low, start cost high (GBP), days to first pound (typical), least hours a week,
# skills, main risk, UK note
IDEAS = [
    ("declutter", "Selling your own unused things", "selling", 0, 20, 3, 2, ("organising", "selling"),
     "One-off: it runs out when the clutter does.", "Selling your own used belongings is usually not trading, but check GOV.UK."),
    ("reselling", "Reselling on Vinted or eBay", "selling", 0, 150, 7, 4, ("selling", "research", "photography"),
     "Fees, slow sellers and cash tied up in stock.", "Regular buying to resell can count as trading; check the rules."),
    ("carboot", "Car boot sales and market stalls", "selling", 10, 100, 14, 5, ("selling", "organising"),
     "Pitch fees, weather and low margins.", "Some markets need a trader licence or insurance."),
    ("upcycling", "Upcycling and selling furniture", "selling", 50, 300, 21, 6, ("diy", "crafts", "practical"),
     "Needs storage space, and each piece takes hours.", "Check fire safety labelling rules for upholstered furniture."),
    ("handmade", "Handmade crafts to sell online or at fairs", "selling", 50, 400, 30, 6, ("crafts", "design"),
     "Crowded market; hours are often unpaid once you count them all.", "Children's items have strict safety rules."),
    ("printondemand", "Print-on-demand designs", "online", 0, 50, 45, 4, ("design", "computers"),
     "Very crowded, thin margins, and sales can take months.", "Check you own or licence every image you use."),
    ("baking", "Home baking, cakes and treats", "selling", 50, 300, 14, 6, ("cooking", "baking"),
     "Hygiene and allergen rules; ingredient costs rise.", "Register your food business with your local council; allergen info is required."),
    ("plants", "Growing and selling plants", "selling", 20, 150, 45, 3, ("outdoors", "gardening"),
     "Slow to start and weather dependent.", "Selling some plants and seeds has rules; check GOV.UK."),
    ("cleaning", "Domestic cleaning", "services", 30, 150, 7, 6, ("practical", "organising"),
     "Physical, cancellations, and you need public liability insurance.", "Insurance is strongly advised."),
    ("dogwalking", "Dog walking", "services", 20, 200, 7, 5, ("animals", "outdoors"),
     "Liability if a dog is hurt or lost; weather.", "Insurance is strongly advised; some councils limit dogs per walker."),
    ("petsitting", "Pet sitting and home visits", "services", 20, 200, 10, 4, ("animals", "caring"),
     "Emergencies, keys to strangers' homes, liability.", "Get insurance and written care instructions."),
    ("gardening", "Gardening and lawn care", "services", 100, 500, 7, 6, ("outdoors", "gardening", "practical"),
     "Seasonal and physical; tools cost money.", "Disposing of green waste can need a licensed carrier."),
    ("windows", "Window cleaning", "services", 100, 400, 10, 6, ("practical", "outdoors"),
     "Working at height and steady rounds take time to build.", "Insurance is strongly advised."),
    ("handyman", "Odd jobs and handyman work", "services", 100, 500, 7, 6, ("diy", "practical"),
     "You are liable for poor work.", "Gas and electrical work must be done by registered people."),
    ("valeting", "Mobile car valeting", "services", 100, 400, 10, 6, ("practical", "driving"),
     "Kit and water supply; weather.", "Check where you may wash cars and how you dispose of water."),
    ("decorating", "Painting and decorating", "services", 100, 600, 14, 8, ("diy", "practical"),
     "Physical; quotes that run over cost you.", "Old paint may contain lead; use proper safety steps."),
    ("errands", "Errands and personal assistant tasks", "services", 0, 50, 7, 4, ("organising", "people", "driving"),
     "Low pay per hour unless priced properly.", "Be clear on who insures your car for business use."),
    ("ironing", "Ironing and laundry help", "services", 0, 80, 7, 5, ("practical",),
     "Low hourly rate and bulky work at home.", "Check your household insurance."),
    ("tutoring", "Tutoring", "services", 0, 50, 14, 3, ("teaching", "numbers", "languages"),
     "Seasonal demand; parents may expect a DBS check.", "A DBS check may be expected when you work with children."),
    ("childcare", "Babysitting and childcare", "care", 0, 100, 10, 4, ("caring", "people"),
     "High responsibility.", "Paid regular childcare can need Ofsted registration; check GOV.UK."),
    ("companion", "Companionship and help for older people", "care", 0, 100, 14, 4, ("caring", "people"),
     "Emotional load; you need clear limits on what you do.", "Checks and insurance matter; keep to non-medical help."),
    ("writing", "Freelance writing", "online", 0, 50, 30, 5, ("writing",),
     "Slow to win clients and low starting rates.", "Freelancers usually register as self-employed."),
    ("virtualassistant", "Virtual assistant", "online", 0, 100, 21, 5, ("computers", "organising"),
     "Clients can be slow to pay.", "Freelancers usually register as self-employed."),
    ("socialmedia", "Social media help for small businesses", "online", 0, 100, 30, 5, ("computers", "writing", "design"),
     "Results depend on things you can't control.", "Set out what you will and won't deliver in writing."),
    ("transcription", "Transcription and captioning", "online", 0, 50, 14, 5, ("computers", "writing"),
     "Low pay per hour at the start.", "Keep client material private."),
    ("surveys", "Paid surveys and app testing", "online", 0, 0, 7, 2, ("computers",),
     "Usually a very low hourly rate; many scams copy this idea.", "Never pay to join."),
    ("translation", "Translation", "online", 0, 100, 30, 4, ("languages", "writing"),
     "Needs strong skills in both languages.", "Certified translations have extra rules."),
    ("webdesign", "Simple websites for local businesses", "online", 0, 200, 45, 6, ("computers", "design"),
     "Support requests keep coming after the job.", "Check the terms of any template or image you use."),
    ("bookkeeping", "Bookkeeping for small businesses", "online", 0, 300, 45, 4, ("numbers", "computers"),
     "Mistakes have real consequences, so training and insurance matter.", "Handling client money and tax filings can have rules."),
    ("graphicdesign", "Graphic design", "online", 0, 300, 30, 6, ("design", "computers"),
     "Crowded, and clients can ask for endless changes.", "Agree who owns the finished work."),
    ("photography", "Photography for events or products", "creative", 100, 800, 30, 6, ("photography", "design"),
     "Kit costs and weekend work.", "Get insurance; check licensing for music or venues."),
    ("videoediting", "Video editing for others", "creative", 0, 300, 30, 6, ("computers", "design"),
     "Deadlines and slow computers cost time.", "Keep proof of who owns the footage."),
    ("music", "Music lessons", "creative", 0, 100, 14, 3, ("music", "teaching"),
     "Cancellations; parents may expect a DBS check.", "A DBS check may be expected for children."),
    ("sewing", "Sewing and clothing alterations", "creative", 0, 200, 14, 4, ("crafts", "practical"),
     "Fiddly, so it is hard to price well.", "Check your insurance if customers visit your home."),
    ("delivery", "Food or parcel delivery driving", "local", 0, 200, 7, 8, ("driving",),
     "Fuel, wear and tear, and self-employed means no holiday or sick pay.", "Check your insurance covers delivery work."),
    ("secondjob", "Evening or weekend part-time job", "local", 0, 0, 14, 8, ("people",),
     "Less flexible; the rota decides your hours.", "Your employer's contract may limit second jobs; tax is taken through PAYE."),
    ("mysteryshop", "Mystery shopping", "local", 0, 0, 21, 2, ("people",),
     "Low and uneven pay; scams often copy this idea.", "Never pay to sign up."),
    ("parking", "Renting out a parking space or driveway", "local", 0, 50, 14, 1, (),
     "Your lease, mortgage or insurance may forbid it.", "Check your tenancy or mortgage terms and tax rules."),
    ("spareroom", "Renting a spare room", "local", 100, 500, 21, 1, ("people",),
     "Needs lender or landlord and insurer permission.", "The Rent a Room scheme has a tax-free limit; check GOV.UK."),
    ("hiring", "Renting out tools, cameras or equipment", "local", 0, 100, 14, 2, ("practical",),
     "Damage, loss and insurance gaps.", "Check what your insurance covers when others use your things."),
    ("mealprep", "Meal prep and catering for others", "local", 100, 500, 21, 6, ("cooking",),
     "Hygiene and allergen rules; waste.", "Register your food business with your local council."),
    ("beauty", "Mobile beauty, nails or hair", "local", 200, 800, 21, 6, ("people", "practical"),
     "Needs training, insurance and often a council licence.", "Check local council licensing rules."),
    ("fitness", "Personal training or fitness classes", "local", 300, 1500, 45, 5, ("fitness", "people", "teaching"),
     "Qualification cost and insurance before your first client.", "You need a recognised qualification and insurance."),
]

FIELDS = ("id", "name", "category", "cost_low", "cost_high", "first_pound_days", "hours_min", "skills", "risk", "uk_note")
CATEGORIES = ["selling", "services", "online", "creative", "local", "care"]
SKILL_WORDS = ["organising", "selling", "research", "photography", "diy", "crafts", "practical", "design", "computers",
               "cooking", "baking", "outdoors", "gardening", "animals", "caring", "people", "driving", "teaching",
               "numbers", "languages", "writing", "music", "fitness"]
ALIASES = {"tidy": "organising", "organised": "organising", "sales": "selling", "sell": "selling", "computer": "computers",
           "tech": "computers", "it": "computers", "artistic": "design", "art": "design", "drawing": "design",
           "dogs": "animals", "pets": "animals", "cook": "cooking", "bake": "baking", "garden": "gardening",
           "maths": "numbers", "math": "numbers", "accounts": "numbers", "language": "languages", "spanish": "languages",
           "french": "languages", "write": "writing", "car": "driving", "drive": "driving", "craft": "crafts",
           "sewing": "crafts", "kids": "caring", "children": "caring", "care": "caring", "sport": "fitness",
           "gym": "fitness", "guitar": "music", "piano": "music", "fix": "diy", "repair": "diy", "painting": "diy",
           "photos": "photography", "camera": "photography", "talking": "people", "customer service": "people"}


def all_ideas() -> list[dict]:
    return [dict(zip(FIELDS, row)) for row in IDEAS]


def idea(name: str) -> dict | None:
    key = " ".join(str(name or "").lower().split())
    rows = all_ideas()
    if not key:
        return None
    exact = [r for r in rows if key in (r["id"], r["name"].lower())]
    if exact:
        return exact[0]
    part = [r for r in rows if key in r["name"].lower() or key in r["id"]]
    return part[0] if len(part) == 1 else (part[0] if part and len(key) > 3 else None)


def skills_in(text) -> set[str]:
    if isinstance(text, (list, tuple)):
        text = ", ".join(str(t) for t in text)
    low = str(text or "").lower()
    found = {w for w in SKILL_WORDS if w in low}
    found |= {v for k, v in ALIASES.items() if f" {k} " in f" {low.replace(',', ' ')} "}
    return found


# (day, text) steps every hustle gets, then a few that depend on the category
PLAN_COMMON = [
    (1, "Write one sentence: who you help or what you sell, and why they would pay."),
    (2, "Check the rules: licences, insurance, your tenancy, mortgage or employer's contract, and benefits (GOV.UK)."),
    (3, "Set your budget cap: the most you can afford to lose. Write it down."),
    (4, "List every startup cost and find the cheapest safe way to begin."),
    (5, "Look at 5 similar sellers or providers and note their prices."),
    (6, "Work out your lowest sensible price (cost-plus and target hourly)."),
    (7, "Decide how many hours a week you can protect, and when."),
    (8, "Choose how you'll get paid and where you'll record income and costs; keep receipts."),
    (12, "Ask 3 people for honest feedback on your offer."),
    (14, "Week 2 check: log your hours and costs so far. Still enjoyable? Still affordable?"),
    (15, "Tell 10 people or places that you are open for business."),
    (19, "Log your first enquiry or order."),
    (21, "Deliver your first order, then ask for feedback or a review."),
    (24, "Improve your offer using what you heard."),
    (26, "Follow up with everyone who asked but didn't buy."),
    (28, "Log all your hours and money and work out your real hourly rate."),
    (30, "Do the monthly review: keep going, change something, or stop."),
]
PLAN_BY_CATEGORY = {
    "selling": [(9, "Photograph and list your first 10 items."), (10, "Price each item after fees and postage.")],
    "services": [(9, "Write a simple price list and what is included."), (10, "Sort insurance and how you'll handle cancellations.")],
    "online": [(9, "Set up a simple profile or page with proof of your skill."), (10, "Make one free sample piece of work.")],
    "creative": [(9, "Make 3 pieces for a small portfolio."), (10, "Set out who owns the finished work.")],
    "local": [(9, "Post in 2 local groups or on a noticeboard."), (10, "Check insurance for working with the public.")],
    "care": [(9, "Check checks and insurance you'll need (for example DBS)."), (10, "Write down clear limits on what you will and won't do.")],
}

SCAMS = {
    "mlm": ("MLM or pyramid scheme", "You pay to join, buy stock, then earn mainly by recruiting others.",
            ["Most of the income comes from signing up new people, not selling to real customers.",
             "You are asked to buy a starter kit or monthly stock.",
             "Earnings claims are shown without the costs and the average member's result."],
            "Ask for the official average income and the total costs. If most members lose money, walk away."),
    "upfront": ("Upfront-fee scheme", "You are asked to pay before you can earn: a kit, training, registration, or a deposit.",
                ["Real employers don't charge you to start a job.", "The fee is small at first, then more fees appear.",
                 "There is pressure to pay quickly."],
                "Never pay to get work. Check the company on Companies House and search its name with the word scam."),
    "crypto": ("Crypto giveaway or doubling", "Someone says send crypto and get double back, often using a famous face.",
               ["Nobody gives away free money.", "The account or video is a fake of a real person.",
                "Crypto can't be reversed once it's sent."],
               "Never send crypto to 'double' it. Report the account to the platform."),
    "cheque": ("Overpayment and fake cheque", "A buyer pays too much and asks you to send the difference back.",
               ["The first payment later fails or bounces.", "You lose the money you sent back plus the item.",
                "The buyer is in a hurry."],
               "Only refund once the money is really in your account, not merely showing as pending."),
    "task": ("Task or 'like and boost' job scam", "A message offers pay for liking videos or boosting products, then asks you to deposit money.",
             ["It arrives unasked on WhatsApp or Telegram.", "Early small payments build trust, then the deposits get bigger.",
              "You can't withdraw without paying more."],
             "Delete and block. Real jobs never ask you to deposit money."),
    "trading": ("Trading bots, signals and 'guaranteed' investing", "A system promises steady profit from forex, crypto or an AI trading bot.",
                ["No one can guarantee returns.", "Screenshots of profits are easy to fake.", "Withdrawals are delayed or blocked."],
                "Check the firm on the Financial Conduct Authority register. If it isn't listed, don't pay."),
    "course": ("Get-rich course or dropshipping coaching", "An expensive course or coach promises a business in a few weeks.",
               ["The sales page shows lifestyle, not the average customer's results.", "There are countdown timers and 'last places'.",
                "Refund terms are hard to find."],
               "Search for independent reviews (not the seller's) and check the refund policy first. Free information covers the basics."),
}

FLAG_RULES = [
    (r"guarantee|risk[- ]free|no risk|can'?t lose|100% (?:safe|profit)", 3, "Guaranteed or risk-free income",
     "Real income is never guaranteed. Anyone promising it is selling something."),
    (r"passive income|easy money|make £?\d[\d,]* (?:a|per) (?:day|week)|£\d[\d,]* (?:a|per) (?:day|week)|while you sleep|little effort", 3,
     "Big earnings for little effort", "Real side hustles take time and skills, and earn less at the start."),
    (r"starter kit|registration fee|join(?:ing)? fee|training fee|admin fee|buy[- ]in|small fee|pay (?:a|the) fee|deposit|activation fee", 4,
     "You pay before you earn", "Real employers don't charge you to work for them."),
    (r"recruit|downline|build your team|invite (?:your )?friends|referral bonus|sign up (?:others|friends)|multi[- ]?level|network marketing", 3,
     "Income depends on recruiting people", "This is how MLM and pyramid schemes work. Most people lose money."),
    (r"(?:bitcoin|crypto|btc|eth|usdt).{0,40}(?:giveaway|double|send)|(?:giveaway|double|send).{0,40}(?:bitcoin|crypto|btc|eth|usdt)", 5,
     "Crypto giveaway or doubling", "Free crypto giveaways are fake. Sent crypto can't be recovered."),
    (r"act now|limited (?:spots|places)|today only|last chance|hurry|expires", 2, "Pressure to hurry",
     "Scammers rush you so you don't check. A genuine offer will still be there tomorrow."),
    (r"don'?t tell|secret method|secret system|insider", 2, "Secrecy", "A 'secret' method is a sales line."),
    (r"gift ?cards?|western union|moneygram|bank transfer only|crypto only|cash ?app", 4, "Odd payment method",
     "Untraceable payment methods are the scammer's favourite. Card or PayPal payments have protection."),
    (r"send (?:back )?the (?:difference|balance)|overpa(?:id|yment)|cheque", 4, "Overpayment or cheque request",
     "This is the fake cheque trick; the cheque bounces later and you lose the money you sent."),
    (r"whatsapp|telegram", 1, "Contact on WhatsApp or Telegram", "Unasked job offers on chat apps are very often scams."),
    (r"like (?:videos?|posts?)|boost (?:products?|ratings?)|complete (?:daily )?tasks|task commission", 4, "Task scam wording",
     "Paid 'tasks' that later ask you to deposit money are a well-known scam."),
    (r"forex|trading (?:bot|signals?)|ai trading|copy trad", 3, "Trading bot or signals",
     "Nobody can guarantee trading profits; check the firm on the FCA register."),
    (r"buy (?:your )?(?:stock|inventory|products) from us|purchase (?:your )?(?:stock|inventory)", 3, "You must buy stock from them",
     "Being tied to buying from the organiser is a warning sign."),
    (r"no experience|no skills|anyone can|anybody can", 1, "'Anyone can do it'", "Real work that pays well usually needs some skill."),
    (r"screenshots? of (?:my )?(?:earnings|profits?)|as seen on|testimonials?", 2, "Proof shown as screenshots",
     "Screenshots and testimonials are easy to fake."),
]

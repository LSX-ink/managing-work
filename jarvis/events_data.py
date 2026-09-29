"""Built-in plans for the events abilities: task timelines by kind of event, the UK wedding checklist, kids' party
timelines by age, party bags, food quantities per guest, and the Christmas dinner timetable."""

# (days before the event, task)
PLANS = {
    "party": [
        (56, "Pick the date, guest list and budget"), (49, "Book the venue or clear the house"),
        (42, "Send the invitations"), (28, "Book entertainment or a DJ, order the cake"),
        (21, "Plan the menu and drinks"), (14, "Chase RSVPs and dietary needs"),
        (7, "Confirm numbers with the venue and caterer, buy decorations"), (3, "Shop for food and drink"),
        (1, "Prepare food, chill drinks, set up the room"), (0, "Party day: set up an hour early"),
        (-2, "Send thank-you messages"),
    ],
    "birthday": [
        (42, "Choose a theme and date"), (35, "Send the invitations"), (28, "Order the cake"),
        (14, "Chase RSVPs and allergies"), (7, "Buy the present, cards and balloons"),
        (3, "Shop for food and drink"), (1, "Wrap the present and prepare the food"),
        (0, "Birthday: candles and lighter ready"), (-2, "Send thank-you messages"),
    ],
    "kids": [
        (42, "Pick the date, theme and venue"), (28, "Send the invitations with an RSVP date"),
        (21, "Order the cake and book any entertainer"), (14, "Chase RSVPs, allergies and lifts"),
        (10, "Buy party bag fillers and decorations"), (5, "Plan the games and prizes"),
        (3, "Shop for party food"), (1, "Make the party bags and prepare food"),
        (0, "Party day: set up, then a first aider and a spare adult"), (-2, "Send thank-you notes"),
    ],
    "wedding": [
        (365, "Set the date and total budget"), (365, "Book the ceremony and reception venues"),
        (330, "Book the photographer, caterer and band or DJ"), (300, "Choose the wedding party and send save-the-dates"),
        (240, "Order the dress, suits and outfits"), (180, "Book the officiant or registrar and the honeymoon"),
        (150, "Send the invitations"), (120, "Order the cake and flowers"), (90, "Plan the ceremony and readings"),
        (60, "Chase RSVPs and plan the seating"),
        (56, "Give notice of marriage at your local register office (at least 29 days before; earlier is safer)"),
        (42, "Final dress and suit fittings, buy rings"), (30, "Confirm every supplier and pay balances"),
        (14, "Give final numbers to the venue and caterer"), (7, "Rehearsal, speeches ready, pack for the honeymoon"),
        (1, "Rings, paperwork and outfits laid out"), (0, "Wedding day"),
        (-14, "Send thank-you cards"),
    ],
    "christmas": [
        (84, "Set the gift budget and make the present list"), (60, "Order the turkey or nut roast from the butcher"),
        (49, "Book Christmas travel and childcare"), (42, "Buy presents early and watch the sales"),
        (28, "Write and post the Christmas cards"), (21, "Order the food shop slot and drinks"),
        (14, "Wrap the presents and post the far-away ones"), (10, "Plan the Christmas dinner and the menu"),
        (5, "Buy the fresh veg and clear space in the fridge"), (2, "Take the turkey out to defrost if frozen"),
        (1, "Peel the veg, set the table and hang stockings"), (0, "Christmas Day"),
        (-3, "Write the thank-you messages"),
    ],
    "gathering": [
        (14, "Pick the date and invite people"), (7, "Chase replies and plan the food"),
        (3, "Shop for food and drink"), (1, "Tidy up and prepare the food"), (0, "Gathering day"),
    ],
    "holiday": [
        (28, "Plan the days and book anything popular"), (14, "Buy the food and decorations"),
        (7, "Confirm who is coming"), (1, "Prepare and tidy up"), (0, "The day itself"),
    ],
}

SETUP = ["Chairs and tables out", "Decorations up", "Balloons blown up", "Music and speaker tested", "Food laid out",
         "Drinks in the fridge", "Ice in the freezer", "Cups, plates and napkins", "Bin bags and cleaning kit",
         "Camera or phone charged", "Coats and bags space", "Name cards and place cards"]

# (oldest age in the band, title, ideas)
KIDS = [
    (2, "Under 3s", ["Keep it to 1.5 hours with parents staying", "Soft play or bubbles", "Simple snacks and juice",
                     "Singing and a short story", "Cake at the start"]),
    (5, "3 to 5", ["Party lasts 2 hours", "Musical statues and pass the parcel", "Face painting or a small entertainer",
                   "Sandwiches, fruit and a cake", "Party bags at the door"]),
    (8, "6 to 8", ["Party lasts 2 hours", "Treasure hunt, disco or sports games", "Craft activity",
                   "Pizza or a hot food choice", "Cake, then party bags"]),
    (12, "9 to 12", ["Party lasts 2 to 3 hours", "Escape room, bowling, cinema or a sleepover",
                     "Karaoke or a games tournament", "Pizza and snacks", "Cake and a photo"]),
    (99, "Teenagers", ["Let them shape the plan", "Music, food and space to chat", "A film or gaming tournament",
                       "Agree a finish time with the parents", "Keep adults in the background"]),
]
# (minutes after the start, step) for a two hour party
KIDS_STEPS = [(0, "Guests arrive, free play"), (15, "Organised games"), (45, "Party food"), (70, "Cake and singing"),
              (85, "Last game or activity"), (110, "Party bags and home time")]
BAGS = ["Party bag (paper, not plastic)", "Sweets or a small chocolate", "Bubbles", "Stickers",
        "Small notebook or pencil", "Bouncy ball or small toy", "Slice of cake in a napkin",
        "Thank-you note with the child's name", "Balloon to take home"]

# (item, amount per adult guest, unit)
FOOD = [("Sandwiches", 3, "rounds"), ("Sausage rolls or pastry bites", 3, "pieces"), ("Crisps and nibbles", 40, "g"),
        ("Cake", 1, "slices"), ("Fruit and veg sticks", 60, "g"), ("Soft drinks", 0.5, "litres"),
        ("Wine", 3, "glasses"), ("Beer or cider", 2, "bottles"), ("Tea and coffee", 2, "cups"), ("Ice", 0.5, "kg")]
# Children eat and drink less; these replace the adult amounts
KIDS_FOOD = {"Sandwiches": 2, "Sausage rolls or pastry bites": 2, "Crisps and nibbles": 30, "Soft drinks": 0.4,
             "Wine": 0, "Beer or cider": 0, "Tea and coffee": 0, "Ice": 0.2}

# Christmas dinner: (minutes relative to serving, step) (the turkey's own steps are worked out from its weight)
XMAS = [(-150, "Peel the potatoes and parsnips"), (-90, "Roast potatoes into hot fat"),
        (-65, "Parsnips and stuffing in; oven up to 220 C"), (-45, "Pigs in blankets in"),
        (-30, "Boil sprouts and carrots; make the gravy"), (-15, "Warm the plates; bread sauce and cranberry out"),
        (-5, "Carve the turkey; drain the veg"), (0, "Serve Christmas dinner")]

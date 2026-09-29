"""Built-in motoring facts: Highway Code speed limits and stopping distances, dashboard warning lights, low emission
zones, checklists and the theory-test style questions. Static, UK-only, nothing is fetched."""

SPEED_LIMITS = [
    ["Cars and motorbikes", "30", "60", "70", "70"],
    ["Cars towing a caravan or trailer", "30", "50", "60", "60"],
    ["Buses and coaches (up to 12 m)", "30", "50", "60", "70"],
    ["Goods vehicles up to 7.5 tonnes", "30", "50", "60", "70"],
    ["Goods vehicles over 7.5 tonnes", "30", "40", "50", "60"],
]
SPEED_COLUMNS = ["Vehicle", "Built-up area", "Single carriageway", "Dual carriageway", "Motorway"]
SPEED_NOTE = ("Speed limits in mph. Street lights usually mean 30 unless signs say otherwise (20 in many towns, "
              "and 20 is the default in built-up areas of Wales). The national limit applies unless a sign shows "
              "another.")

# speed mph, thinking m, braking m, total m
STOPPING = [(20, 6, 6, 12), (30, 9, 14, 23), (40, 12, 24, 36), (50, 15, 38, 53), (60, 18, 55, 73), (70, 21, 75, 96)]
STOPPING_NOTE = ("Highway Code typical stopping distances in dry conditions with a good driver; allow at least double "
                 "on wet roads and up to ten times on ice. A car is about 4 metres long.")

# name, colour, meaning, what to do
LIGHTS = [
    ("Oil pressure", "red", "Engine oil pressure is too low.", "Stop safely and switch off. Check the oil; do not drive on."),
    ("Engine temperature", "red", "The engine is overheating.", "Stop safely, switch off and let it cool before opening the bonnet or coolant cap."),
    ("Battery / charging", "red", "The battery is not charging.", "Switch off extras and get to a garage soon; the car may die."),
    ("Brake system", "red", "Handbrake on, low brake fluid or a brake fault.", "Check the handbrake is off. If it stays on, do not drive; call for help."),
    ("Airbag", "red", "A fault in the airbag or seat belt system.", "Get it checked; the airbags may not work in a crash."),
    ("Power steering", "red", "The power steering has failed.", "Steering will be heavy. Pull over safely and call for help."),
    ("Engine management", "amber", "A fault in the engine or emissions system.", "Get it checked soon. If it flashes, ease off and stop safely."),
    ("ABS", "amber", "The anti-lock braking system has a fault.", "Normal brakes still work but without ABS. Get it checked."),
    ("Tyre pressure (TPMS)", "amber", "One or more tyres are low.", "Check and inflate all tyres to the right pressure."),
    ("Diesel particulate filter", "amber", "The filter is clogged.", "Drive for 15 to 20 minutes at a steady 40 mph or more; see a garage if it stays on."),
    ("Glow plug (diesel)", "amber", "The diesel engine is warming up, or has a fault if it flashes.", "Wait until it goes out before starting."),
    ("Low fuel", "amber", "You are running low on fuel.", "Refuel soon; about 30 to 50 miles may be left."),
    ("Traction / stability control", "amber", "Flashing: the car is controlling a skid. Steady: a fault or switched off.", "Ease off and drive gently if flashing."),
    ("Washer fluid", "amber", "Screen wash is low.", "Top it up."),
    ("Service due", "amber", "A service or inspection is due.", "Book a service."),
    ("Dipped headlights", "green", "Dipped headlights are on.", "Nothing to do."),
    ("Main beam", "blue", "Main beam headlights are on.", "Dip them for oncoming traffic and when following."),
    ("Fog lights", "green", "Fog lights are on.", "Turn them off when visibility improves."),
    ("Indicators", "green", "An indicator or the hazard lights are flashing.", "Fast flashing can mean a blown bulb."),
]
LIGHT_NOTE = ("Red means stop safely and act now, amber means get it checked soon, green or blue means a system is "
              "on. Your handbook has the exact symbols for your car.")

ZONES = [
    ["London ULEZ", "Every London borough. About 12.50 pounds a day in a car that doesn't meet the standard (roughly "
                    "petrol from 2006, diesel from September 2015). Runs all day, every day except Christmas Day."],
    ["London Congestion Charge", "Central London, 07:00 to 18:00 on weekdays and 12:00 to 18:00 at weekends and bank "
                                 "holidays. Not charged between Christmas Day and New Year's Day."],
    ["Other clean air zones", "Charging zones exist in Birmingham, Bath, Bristol, Bradford, Portsmouth, Sheffield and "
                              "Tyneside. Most charge only older diesels, vans, lorries and buses."],
    ["Scotland's low emission zones", "Glasgow, Edinburgh, Aberdeen and Dundee. Fines rather than daily charges for "
                                      "cars that don't meet the standard."],
    ["Dartford Crossing", "Pay the charge online by midnight the day after crossing."],
    ["Check first", "Prices and rules change, so check tfl.gov.uk or gov.uk for the current ones before you travel."],
]

CHECKLISTS = {
    "breakdown": ("If you break down", [
        "Get off the road if you can: left-hand lane, hard shoulder or a lay-by. Put hazard lights on.",
        "On a motorway, leave by the left-hand door and get everyone up the bank behind the barrier.",
        "Do not stay in the car on a motorway. Keep pets inside or on a lead.",
        "Use the orange emergency phone (it tells the operator exactly where you are) or call your breakdown cover.",
        "Wear a hi-vis if you have one. Never try to fix a fault on a motorway.",
        "If you cannot leave the car, stay in with your seat belt on and hazards flashing, and call 999 if in danger.",
        "Do not put a warning triangle out on a motorway. On other roads, put one at least 45 metres behind if safe.",
        "Have your registration, cover membership number and location ready for the call."]),
    "accident": ("After an accident", [
        "Stop, switch off the engine and put hazard lights on. Do not leave the scene.",
        "Check everyone is safe. Call 999 if anyone is hurt, the road is blocked or there is danger.",
        "Do not admit fault or say sorry for the crash at the scene.",
        "Swap details: names, addresses, phone numbers, registrations, insurers and vehicle makes.",
        "Take photos: the vehicles, the road, road signs, damage and the weather.",
        "Note the time, place and the names of witnesses.",
        "If you damaged property or an unattended car, try to find the owner or leave your details.",
        "Report to the police as soon as possible, and within 24 hours, if anyone was injured or you didn't share details.",
        "Tell your insurer as soon as you can, even if you don't plan to claim."]),
    "winter": ("Winter car kit", [
        "Ice scraper and de-icer", "Warm coat, hat, gloves and boots", "Blanket", "Torch with spare batteries",
        "Jump leads", "Small shovel", "Hi-vis jacket and warning triangle", "Phone charger or power bank",
        "Bottle of water and snacks", "Screen wash that works in freezing weather", "First aid kit",
        "Old mat for traction", "Breakdown cover number"]),
    "roadtrip": ("Road trip packing", [
        "Driving licence and insurance details", "Breakdown cover number", "Phone charger and car mount",
        "Sat nav or offline maps", "Water and snacks", "Sunglasses", "Travel sickness tablets if needed",
        "Wet wipes and tissues", "Bin bag for rubbish", "Playlist or podcasts downloaded",
        "Spare change for parking and tolls", "Emergency kit: torch, first aid, hi-vis",
        "Games or books for children"]),
    "usedcar": ("Used car checklist", [
        "Check the V5C logbook matches the seller and the car's registration and VIN.",
        "Check the MOT history and mileage on gov.uk for free.",
        "Run a history check for finance, theft or write-offs.",
        "Look at the service history and receipts.",
        "View it in daylight and dry weather; check panels, paint match and rust.",
        "Check tyre tread and wear, and that all four tyres match.",
        "Look under the bonnet for leaks; check the oil isn't milky.",
        "Test every switch: windows, lights, wipers, air con and heating.",
        "Test drive: brakes straight, no strange noises, clutch and gears smooth.",
        "Warning lights should come on then go out at start-up.",
        "Ask how many owners and why they are selling. Never pay a deposit before seeing it.",
        "Pay by bank transfer or card for protection, and get a receipt."]),
}

# question, right answer, three wrong ones, explanation
QUESTIONS = [
    ("What is the national speed limit for cars on a single carriageway?", "60 mph", ["50 mph", "70 mph", "40 mph"], "Cars on single carriageways: 60 mph."),
    ("What is the national speed limit for cars on a motorway?", "70 mph", ["60 mph", "80 mph", "50 mph"], "Cars on motorways and dual carriageways: 70 mph."),
    ("What is the typical overall stopping distance at 30 mph?", "23 metres", ["12 metres", "36 metres", "53 metres"], "23 metres, about six car lengths."),
    ("What is the typical overall stopping distance at 70 mph?", "96 metres", ["53 metres", "73 metres", "120 metres"], "96 metres, about 24 car lengths."),
    ("What is the minimum legal tread depth for car tyres?", "1.6 mm", ["1.0 mm", "2.0 mm", "3.0 mm"], "1.6 mm across the central three-quarters of the tyre."),
    ("What does a solid white line along the middle of the road mean?", "Do not cross it unless it is safe and you must", ["Overtake freely", "Slow down", "Give way"], "A solid line means you should not cross it, except to enter a side road or property."),
    ("When may you use your horn?", "To warn other road users of your presence", ["To greet a friend", "To show you are annoyed", "To tell others to hurry"], "Only to warn, never in anger, and not in built-up areas between 11.30 pm and 7 am."),
    ("At a roundabout, who has priority?", "Traffic already on the roundabout, coming from your right", ["Traffic entering", "The largest vehicle", "The fastest driver"], "Give way to traffic from the right unless signs say otherwise."),
    ("What does a red traffic light mean?", "Stop and wait behind the stop line", ["Prepare to go", "Slow down", "Give way"], "Stay stopped until it turns green."),
    ("At a pelican crossing, what does flashing amber mean?", "Give way to pedestrians on the crossing, and go if it is clear", ["Stop", "Speed up", "Sound your horn"], "Give way to anyone still crossing, and proceed if clear."),
    ("What is the minimum following gap on dry roads?", "At least two seconds", ["One second", "Half a second", "Five seconds"], "Two seconds on dry roads, at least double in the wet."),
    ("How much longer might stopping take on wet roads?", "At least double", ["The same", "Half as long", "10 per cent more"], "Allow at least twice the distance."),
    ("When must you use dipped headlights?", "When visibility is seriously reduced, generally under 100 metres", ["Only after midnight", "Only in fog", "Never in daylight"], "Use them in bad visibility, and at night."),
    ("What must you do when a school crossing patrol shows a stop sign?", "Stop", ["Carry on if it is clear", "Slow down and sound the horn", "Flash your lights"], "You must stop."),
    ("What is the drink drive limit in England, Wales and Northern Ireland?", "80 mg of alcohol per 100 ml of blood", ["50 mg", "20 mg", "100 mg"], "80 mg per 100 ml of blood; Scotland's limit is 50 mg. The safest advice is not to drink at all."),
    ("What does a blue circular sign mean?", "A mandatory instruction", ["A warning", "A prohibition", "Information only"], "Blue circles give orders, such as turn left."),
    ("What does a red circular sign mean?", "A prohibition, something you must not do", ["A warning", "Give way", "Information"], "Red circles mean don't, like no entry or speed limits."),
    ("What shape is a give way sign?", "A triangle pointing downwards", ["An octagon", "A circle", "A triangle pointing up"], "An inverted triangle with a red border."),
    ("What shape is a stop sign?", "An octagon", ["A triangle", "A circle", "A diamond"], "Always stop at the line, even if it looks clear."),
    ("On a motorway, which lane is for driving normally?", "The left-hand lane", ["The right-hand lane", "The middle lane", "Any lane"], "Keep left unless overtaking."),
    ("What should you do if you miss your motorway exit?", "Carry on to the next exit", ["Reverse along the hard shoulder", "Stop and turn round", "Cross the central reservation"], "Never reverse or turn round on a motorway."),
    ("An emergency vehicle approaches with blue lights and siren. What should you do?", "Stay calm and let it pass safely", ["Speed up", "Stop suddenly where you are", "Ignore it"], "Pull over safely if you can, without breaking the law."),
    ("Who is responsible for making sure all children under 14 wear seat belts?", "The driver", ["The children", "Their parents only", "Nobody"], "The driver is responsible for passengers under 14."),
    ("Until what age or height must a child use a child car seat?", "Age 12 or 135 cm tall", ["Age 8", "Age 5", "Age 16"], "Whichever comes first: 12th birthday or 135 cm."),
    ("How often does a car need an MOT once it is three years old?", "Every year", ["Every two years", "Every three years", "Only if it fails"], "Annually after the first three years."),
    ("When is the first MOT due on a new car?", "Three years after registration", ["One year", "Two years", "Five years"], "It needs one on the third anniversary of registration."),
    ("What do double yellow lines along the kerb mean?", "No waiting at any time unless signs say otherwise", ["No waiting on weekdays only", "You may park for an hour", "Loading only"], "No waiting; check signs for loading times."),
    ("What does a single yellow line mean?", "There are waiting restrictions; read the nearby sign", ["No waiting ever", "Free parking", "Taxi rank"], "Times are on a nearby plate."),
    ("Before you set off, what should you check about your load?", "That it is secure and does not stick out dangerously", ["That it is heavy", "That it is covered in plastic", "Nothing"], "Loads must be secure."),
    ("What is the safest way to overtake a cyclist?", "Give at least 1.5 metres and pass when safe", ["Pass as close as you can", "Sound the horn", "Stay behind at all times"], "Leave at least 1.5 metres at up to 30 mph, and more at higher speed."),
    ("What does the yellow box junction rule say?", "Don't enter unless your exit is clear, except when turning right and waiting for a gap", ["Stop in the box", "Enter and wait", "Only for buses"], "Do not enter unless your exit road is clear."),
    ("If you feel tired on a long drive, what is best?", "Stop somewhere safe and rest; a short nap helps", ["Open the window and carry on", "Turn the radio up", "Drink coffee only"], "Take a break every two hours and stop if you feel drowsy."),
    ("How long may you drive before a break is recommended?", "About two hours", ["Four hours", "Six hours", "There is no advice"], "A break of at least 15 minutes every two hours."),
    ("What is the penalty for using a handheld phone while driving?", "Six penalty points and a 200 pound fine", ["Three points", "A warning", "Nine points"], "It is illegal, even at traffic lights, and new drivers can lose their licence."),
    ("When is the best time to check tyre pressure?", "When the tyres are cold", ["When they are hot", "After a long motorway drive", "Only when flat"], "Cold readings are the most accurate."),
    ("A pedestrian is waiting at a zebra crossing. You should", "Slow down and be ready to stop", ["Speed up", "Flash your lights to hurry them", "Sound the horn"], "Give way to anyone on the crossing and be ready to stop for those waiting."),
    ("What does a flashing amber light on a motorway signal mean?", "Slow down and be prepared to stop", ["Speed up", "Lane closed to buses", "Toll ahead"], "It warns of a hazard ahead."),
    ("A red cross over a motorway lane means", "Do not use this lane", ["Emergency vehicles only", "Slow down", "Overtaking lane"], "Never drive under a red X."),
    ("What is the minimum age to drive a car in the UK?", "17 (16 with enhanced PIP)", ["16 for everyone", "18", "21"], "You can drive a car at 17, or 16 if you get the enhanced rate PIP mobility component."),
]

"""Built-in words for the active abilities: about 30 exercises with how-to text, stretch routines, kit lists, the
Countryside Code, hill-walking safety and the MET table for calories. Plain text, nothing fetched.
"""

# key: (name, gear, focus, kind, how, common mistake, easier way)
# gear: body, dumbbell or gym. focus: upper, lower, core, cardio or full. kind: reps or time.
EXERCISES = {
    "squat": ("Bodyweight squat", "body", "lower", "reps",
              "Feet shoulder-width apart, toes slightly out. Sit back and down as if into a chair until your thighs are "
              "about parallel, then push through your heels to stand.",
              "Knees caving in or heels lifting.", "Squat to a chair and stand up again."),
    "press-up": ("Press-up", "body", "upper", "reps",
                 "Hands under your shoulders, body in one straight line. Lower your chest to just above the floor, "
                 "elbows about 45 degrees from your sides, then push back up.",
                 "Sagging hips or flared elbows.", "Hands on a wall, table or your knees."),
    "lunge": ("Reverse lunge", "body", "lower", "reps",
              "Stand tall, step one foot back and lower until both knees are about 90 degrees, back knee just off the "
              "floor. Push through the front heel to return. Swap legs.",
              "Front knee shooting past your toes.", "Hold a wall for balance or shorten the step."),
    "glute bridge": ("Glute bridge", "body", "lower", "reps",
                     "Lie on your back, knees bent, feet flat. Squeeze your bottom and lift your hips until your body "
                     "is a straight line from shoulders to knees. Pause, then lower.",
                     "Arching your lower back.", "Smaller lift with a short pause."),
    "plank": ("Plank", "body", "core", "time",
              "Forearms on the floor, elbows under shoulders. Lift into a straight line from head to heels, tummy "
              "tight, breathing steadily.",
              "Hips sagging or piking up.", "Plank from your knees, or hands on a table."),
    "mountain climber": ("Mountain climbers", "body", "cardio", "time",
                         "From a high plank, drive one knee towards your chest then swap quickly, like running "
                         "on the spot with your hands on the floor.",
                         "Bouncing your hips high.", "Slow it down, or hands on a bench."),
    "burpee": ("Burpee", "body", "cardio", "reps",
               "Squat and put your hands down, jump or step your feet back to a plank, do a press-up if you like, "
               "jump or step in, then stand and jump with arms up.",
               "Collapsing your back in the plank.", "Step instead of jumping, and skip the press-up."),
    "jumping jack": ("Jumping jacks", "body", "cardio", "time",
                     "Jump your feet wide while your arms swing overhead, then jump back together. Land softly on "
                     "the balls of your feet.", "Landing flat and stiff.", "Step side to side with arm raises."),
    "high knees": ("High knees", "body", "cardio", "time",
                   "Run on the spot, lifting each knee to about hip height and pumping your arms. Stay tall.",
                   "Leaning back.", "March with high knees."),
    "superman": ("Superman", "body", "core", "reps",
                 "Lie face down, arms forward. Lift your arms, chest and legs a few centimetres, squeeze your back "
                 "and bottom for a second, then lower.", "Cranking your neck up.", "Lift just arms or just legs."),
    "dead bug": ("Dead bug", "body", "core", "reps",
                 "On your back, arms up and knees over hips. Lower the opposite arm and leg towards the floor while "
                 "your lower back stays pressed down, then swap.", "Lower back arching off the floor.",
                 "Move only the legs."),
    "bird dog": ("Bird dog", "body", "core", "reps",
                 "On hands and knees, reach one arm forward and the opposite leg back, hips level. Hold a second, "
                 "return and swap.", "Twisting or sagging.", "Lift just the leg."),
    "chair dip": ("Chair dip", "body", "upper", "reps",
                  "Hands on the edge of a sturdy chair, legs out in front. Bend your elbows straight back to lower "
                  "your bottom towards the floor, then press up.", "Elbows flaring, shoulders shrugging.",
                  "Bend your knees and keep feet close."),
    "wall sit": ("Wall sit", "body", "lower", "time",
                 "Back flat against a wall, slide down until your knees are about 90 degrees and hold, weight in "
                 "your heels.", "Knees past your toes.", "Slide down only part way."),
    "step-up": ("Step-up", "body", "lower", "reps",
                "Step onto a sturdy step or bench with one foot, drive up through that heel to stand, then step "
                "down slowly. Do all reps then swap legs.", "Pushing off the back foot.", "Use a lower step."),
    "bicycle crunch": ("Bicycle crunch", "body", "core", "reps",
                       "On your back, hands lightly behind your head. Bring one elbow towards the opposite knee while "
                       "the other leg straightens, and alternate slowly.", "Pulling on your neck.",
                       "Tap your heels down between reps."),
    "calf raise": ("Calf raise", "body", "lower", "reps",
                   "Stand tall, rise up onto the balls of your feet, pause at the top, then lower slowly. Use a "
                   "wall for balance.", "Bouncing quickly.", "Hold something for support."),
    "goblet squat": ("Goblet squat", "dumbbell", "lower", "reps",
                     "Hold one dumbbell upright against your chest. Squat down between your knees, elbows inside "
                     "your knees, chest tall, then stand.", "Chest dropping forward.", "Use a lighter weight."),
    "dumbbell row": ("Dumbbell row", "dumbbell", "upper", "reps",
                     "One hand and knee on a bench or chair, flat back. Pull the dumbbell to your hip, squeezing your "
                     "shoulder blade, then lower under control. Swap sides.", "Twisting your body to lift.",
                     "Lighter weight, slower pace."),
    "shoulder press": ("Dumbbell shoulder press", "dumbbell", "upper", "reps",
                       "Dumbbells at shoulder height, palms forward. Press overhead until your arms are straight, "
                       "ribs down, then lower.", "Arching your back.", "Do it seated, lighter."),
    "romanian deadlift": ("Romanian deadlift", "dumbbell", "lower", "reps",
                          "Dumbbells in front of your thighs, soft knees. Push your hips back, sliding the weights "
                          "down your legs with a flat back until you feel your hamstrings stretch, then stand.",
                          "Rounding your back.", "Use no weight until the hinge feels easy."),
    "bicep curl": ("Bicep curl", "dumbbell", "upper", "reps",
                   "Elbows tucked by your sides, curl the dumbbells up to your shoulders, then lower slowly.",
                   "Swinging your body.", "Lighter weights."),
    "floor press": ("Dumbbell floor press", "dumbbell", "upper", "reps",
                    "Lie on your back, knees bent, dumbbells above your chest. Lower until your upper arms touch the "
                    "floor, then press back up.", "Flaring elbows wide.", "Lighter weights."),
    "farmer's carry": ("Farmer's carry", "dumbbell", "full", "time",
                       "Hold a heavy dumbbell in each hand at your sides and walk tall with short, steady steps.",
                       "Leaning to one side.", "Carry one lighter weight."),
    "dumbbell swing": ("Dumbbell swing", "dumbbell", "full", "reps",
                       "Hold one dumbbell with both hands. Hinge back, then snap your hips forward so the weight "
                       "swings to chest height. Let it fall back between your legs.",
                       "Lifting with your arms.", "Practise the hip hinge with no weight."),
    "barbell squat": ("Barbell back squat", "gym", "lower", "reps",
                      "Bar across your upper back, feet shoulder-width. Brace your tummy, sit down and back to at "
                      "least parallel, then drive up. Use the safety bars or a spotter.",
                      "Rounding your back or heels lifting.", "Goblet squat first."),
    "deadlift": ("Deadlift", "gym", "lower", "reps",
                 "Bar over mid-foot, hinge down and grip just outside your legs, flat back. Push the floor away "
                 "and stand tall, hips and knees locking together. Lower with control.",
                 "Rounding your back or the bar drifting forward.", "Romanian deadlift with light dumbbells."),
    "bench press": ("Bench press", "gym", "upper", "reps",
                    "Lie with eyes under the bar, feet flat, shoulder blades pinched. Lower the bar to your mid-chest "
                    "and press up. Use a spotter or safety arms.", "Bouncing the bar or lifting your bottom.",
                    "Dumbbell floor press."),
    "lat pulldown": ("Lat pulldown", "gym", "upper", "reps",
                     "Sit with thighs under the pad. Pull the bar to your upper chest, elbows down and back, then "
                     "return slowly.", "Leaning far back and yanking.", "Lighter weight, slower."),
    "leg press": ("Leg press", "gym", "lower", "reps",
                  "Feet shoulder-width on the platform. Lower until your knees are about 90 degrees, then press "
                  "without locking your knees out.", "Bottom lifting off the seat.", "Lighter weight."),
    "cable row": ("Seated cable row", "gym", "upper", "reps",
                  "Sit tall, pull the handle to your tummy, squeezing your shoulder blades together, then extend "
                  "your arms slowly.", "Rocking back and forth.", "Lighter weight."),
    "rowing machine": ("Rowing machine", "gym", "cardio", "time",
                       "Legs first, then lean back, then pull the handle to your ribs. Return in reverse: arms, "
                       "body, legs.", "Pulling with your arms first.", "Slow and steady rhythm."),
}
ALIASES = {"pushup": "press-up", "pushups": "press-up", "push-ups": "press-up", "push-up": "press-up", "push up": "press-up", "press up": "press-up",
           "pressup": "press-up", "squats": "squat", "bodyweight squat": "squat", "lunges": "lunge",
           "reverse lunge": "lunge", "bridge": "glute bridge", "planks": "plank", "burpees": "burpee",
           "jumping jacks": "jumping jack", "star jumps": "jumping jack", "mountain climbers": "mountain climber",
           "dips": "chair dip", "tricep dip": "chair dip", "crunch": "bicycle crunch", "curl": "bicep curl",
           "curls": "bicep curl", "row": "dumbbell row", "rows": "dumbbell row", "overhead press": "shoulder press",
           "press": "shoulder press", "deadlifts": "deadlift", "rdl": "romanian deadlift", "bench": "bench press",
           "back squat": "barbell squat", "squat with barbell": "barbell squat", "pulldown": "lat pulldown",
           "lat pull down": "lat pulldown", "rower": "rowing machine", "rowing": "rowing machine",
           "carry": "farmer's carry", "farmers carry": "farmer's carry", "swing": "dumbbell swing",
           "kettlebell swing": "dumbbell swing", "step ups": "step-up", "step up": "step-up",
           "calf raises": "calf raise", "wall sits": "wall sit", "high knee": "high knees"}
FOCUSES = ["full body", "upper body", "lower body", "core", "cardio"]
FOCUS_KEY = {"full": "full", "full body": "full", "upper": "upper", "upper body": "upper", "lower": "lower",
             "lower body": "lower", "legs": "lower", "core": "core", "abs": "core", "cardio": "cardio", "hiit": "cardio"}
GEARS = ["bodyweight", "dumbbell", "gym"]

STRETCHES = {
    "morning": ("Morning stretch", "Wake the body up gently, about 6 minutes.", [
        ("Neck rolls", "Slowly roll your head in a half circle, ear to shoulder to chest to shoulder.", 30),
        ("Shoulder rolls", "Roll both shoulders backwards in big circles.", 30),
        ("Cat-cow", "On hands and knees, arch and round your back slowly with your breath.", 45),
        ("Standing side bend", "Reach one arm overhead and lean to the other side. Swap halfway.", 40),
        ("Forward fold", "Feet hip-width, soft knees, hang forward and let your arms dangle.", 40),
        ("Hip circles", "Hands on hips, draw slow big circles with your hips, then reverse.", 30),
        ("Reach for the sky", "Rise onto your toes, reach up tall and take a deep breath.", 30)]),
    "after run": ("After-run stretch", "Loosen legs and hips once you've cooled down, about 6 minutes.", [
        ("Standing quad stretch, left", "Hold your left ankle to your bottom, knees together.", 30),
        ("Standing quad stretch, right", "Hold your right ankle to your bottom, knees together.", 30),
        ("Calf stretch, left", "Hands on a wall, left leg back with the heel down.", 30),
        ("Calf stretch, right", "Hands on a wall, right leg back with the heel down.", 30),
        ("Hamstring stretch, left", "Heel forward on the ground, hinge at the hips with a flat back.", 30),
        ("Hamstring stretch, right", "Heel forward on the ground, hinge at the hips with a flat back.", 30),
        ("Hip flexor lunge, left", "Kneel on the left knee, tuck your tailbone and press your hips forward.", 40),
        ("Hip flexor lunge, right", "Kneel on the right knee, tuck your tailbone and press your hips forward.", 40),
        ("Figure-four glute stretch", "Lying down, ankle over the opposite knee, pull that thigh towards you.", 45)]),
    "pre run": ("Pre-run warm-up", "Dynamic moves to warm up before a run, about 5 minutes.", [
        ("Brisk walk or march", "Get your heart rate up gently.", 60),
        ("Leg swings, left", "Hold a wall and swing your left leg forward and back.", 30),
        ("Leg swings, right", "Hold a wall and swing your right leg forward and back.", 30),
        ("Walking lunges", "Long steps, sinking into each lunge with a tall chest.", 45),
        ("Butt kicks", "Jog on the spot, heels flicking up to your bottom.", 30),
        ("High knees", "Light and quick, pumping your arms.", 30),
        ("Ankle bounces", "Small quick hops on the balls of your feet.", 30)]),
    "lower back": ("Lower back relief", "Gentle moves for a stiff back, about 5 minutes. Skip any that hurt.", [
        ("Knees to chest", "Lying on your back, hug both knees in and rock gently.", 40),
        ("Lower back rotation", "Knees bent, drop both knees to one side, then the other.", 40),
        ("Child's pose", "Sit back on your heels, arms stretched forward, breathe into your back.", 45),
        ("Cat-cow", "On hands and knees, arch and round slowly.", 45),
        ("Glute bridge holds", "Lift your hips, hold for a few breaths, lower.", 40),
        ("Seated twist", "Sit tall, turn to one side, then the other.", 40)]),
    "evening": ("Evening wind-down stretch", "Slow stretches before bed, about 5 minutes.", [
        ("Neck stretch", "Ear towards your shoulder, one side then the other.", 40),
        ("Chest opener", "Clasp your hands behind you and lift gently.", 30),
        ("Seated forward fold", "Legs out, reach towards your toes without forcing it.", 45),
        ("Butterfly stretch", "Soles of your feet together, knees relaxing outwards.", 45),
        ("Legs up the wall", "Lie with your legs resting up a wall and breathe slowly.", 90)]),
}
STRETCH_ALIASES = {"morning": "morning", "wake up": "morning", "after run": "after run", "after running": "after run",
                   "post run": "after run", "cool down": "after run", "pre run": "pre run", "before run": "pre run",
                   "warm up": "pre run", "warm-up": "pre run", "lower back": "lower back", "back": "lower back",
                   "evening": "evening", "bed": "evening", "bedtime": "evening", "before bed": "evening",
                   "wind down": "evening"}

KITS = {
    "day walk": ("Day walk kit", [
        "Comfortable walking shoes or boots", "Waterproof jacket", "Water bottle", "Snacks or a packed lunch",
        "Phone, charged", "Sun hat and sun cream", "Small first aid kit and plasters", "Map or offline map",
        "Spare layer such as a fleece", "Bin bag for your rubbish", "Some cash or a card"]),
    "hill walk": ("Hill walking kit", [
        "Walking boots with good grip", "Waterproof jacket and over-trousers", "Warm mid-layer and spare layer",
        "Hat and gloves, even in summer", "Map and compass, and knowing how to use them", "Phone in a waterproof bag",
        "Portable charger", "Head torch with spare batteries", "Whistle", "Emergency bivvy bag or foil blanket",
        "First aid kit", "Two litres of water", "Extra food and energy snacks", "Sun cream and sunglasses",
        "Rucksack with a waterproof liner"]),
    "winter": ("Winter hill kit", [
        "Insulated waterproof jacket", "Warm base layers", "Insulated gloves plus a spare pair", "Warm hat and buff",
        "Boots suited to winter, with crampon compatibility if needed", "Ice axe and crampons for real winter conditions",
        "Map, compass and phone", "Head torch and spare batteries", "Whistle", "Emergency bivvy bag",
        "Hot drink in a flask", "Extra food", "Goggles or sunglasses for snow glare", "Gaiters",
        "Check the avalanche and weather forecast before you go"]),
    "overnight": ("Overnight trip kit", [
        "Tent or shelter and pegs", "Sleeping bag and mat", "Stove, fuel, lighter", "Pan and spork", "Food and snacks",
        "Water bottles and a filter or tablets", "Waterproofs and warm layers", "Spare socks and a dry sleeping top",
        "Map, compass and phone", "Head torch", "Toilet kit and a trowel", "First aid kit", "Whistle",
        "Rucksack liner and dry bags", "Tell someone your route and when to expect you"]),
}
KIT_ALIASES = {"day": "day walk", "walk": "day walk", "hill": "hill walk", "hills": "hill walk", "hike": "hill walk",
               "hiking": "hill walk", "mountain": "hill walk", "winter": "winter", "snow": "winter",
               "overnight": "overnight", "camping": "overnight", "camp": "overnight", "backpacking": "overnight"}

COUNTRYSIDE_CODE = [
    ("Respect everyone", [
        "Be considerate to those living in, working in and enjoying the countryside.",
        "Leave gates and property as you find them.",
        "Follow paths, signs and any local restrictions.",
        "Keep to public rights of way, or to land where you have access."]),
    ("Protect the environment", [
        "Take your litter home. Dropped rubbish is dangerous to wildlife and farm animals.",
        "Don't light fires or barbecues where they are not allowed; they can cause serious damage.",
        "Keep dogs under effective control, on a lead near livestock and on nesting-bird land.",
        "Bag your dog's poo and put it in a bin or take it home.",
        "Care for wildlife, plants and trees, and leave things as you find them."]),
    ("Enjoy the outdoors", [
        "Plan ahead and be prepared for the weather and your route.",
        "Check what's open, and follow local advice and signs.",
        "Take care on roads and near water, cliffs and steep ground.",
        "Give livestock plenty of space, and if cattle charge, let go of the dog and move away calmly."]),
]
COUNTRYSIDE_NOTE = ("This is the England and Wales version in plain words. Scotland has its own Outdoor Access Code "
                    "with a right to roam responsibly on most land, and Northern Ireland has its own rules, so check "
                    "locally.")

HILL_SAFETY = [
    "Check the weather and mountain forecast before you go, and again the morning you set off.",
    "Tell someone your route, when you expect to be back, and when to call for help.",
    "Choose a route that suits the least experienced person, and allow extra time.",
    "Carry a map and compass and know how to use them; a phone battery can die.",
    "Wear proper footwear and pack waterproofs, warm layers, food, water and a torch.",
    "Know your turn-around time and stick to it, even if the summit is close.",
    "Stay together as a group and go at the pace of the slowest.",
    "If the weather closes in or you feel unwell, turn back early.",
    "In an emergency: dial 999, ask for Police, then Mountain Rescue. Give your location and stay put.",
    "Distress signal: six blasts on a whistle or six flashes of a torch in a minute, then wait a minute and repeat.",
    "Stay warm if you have to wait: put on layers, get in a bivvy bag and shelter from the wind.",
    "Leave no trace: take rubbish home and leave gates as you found them.",
]

MET = {
    "walking slowly": 2.8, "walking briskly": 4.3, "walking uphill": 6.0, "hiking": 6.0, "nordic walking": 4.8,
    "running 8 km/h": 8.3, "running 10 km/h": 9.8, "running 12 km/h": 11.8, "running 14 km/h": 12.8,
    "cycling leisurely": 4.0, "cycling moderately": 8.0, "cycling fast": 10.0, "mountain biking": 8.5,
    "swimming": 7.0, "rowing machine": 7.0, "elliptical": 5.0, "weight training": 3.5, "circuit training": 8.0,
    "hiit": 8.0, "yoga": 2.5, "pilates": 3.0, "dancing": 5.0, "football": 7.0, "tennis": 7.3, "gardening": 3.8,
}
MET_ALIASES = {"walk": "walking briskly", "walking": "walking briskly", "brisk walk": "walking briskly",
               "run": "running 10 km/h", "running": "running 10 km/h", "jog": "running 8 km/h",
               "jogging": "running 8 km/h", "cycle": "cycling moderately", "cycling": "cycling moderately",
               "bike": "cycling moderately", "cycle ride": "cycling moderately", "hike": "hiking",
               "weights": "weight training", "gym": "weight training", "strength": "weight training",
               "row": "rowing machine", "rowing": "rowing machine", "swim": "swimming", "circuit": "circuit training",
               "hill walk": "walking uphill", "hill walking": "walking uphill", "tabata": "hiit",
               "soccer": "football", "dance": "dancing"}

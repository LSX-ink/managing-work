"""Words for the calm abilities: breathing patterns, guided scripts, quick calm-down ideas, affirmations, kindness ideas
and the default wind-down routine. Plain, kind and everyday; none of it is medical advice.
"""

# name -> (title, [(phase, seconds)], blurb)
BREATHING = {
    "box": ("Box breathing", [("Breathe in", 4), ("Hold", 4), ("Breathe out", 4), ("Hold", 4)],
            "In, hold, out, hold, four seconds each."),
    "478": ("4-7-8 breathing", [("Breathe in", 4), ("Hold", 7), ("Breathe out", 8)],
            "In for 4, hold for 7, out slowly for 8. Often used to wind down before sleep."),
    "coherent": ("Coherent breathing", [("Breathe in", 5.5), ("Breathe out", 5.5)],
                 "Slow and even, about five and a half seconds in and out."),
    "sigh": ("Physiological sigh", [("Big breath in through the nose", 3), ("Second small sip in", 1),
                                    ("Long slow sigh out", 6)],
             "Two breaths in, one long sigh out. A quick reset when you feel wound up."),
}
BREATHING_ALIASES = {"4-7-8": "478", "478": "478", "box": "box", "square": "box", "coherent": "coherent",
                     "5.5": "coherent", "resonant": "coherent", "sigh": "sigh", "physiological sigh": "sigh",
                     "physiological": "sigh"}

# name -> (title, [(step text, seconds to pause)])
GUIDES = {
    "body_scan": ("Body scan", [
        ("Get comfortable, sitting or lying down. Let your eyes close if you like.", 10),
        ("Take a slow breath in, and let it go.", 8),
        ("Bring your attention to your feet. Notice anything there: warmth, pressure, tingling, or nothing at all.", 15),
        ("Move up to your legs, your calves, knees and thighs. Let them feel heavy.", 15),
        ("Notice your hips and lower back. Let the surface hold your weight.", 15),
        ("Bring your attention to your belly. Feel it rise and fall with each breath.", 15),
        ("Notice your chest and your shoulders. Let your shoulders drop away from your ears.", 15),
        ("Move down your arms to your hands. Let your fingers be soft.", 15),
        ("Notice your neck, your jaw and your face. Unclench your teeth, soften your forehead.", 15),
        ("Feel your whole body resting here, breathing quietly.", 12),
        ("When you're ready, wiggle your fingers and toes, and gently open your eyes.", 6)]),
    "grounding": ("5-4-3-2-1 grounding", [
        ("Take one slow breath. We'll use your senses to come back to this moment.", 8),
        ("Look around and name five things you can see.", 20),
        ("Now notice four things you can feel: your feet on the floor, your clothes, the air on your skin.", 20),
        ("Listen for three things you can hear, near or far.", 15),
        ("Find two things you can smell, or two smells you like.", 12),
        ("Notice one thing you can taste.", 10),
        ("Take a last slow breath in and out. You are here, and you are safe right now.", 8)]),
    "loving_kindness": ("Loving-kindness", [
        ("Settle in and take a few easy breaths.", 10),
        ("Picture yourself. Silently say: May I be happy. May I be well. May I be at peace.", 20),
        ("Now picture someone you love. Say: May you be happy. May you be well. May you be at peace.", 20),
        ("Picture someone neutral, like a neighbour or a shopkeeper. Wish them the same.", 20),
        ("If you feel able, picture someone you find difficult. Wish them peace too.", 20),
        ("Now widen out to everyone, everywhere. May all beings be happy and at peace.", 20),
        ("Take a breath, and come back to the room.", 6)]),
    "muscle_relaxation": ("Progressive muscle relaxation", [
        ("Sit or lie comfortably. We'll tense each part for five seconds, then let go.", 8),
        ("Hands: make tight fists. Hold. Now release and feel the difference.", 12),
        ("Arms: bend your elbows and tense your upper arms. Hold. Release.", 12),
        ("Shoulders: shrug them up to your ears. Hold. Let them drop.", 12),
        ("Face: scrunch it up tight. Hold. Release and let your face go soft.", 12),
        ("Stomach: tighten your tummy muscles. Hold. Release.", 12),
        ("Legs: press your thighs together and tense them. Hold. Release.", 12),
        ("Feet: curl your toes. Hold. Release.", 12),
        ("Let your whole body feel loose and heavy. Breathe slowly.", 12)]),
    "wind_down": ("Sleepy wind-down", [
        ("Lie back and let the bed hold you. Nothing to do now.", 10),
        ("Breathe in slowly, and let a long breath out, like fogging a window.", 12),
        ("Let go of the day. Whatever is unfinished can wait until tomorrow.", 12),
        ("Think of one good thing from today, however small.", 15),
        ("Soften your face, your jaw, your shoulders, your hands.", 15),
        ("Picture somewhere calm and safe. Stay there and keep breathing slowly.", 25),
        ("Goodnight. Let sleep come when it comes.", 8)]),
}
GUIDE_ALIASES = {"body scan": "body_scan", "bodyscan": "body_scan", "scan": "body_scan", "grounding": "grounding",
                 "5-4-3-2-1": "grounding", "54321": "grounding", "loving kindness": "loving_kindness",
                 "metta": "loving_kindness", "loving-kindness": "loving_kindness", "muscle": "muscle_relaxation",
                 "pmr": "muscle_relaxation", "progressive muscle relaxation": "muscle_relaxation",
                 "muscle relaxation": "muscle_relaxation", "wind down": "wind_down", "sleep": "wind_down"}

CALM_MENU = {
    "anxious": ["Try the physiological sigh: two breaths in, one long breath out.",
                "Name five things you can see, four you can feel, three you can hear.",
                "Splash cool water on your face or hold something cold.",
                "Write the worry on your worry list and set it aside until worry time.",
                "Put your feet flat on the floor and press down. Feel the ground."],
    "angry": ["Step away for five minutes if you can.", "Breathe out for longer than you breathe in.",
              "Squeeze your fists hard for five seconds, then let go.", "Walk briskly around the block.",
              "Write it down, then screw the paper up. You don't have to send anything."],
    "overwhelmed": ["Pick just one thing and do only that.",
                    "Brain-dump everything onto a list, then pick the smallest task.",
                    "Drink a glass of water and open a window.", "Do three rounds of box breathing.",
                    "Tell someone you trust that you've got a lot on."],
    "restless": ["Stretch your arms overhead and roll your shoulders.", "Go outside for ten minutes.",
                 "Put on one song and move to it.", "Do a body scan, starting at the feet.",
                 "Tidy one small surface."],
    "sad": ["Be kind to yourself. It's okay to feel this.", "Wrap up in a blanket with a warm drink.",
            "Message someone who makes you smile.", "Step outside and look at the sky for a minute.",
            "Write down one thing that went okay today."],
    "tired": ["Have a glass of water.", "Take a ten minute rest without your phone.",
              "Open a window and take five deep breaths.", "Step outside for daylight if you can.",
              "Be gentle: what's the one thing that really needs doing today?"],
    "lonely": ["Send a message to someone you haven't spoken to for a while.",
               "Go somewhere with people around: a cafe or a park.",
               "Listen to a podcast or radio show with voices you like.", "Do something kind for someone else.",
               "Remember it's a feeling, and it will pass."],
}
FEELING_ALIASES = {"anxiety": "anxious", "nervous": "anxious", "stressed": "overwhelmed", "stress": "overwhelmed",
                   "panicky": "anxious", "worried": "anxious", "annoyed": "angry", "frustrated": "angry",
                   "fidgety": "restless", "low": "sad", "down": "sad", "exhausted": "tired", "alone": "lonely"}

AFFIRMATIONS = [
    "I am doing the best I can, and that is enough.", "I can take this one step at a time.",
    "I am allowed to rest.", "My feelings are welcome here, and they will pass.",
    "I am learning and growing every day.", "I choose to be kind to myself today.",
    "I have handled hard days before, and I can handle this one.", "I don't have to be perfect to be worthy.",
    "I am allowed to say no.", "Small steps still count.", "I let go of what I can't control.",
    "I deserve peace and I deserve joy.", "I breathe in calm and breathe out tension.",
    "Today, I will focus on what I can do.", "I am grateful for the small good things around me.",
    "It's okay to ask for help.", "I trust myself to work things out.", "This moment is enough.",
    "I am more than my to-do list.", "I give myself permission to start again.", "I can be gentle and strong at once.",
    "I am worthy of care, including my own.", "I welcome a slower pace.", "Progress, not perfection.",
    "I release comparison and celebrate my own path.", "I am safe in this moment.",
    "Every breath is a fresh start.", "I make room for things that matter to me.",
    "I forgive myself for what I didn't know then.", "I'm allowed to enjoy today.",
]

KINDNESS = [
    "Send a message to someone you haven't spoken to in a while.", "Give someone a genuine compliment today.",
    "Hold a door open and smile.", "Leave a kind review for a small local business.",
    "Make someone a cup of tea without being asked.", "Thank someone who normally goes unthanked.",
    "Let someone go ahead of you in the queue.", "Donate something you no longer need to a charity shop.",
    "Write a short thank-you note to a friend.", "Ask a neighbour how they are, and really listen.",
    "Tell someone what you like about them.", "Pick up a bit of litter on your walk.",
    "Forgive a small thing that has been bothering you.", "Text a friend who has a big day coming up.",
    "Cook a little extra and share it.", "Give a big smile to the next person you meet.",
    "Offer to help someone carry something.", "Be patient with someone who is testing your patience.",
    "Send a family member a happy memory or a photo.", "Be kind to yourself: do one thing you enjoy.",
    "Call a relative for a five minute chat.", "Say thank you to a delivery driver or bus driver.",
    "Share something useful you learned this week.", "Check in on someone who's been having a rough time.",
    "Leave a treat for the next person at work.", "Let a driver out at a junction.",
    "Write down three things you appreciate about someone and tell them one.",
    "Give your full attention to someone during a conversation.", "Bring a friend a treat.",
    "Say sorry for something, if it's been on your mind.",
]

WINDDOWN = ["Put your phone on charge, away from the bed", "Tidy up for five minutes", "Set out clothes for tomorrow",
            "Write tomorrow's top three tasks", "Dim the lights", "Warm drink, no caffeine", "Wash face and brush teeth",
            "Read a few pages of a book", "Five minutes of breathing or stretching"]

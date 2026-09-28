"""Fixed text for conversation modes: how Alfred behaves in each mode, interview questions, debate motions,
language topics, role-play scenarios, filler words and the rubber duck checklist."""

STAY = ("Stay in this mode on every reply until the user says stop, normal mode or picks another mode. "
        "Keep speaking plainly: everything you say is read aloud. ")

# key -> (label, one-line summary for the badge, instructions)
MODES = {
    "tutor": ("Tutor", "Teaching step by step",
              "Be a patient tutor. Explain one idea at a time, check understanding with a short question, and "
              "build up from what the user already knows."),
    "coach": ("Coach", "Goals, next steps, encouragement",
              "Be a supportive life and performance coach. Ask open questions, help the user name a goal and a "
              "small next step, and reflect back what you hear. Don't lecture."),
    "debate": ("Debate partner", "Arguing the other side",
               "Be a sharp, fair debate partner. Take the opposite side to the user, make one clear argument per "
               "turn, rebut their points, and never get personal."),
    "interviewer": ("Interviewer", "Job interview practice",
                    "Be a professional but friendly job interviewer. Ask one question at a time, listen to the "
                    "whole answer, then give brief, specific feedback before the next question."),
    "language": ("Language partner", "Conversation practice",
                 "Be a language conversation partner. Speak mostly in the language being practised at the "
                 "user's level, gently correct mistakes by repeating the right form, and keep the chat flowing."),
    "storyteller": ("Storyteller", "Telling a story together",
                    "Be a vivid storyteller. Tell the story in short spoken chunks, pause at choices and ask the "
                    "user what happens next, and keep characters consistent."),
    "quiz": ("Quiz master", "Asking quiz questions",
             "Be an upbeat quiz master. Ask one question at a time, wait for the answer, say if it's right and "
             "give the answer if not, then mark it with the learning_session quiz_mark action."),
    "brainstorm": ("Brainstorm", "Generating ideas together",
                   "Be an energetic brainstorm partner. Build on the user's ideas, offer bold new ones, don't "
                   "judge yet, and save every idea worth keeping with debate_and_ideas idea_add."),
    "rubber_duck": ("Rubber duck", "Talking through code",
                    "Be a rubber duck for debugging. Mostly listen. Ask the user to explain what the code should "
                    "do, what it actually does, and walk through it line by line. Ask short questions; only "
                    "suggest a fix if they ask."),
    "listener": ("Calm listener", "Listening, supportive",
                 "Be a calm, supportive listener. Let the user talk, reflect feelings back warmly, don't rush to "
                 "fix things or give advice unless asked, and keep your voice gentle and brief. If they mention "
                 "being in danger or wanting to harm themselves, kindly suggest calling 999 or Samaritans on 116 123."),
    "devils_advocate": ("Devil's advocate", "Challenging every idea",
                        "Play devil's advocate. Politely challenge whatever the user proposes with the strongest "
                        "counter-arguments and awkward questions, so they can test their thinking."),
    "eli5": ("Explain simply", "Explaining like you're five",
             "Explain everything as if to a curious five-year-old: short words, everyday comparisons, no jargon."),
    "concise": ("Concise", "Short answers only",
                "Answer in as few words as possible, one short sentence at most, unless asked for more."),
    "chatty": ("Chatty", "Relaxed and talkative",
               "Be relaxed and chatty: longer, warmer replies, share opinions and small asides, and ask the user "
               "about themselves."),
}

STAR = ("STAR method for behavioural answers:\n"
        "S - Situation: set the scene in a sentence or two.\n"
        "T - Task: what you had to achieve.\n"
        "A - Action: what you did, step by step (say I, not we).\n"
        "R - Result: what happened, with a number if you can, and what you learned.")

QUESTION_TYPES = ("behavioural", "strengths", "situational", "technical")

INTERVIEW_QUESTIONS = {
    "behavioural": [
        "Tell me about a time you solved a difficult problem at work.",
        "Describe a time you disagreed with a colleague. How did you handle it?",
        "Tell me about a time you made a mistake. What did you do?",
        "Give an example of when you worked well under pressure.",
        "Tell me about a time you led a team or a project.",
        "Describe a time you had to meet a tight deadline.",
        "Tell me about a time you went above and beyond for a customer.",
        "Give an example of when you had to learn something quickly.",
        "Tell me about a time you received criticism. How did you respond?",
        "Describe a time you persuaded someone to see things your way.",
        "Tell me about a time you failed to reach a goal.",
        "Give an example of how you dealt with a difficult customer or client.",
        "Tell me about a time you improved a process.",
        "Describe a time you had to juggle several priorities.",
        "Tell me about a time you helped a struggling teammate.",
    ],
    "strengths": [
        "Tell me about yourself.",
        "What are your greatest strengths?",
        "What is your biggest weakness?",
        "Why do you want this job?",
        "Why should we hire you?",
        "What motivates you at work?",
        "What would your last manager say about you?",
        "What achievement are you proudest of?",
        "Where do you see yourself in five years?",
        "What kind of work environment suits you best?",
        "What do you know about our company?",
        "Why are you leaving your current role?",
        "What do you enjoy doing outside work?",
        "How would your colleagues describe you in three words?",
        "Do you have any questions for us?",
    ],
    "situational": [
        "What would you do if you missed an important deadline?",
        "How would you handle a colleague who wasn't pulling their weight?",
        "What would you do if your manager asked you to do something you thought was wrong?",
        "How would you handle two urgent tasks from two different managers?",
        "What would you do in your first 90 days in this role?",
        "How would you deal with an angry customer on the phone?",
        "What would you do if you noticed a mistake in someone else's work?",
        "How would you respond if a project's requirements changed at the last minute?",
        "What would you do if you disagreed with your team's decision?",
        "How would you approach a task you'd never done before?",
        "What would you do if you were given more work than you could finish?",
        "How would you handle confidential information shared with you by mistake?",
        "What would you do if a teammate took credit for your work?",
        "How would you get up to speed in a new team quickly?",
        "What would you do if a customer asked for something outside company policy?",
    ],
    "technical": [
        "Walk me through how you would plan a project from start to finish.",
        "How do you decide what to prioritise when everything seems important?",
        "How do you check your work for accuracy?",
        "Which tools or software do you use most, and how?",
        "How do you keep your skills up to date?",
        "Explain something technical from your field to someone with no background in it.",
        "How do you measure whether your work was successful?",
        "How do you organise your day and your tasks?",
        "Describe how you would investigate a problem with no obvious cause.",
        "How do you handle data or information you're not sure is correct?",
        "What steps do you take before making an important decision?",
        "How would you document your work so someone else could pick it up?",
        "How do you give and receive feedback on work?",
        "What's a recent development in your field that interests you?",
        "How would you improve a process you found inefficient?",
    ],
}

MOTIONS = [
    "This house would ban homework in primary schools.",
    "This house believes social media does more harm than good.",
    "This house would make voting compulsory.",
    "This house would introduce a four-day working week.",
    "This house believes remote working is better than office working.",
    "This house would ban cars from city centres.",
    "This house believes artificial intelligence will create more jobs than it destroys.",
    "This house would lower the voting age to 16.",
    "This house would make university free for everyone.",
    "This house believes zoos should be abolished.",
    "This house would ban single-use plastics.",
    "This house believes space exploration is worth the cost.",
    "This house would introduce a universal basic income.",
    "This house believes celebrities have a duty to be role models.",
    "This house would ban smartphones in schools.",
    "This house believes video games are good for young people.",
    "This house would tax sugary food more heavily.",
    "This house believes cash should be phased out.",
    "This house would make learning a second language compulsory until 18.",
    "This house believes the monarchy should be abolished.",
    "This house would ban advertising aimed at children.",
    "This house believes professional athletes are overpaid.",
    "This house would make public transport free.",
    "This house believes nuclear power is the answer to climate change.",
    "This house would require everyone to do a year of national service.",
    "This house believes reality TV is harmful.",
    "This house would ban fast food adverts on TV.",
    "This house believes it's better to rent than to buy a home.",
    "This house would give pets legal rights.",
    "This house believes exams are not a good measure of ability.",
    "This house would ban private cars by 2050.",
    "This house believes tourism does more harm than good.",
    "This house would replace school uniforms with free dress.",
    "This house believes billionaires should not exist.",
    "This house would allow self-driving cars on all roads.",
    "This house believes books are better than films.",
    "This house would ban junk food in schools.",
    "This house believes working from home harms team spirit.",
    "This house would make cooking lessons compulsory in schools.",
    "This house believes it is never right to lie.",
]

LEVELS = ("A1", "A2", "B1", "B2", "C1")
LEVEL_NOTES = {
    "A1": "complete beginner: very short sentences, present tense, common words, speak slowly and repeat",
    "A2": "elementary: simple sentences about everyday things, past and future introduced gently",
    "B1": "intermediate: connected sentences, opinions and experiences, some new vocabulary each turn",
    "B2": "upper intermediate: natural speed, idioms now and then, discuss abstract topics",
    "C1": "advanced: native-like conversation, nuance, idioms and tricky grammar",
}
LANGUAGE_TOPICS = {
    "A1": ["Introducing yourself", "Family", "Food and drink", "Numbers and prices", "Days and times",
           "Colours and clothes", "Your home", "Weather"],
    "A2": ["Shopping", "Your daily routine", "Hobbies", "Last weekend", "Directions in town", "At a café",
           "Holidays", "Health and the doctor"],
    "B1": ["Work and jobs", "Travel stories", "Films and books", "Plans for the future", "Technology",
           "Sport", "City versus countryside", "Festivals and traditions"],
    "B2": ["The environment", "Social media", "Education", "News of the week", "Work-life balance",
           "Culture and identity", "Money and saving", "Health and lifestyle"],
    "C1": ["Politics and society", "Ethics of AI", "Art and meaning", "The economy", "Science and discovery",
           "History's turning points", "Language and thought", "Globalisation"],
}

# name -> (Alfred's role, the user's goals, difficulty)
ROLEPLAYS = {
    "Ordering at a restaurant": ("a waiter in a busy restaurant",
                                 "Get a table, ask about a dish, order a meal and a drink, ask for the bill",
                                 "easy"),
    "Returning an item": ("a shop assistant who needs a receipt",
                          "Explain what's wrong, ask for a refund, stay polite if offered only a credit note",
                          "medium"),
    "Asking for a raise": ("the user's manager, friendly but careful with the budget",
                           "Make the case with achievements, name a figure, agree a next step",
                           "hard"),
    "Calling the doctor's surgery": ("a GP surgery receptionist with few appointments left",
                                     "Describe the problem briefly, get an appointment or a call-back, confirm the time",
                                     "medium"),
    "Small talk at a party": ("a friendly stranger at a party",
                              "Introduce yourself, keep the chat going with questions, exit politely",
                              "easy"),
    "Complaining to a landlord": ("a busy landlord who'd rather not spend money",
                                  "Explain the repair, agree a date, keep a record of what's promised",
                                  "hard"),
    "Checking in at a hotel": ("a hotel receptionist",
                               "Check in, ask about breakfast and Wi-Fi, request a quiet room",
                               "easy"),
    "Saying no to extra work": ("a colleague asking for a favour",
                                "Decline politely but firmly, offer an alternative if you want",
                                "medium"),
}

FILLERS = ["um", "uh", "er", "erm", "like", "you know", "basically", "actually", "sort of", "kind of"]

DUCK_CHECKLIST = [
    "Say in one sentence what the code should do.",
    "Say what it actually does, and the exact error message.",
    "Can you make it fail every time? What are the smallest steps?",
    "What changed since it last worked?",
    "Walk through it line by line, out loud.",
    "Check your assumptions: print or log the values you think you know.",
    "Check the inputs: empty, None, wrong type, off by one?",
    "Read the error from the bottom of the stack trace up.",
    "Is the code you're running the code you're editing (saved, rebuilt, right branch)?",
    "Try the simplest possible version, then add back one piece at a time.",
    "Take a five-minute break and explain it again from the start.",
]

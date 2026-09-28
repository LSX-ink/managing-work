# Discover: science, space, codes and learning games

Things to say to Alfred to explore and learn. Most answers pop up a window on the Alfred screen; in
quizzes you can click the answer buttons instead of speaking.

## Science and space
- **Element facts**: "Tell me about the element tungsten." / "What's element 79?" / "What is Fe?"
  A table pops up with the symbol, number, mass, group, period and category, plus buttons for the neighbouring elements.
- **Periodic table**: "Show me the periodic table." A full table of all 118 elements pops up. Click any element and Alfred tells you about it.
- **Planets and moons**: "Tell me about Saturn." / "Tell me about Europa." A fact table pops up, with buttons for the planet's big moons.
- **Compare the planets**: "Compare the planets." A table of all eight planets: size, distance from the Sun, day, year, moons, gravity and temperature.
- **Constellations**: "What constellations can I see this month?" / "What can I see in the sky in December?"
  A list pops up of what's well placed in the evening from the UK, with what to look for. Click one for tips, or ask
  "How do I find Cassiopeia?"
- **Night sky tonight**: "What's in the night sky tonight?" Sunset time, the moon's phase and which bright planets
  are up (evening or morning), in a small table. Sunset uses your home city (`JARVIS_CITY`).
- **Science fact and unit of the day**: "What's today's science fact?" / "What's the unit of the day?" The same fact all day, a new one tomorrow.
- **Compare two countries**: "Compare France and Japan." A side-by-side table: flag, capital, population, area,
  people per km², currency, languages and region.

## Learning games
Each question pops up with answer buttons and your score. After each answer Alfred says whether you were right and asks the next one.
Say "I give up" to hear the answer, "What's my quiz score?" for your scores, or just stop whenever you like.

- **Times tables**: "Test me on my times tables." / "Practise the 7 times table."
- **Spelling bee**: "Let's do a spelling bee." / "Give me a hard spelling bee." Alfred says a word; spell it out loud
  ("N-E-C-E-S-S-A-R-Y") or type it in the box in the pop-up. Levels: easy, medium and hard.
- **Human body quiz**: "Quiz me on the human body."
- **Timeline quiz**: "Give me a timeline quiz." Four historical events pop up; click them from earliest to latest
  (or say "C, A, D, B").
- **Kids' quiz**: "Give me a kids' quiz." Easy questions with big buttons.
- **Quiz scores**: "What's my quiz score?" A table of right answers for each game.

## Vocabulary builder
- **Save a word**: "Add ubiquitous to my vocabulary: it means found everywhere."
- **See your words**: "Show my vocabulary list." A list of your words and meanings pops up.
- **Quiz me**: "Quiz me on my vocabulary." Pick the right meaning from the buttons. Words you get wrong come up more often.
- **Remove a word**: "Remove ubiquitous from my vocabulary." (Alfred checks with you first.)

## Codes and numbers
- **Number facts**: "Tell me about the number 144." / "Is 97 prime?" A table pops up: prime or not, factors, binary,
  hex, square, cube and whether it's a Fibonacci number.
- **Text to Morse code**: "What's SOS in Morse code?" The dots and dashes pop up with a Play button to hear the beeps.
- **Morse code to text**: "What does .... .. mean in Morse?"
- **NATO phonetic alphabet**: "Spell my postcode SW1A 1AA phonetically." (Sierra, Whiskey, One, Alfa...) A list pops up.
- **Braille**: "Show hello in braille." The braille pops up in big dots.

## Study planner
- **Add an exam**: "My maths exam is on the 5th of October."
- **See your exams**: "What exams have I got?" A table with how many days are left.
- **Revision timetable**: "Make me a revision timetable." / "Make me a timetable with 4 sessions a day." A
  day-by-day table pops up until your last exam: nearer exams get more sessions and the day before an exam is for that subject.
- **Remove an exam**: "Remove my history exam." (Alfred checks with you first.)

Your vocabulary is kept in `discover-vocab.json` and your exams in `discover-exams.json` in your memory folder;
quiz scores are in `.discover-quiz.json`. Everything works offline except sunset times (Open-Meteo) and comparing
countries (restcountries.com); only the city or country names are sent.

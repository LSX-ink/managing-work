# Party and game-night host

Alfred can run a family-friendly game night: a quiz with teams, a buzzer, word games, a Secret Santa draw, team
splitting and timers. Everything works offline. Nothing is sent anywhere.

Already covered elsewhere, so not repeated here: trivia questions, would you rather and this or that
([Games and fun](fun.md)), the bingo caller and its board ([Screen games](screen-games.md)), the picker wheel
([Widgets](widgets.md)), the pub quiz league table and the five-a-side team picker ([Sports](sports.md)) and the
party planner and guest list ([Household plus](household-plus.md)).

## Quiz night

The quiz keeps its state in `partyhost-quiz.json`, your own questions in `partyhost-questions.json`, and the questions
already asked in `partyhost-seen.json` so a new night doesn't repeat them.

1. **Start a quiz**: "Start a quiz night with the Reds, the Blues and the Greens, four rounds of five." Optional
   "science and sport rounds". If a quiz with scores is running, Alfred asks before replacing it. Pops up the big scoreboard.
2. **Categories**: "What quiz categories have you got?" A table of ten categories with 150 questions (plus yours).
3. **Next question**: "Next question." A big question screen; Alfred reads it out.
4. **Reveal the answer**: "What's the answer?" The answer appears in a box.
5. **Award points**: "Give the Blues two points." (one point if you don't say). Pops up the scoreboard.
6. **Undo**: "Take that point back." Removes the last award.
7. **Scoreboard**: "Show the scoreboard." Big bars, ranks, and each team's points by round.
8. **Round results**: "Round two results." How each team did in that round.
9. **Finish**: "Final scores." Announces the winner, or a tie.
10. **Your own question**: "Add a quiz question: who snores loudest? Answer: Dad. Category Family." It joins the bank.
11. **Tiebreaker**: "Give us a tiebreaker." A closest-number question; "What's the answer?" reveals it.
12. **Answer sheet**: "Make an answer sheet for the teams." A table with a row per question.
13. **Host's sheet**: "Show me the answer key." Every question with its answer; keep it to yourself.
14. **Buzzer**: "Put up the buzzer for the Reds and the Blues." Each team has a number key (1, 2, 3...) or click.
    First press wins and Alfred announces it. Space resets. Uses the quiz teams if you don't name any.

## Word games and prompts

The word never appears in what Alfred says out loud. The card hides it until the player taps "Show word".

15. **Charades**: "Give me a charades card, animals." Hidden word, a 90 second timer with Start.
16. **Pictionary**: "Give me a Pictionary word." Only things that can be drawn; 60 seconds.
17. **Taboo or Articulate**: "Give me a Taboo card." A word with five forbidden words.
18. **Heads Up**: "Deal a Heads Up deck of films." Hold it up; tap Got it or Pass (or the arrow keys). Alfred hears the score.
19. **Truth**: "Give me a truth."
20. **Dare**: "Give me a dare." Silly and safe.
21. **Truth or dare**: "Truth or dare?" Alfred picks one; buttons for the other.
22. **Two truths and a lie ideas**: "Give me ideas for two truths and a lie."
23. **Shuffle two truths and a lie**: "My statements are: I swam with sharks, I have three cats, I can juggle. The lie is the second." They come up in a random order; tap one to reveal the lie.
24. **Scattergories**: "Play Scattergories." A letter, categories and a two minute timer.
25. **Icebreaker questions**: "Give me an icebreaker."
26. **Word sets**: "What word sets do you have for charades?" Animals, actions, films, jobs, food, objects, sports and hobbies, places, tv and books, easy.

## Draws, teams and timers

27. **Secret Santa draw**: "Do a Secret Santa for Mum, Dad, Ava, Leo and Nan. Mum and Dad can't have each other. Budget 10 pounds."
    Nobody draws themselves; who drew whom is never said out loud. Stored in `.partyhost-santa.json`. Redrawing asks first.
28. **Reveal one name at a time**: "Next person." Alfred says who to pass the screen to. They tap "Show my name", then "Hide and pass on".
29. **Secret Santa progress**: "Has everyone seen their name?" A table of who has looked (never the names).
30. **Clear the draw**: "Clear the Secret Santa draw." Asks you to confirm first.
31. **Random teams**: "Split Ava, Leo, Mum, Dad, Nan and Sam into two teams with captains." Coloured team cards; "Shuffle again".
32. **Musical chairs timer**: "Start the musical chairs timer, between 10 and 30 seconds." Press Start; at a random moment a big STOP shows and a sound plays.
33. **Bingo tickets**: "Give me two bingo tickets." UK 90-ball tickets (three rows, five numbers a row); tap to mark off. Pair with the caller in Screen games.
34. **Bingo calls**: "What's the bingo call for 21?" ("Key of the door.") Or "Show the bingo calls."
35. **Who goes first**: "Who goes first: Ava, Leo, Mum?" A random playing order.
36. **Round timer**: "Give us a 90 second timer." A live countdown.

## Rules and ideas

37. **Rules of a classic**: "How do you play sardines?" Charades, Pictionary, Articulate, Taboo, Heads Up, musical chairs
    and statues, pass the parcel, sardines, murder in the dark, wink murder, Chinese whispers, I spy, twenty questions,
    Simon says, consequences, hot potato, Fizz Buzz, werewolf, bingo, snap, old maid, Go Fish, cheat, dominoes,
    Scattergories and quiz night.
38. **List the games**: "What party games do you know the rules to?" Tap one to hear it.
39. **Ideas**: "What can we play with six people and two kids for half an hour, something lively?" A table of games with players, time and what you need.
40. **Plan the night**: "Plan a three hour game night for eight people." A running order with times, from icebreakers to prizes.

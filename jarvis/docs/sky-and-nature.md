# Sky and nature: what to say to Alfred

Everything here is worked out on your PC from built-in tables and a small astronomy calculator, so it works offline.
The only exception is "Is the ISS overhead?", which asks a free public tracker for the space station's position and
sends it nothing about you. Places come from your home city (`JARVIS_CITY`, if it's one of about 50 UK cities), or say
a city, or give a latitude and longitude. Times are UK time (GMT or BST). Alfred already had "What's in the night sky
tonight?" and "Tell me about the constellation Orion" (see discover.md); these add to them.

Your nature journal is saved in `skynature-journal.json` in your memory folder.

## The sky
1. **Moon tonight**: "What's the moon tonight?" / "What was the moon on 2026-08-12?" Pops up a drawn moon showing the
   phase, with how much is lit, moonrise, moonset and the next full and new moon.
2. **Moon dates**: "When is the next full moon?" Pops up a table of the next eight new, quarter and full moons.
3. **Moon calendar**: "Show the moon calendar for October." Pops up a month of little moons with new, quarter and full moons
   marked; click a day to ask about it, and use the buttons to move month.
4. **Planets tonight**: "Which planets can I see tonight?" A table of the bright planets that are up, when, in which
   direction and how high (roughly; the built-in calculator is good to a few degrees).
5. **Star map**: "Show me the star map for tonight." / "Star map for midnight." Pops up a round sky chart of the
   constellations above the horizon with the bright stars, planets and moon (north at the top, east on the left).
6. **Star facts**: "Tell me about the star Betelgeuse." / "What bright stars can I ask about?"
7. **Meteor showers**: "When is the next meteor shower?" / "When do the Perseids peak?" A table of the year's showers with
   peak dates, rates and whether the moon will spoil them. Peak dates can move by a day.
8. **Eclipses**: "When is the next eclipse?" / "Which eclipses can I see from the UK?" A table of solar and lunar eclipses for
   2026 to 2030 with what the UK sees. Never look at the sun without proper eclipse glasses.
9. **Golden hour and blue hour**: "When is golden hour tonight?" Pops up a 24-hour bar of night, blue hour, golden hour
   and day, with sunrise and sunset marked and a table of all the times, for your city and any date.
10. **Sunrise, sunset and daylight**: "What time is sunset in Cardiff on Friday?" Same daylight bar, plus how much longer or
    shorter the day is getting and when it's fully dark.
11. **Day length chart**: "Show me a chart of day length through the year." A line chart of hours of daylight.
12. **Equinoxes and solstices**: "When is the winter solstice?" A table of the four dates and times.
13. **ISS overhead**: "Is the ISS overhead?" Says whether the space station is above your horizon, and how far away it is.

## Nature journal
14. **Log a sighting**: "Log a goldfinch at Roundhay Park, three of them." / "I saw a fox yesterday in the garden." Alfred
    tells you when it's a new bird for your life list or your first of the year.
15. **List sightings**: "Show my last bird sightings." / "What plants have I logged in April?" A list; click one to
    see all of that species.
16. **Species counts**: "How many of each species have I logged?" A table of sightings and individuals per species.
17. **First of the year**: "What are my first sightings this year?" A table with the date and place of each first, marking
    the ones that are new to you.
18. **Bird life list**: "Show my bird life list." A table of every bird with the first date and place, with the yearly totals
    spoken.
19. **Busiest months**: "Which month do I see most species?" A bar chart of species per month.
20. **Best places**: "Where do I see the most species?" A table of places.
21. **Delete a sighting**: "Delete sighting number 4." Alfred asks you to confirm first.

## Nature guide
22. **Garden bird ID**: "What's the small bird with a red breast and brown back?" Up to three likely birds (about 30 common UK
    birds) as a list; click one for facts.
23. **Bird facts and feeding tips**: "Tell me about the nuthatch." A card with a Log a sighting button.
24. **Tree ID from leaves**: "What tree has lobed leaves and acorns?" Up to three likely trees (about 20 UK trees).
25. **Tree facts**: "Tell me about the rowan."
26. **In season to spot**: "What can I see in nature this month?" / "What's around in May?" A list of wildlife and plants
    to look out for.
27. **In season to forage**: "What can I forage this month?" A table of wild foods, what to look for and what to take care
    over, always with a safety row.
28. **Foraging safety**: "Give me the foraging safety rules." Never eat anything unless you are 100 percent sure of it.
29. **Bird of the day**: "Give me a bird to learn about today."
    "What birds do you know?" / "What trees do you know?" lists them all.

The ID hints match your words against a built-in table; they point you in the right direction but are not a certain
identification, and foraging is always at your own risk.

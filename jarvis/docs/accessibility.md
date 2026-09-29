# Accessibility

Make the Alfred screen easy to use for everyone. Everything can be switched with the **ACCESS** button in the top bar (or a small ACCESS button in the top corner on plain themes), with the keyboard (**Alt+A**), or by asking Alfred. Settings are saved in the browser, per device, so your phone and your PC can have different ones. They apply as the page loads, before anything is drawn. Nothing here changes your login or your voice choice.

Asking Alfred uses one tool, `accessibility_settings`. Each time, a small "Accessibility" window pops up showing the current settings, so you can also click them.

## What you can do

1. **Bigger text** (three sizes: normal, large, extra large). Scales the HUD, the chat and every pop-up.
   Say: "Make the text bigger." or "Extra large text." The Accessibility window opens.
2. **High contrast**: pure black and white, thicker borders, no faint text; the stars and wolf are dimmed.
   Say: "Turn on high contrast."
3. **Reduce motion**: stops the twinkling stars, the wolf's streaming dots, the radar sweep and pop-up animations. It turns on by itself if your device asks for reduced motion.
   Say: "Reduce the motion."
4. **Captions**: a bar at the bottom shows what Alfred says, as he says it, and what you said.
   Say: "Turn on captions."
5. **Keyboard control**: Tab and Shift+Tab reach every button and pop-up, with a clear white focus ring. **Escape** closes the top pop-up. **Alt+M** or **Ctrl+/** turns the microphone on or off. **Alt+T** jumps to the typing box, **Alt+W** into the top pop-up, **Alt+A** opens the settings. **?** shows the shortcuts list.
   Say: "Show me the keyboard shortcuts." The list pops up.
6. **Screen reader support**: buttons have proper labels, pop-ups are dialogs named by their titles, and Alfred's replies and new pop-ups are announced.
7. **Dyslexia-friendly font**: a plain wide font (Verdana or Tahoma, nothing downloaded) with more space between letters, words and lines.
   Say: "Use the dyslexia font."
8. **Speech speed**: Alfred speaks slower or faster. His voice itself is not changed.
   Say: "Speak more slowly." or "Speak at 1.3 speed." A slider in the window lets you fine-tune it and hear a sample.
9. **Colour-blind safe colours**: blue and orange instead of red and green in charts and status colours.
   Say: "Turn on colour-blind mode."
10. **Accessibility settings window**: all of the above as tick boxes, with a Reset button.
    Say: "Open the accessibility settings." To put everything back: "Reset the accessibility settings."

## Good to know

- The tool's actions are `big_text`, `high_contrast`, `reduce_motion`, `captions`, `dyslexia_font`, `colour_blind`, `speech_speed`, `show_settings`, `show_shortcuts` and `reset`.
- Switches take on, off or toggle (on if you don't say). Speech speed takes slower, faster, normal or a number such as 0.8.
- Because settings live in the browser, saying "big text" on your phone does not change the PC.

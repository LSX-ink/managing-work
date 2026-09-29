"""Built-in photography reference lists: shoot types (shot lists and packing), composition tips, challenges,
walk ideas, starting camera settings, lens roles and a small glossary. Plain data, no logic."""

# Each shoot type: shots to capture, and things to pack as (label, gear type or word to match in your gear list).
SHOOTS = {
    "portrait": {
        "shots": ["Headshot with soft window light", "Half-length, looking away", "Full-length, walking", "Close-up of hands",
                  "Laughing candid", "Backlit at golden hour", "Detail of jewellery or clothing", "Environmental portrait"],
        "pack": [("Camera body", "camera"), ("Portrait lens (50 to 85 mm)", "lens"), ("Spare battery", "battery"),
                 ("Memory cards", "card"), ("Reflector", "reflector"), ("Speedlight or continuous light", "flash"),
                 ("Lens cloth", ""), ("Water and snacks for the model", "")]},
    "landscape": {
        "shots": ["Wide establishing scene", "Foreground interest with a distant view", "Leading line to the horizon",
                  "Long exposure of water", "Details in rock, grass or bark", "Panorama in several frames",
                  "Golden hour glow", "Moody weather or mist"],
        "pack": [("Camera body", "camera"), ("Wide lens (16 to 35 mm)", "lens"), ("Sturdy tripod", "tripod"),
                 ("ND filters", "filter"), ("Polarising filter", "filter"), ("Spare battery", "battery"),
                 ("Memory cards", "card"), ("Head torch", ""), ("Waterproofs and warm layers", ""), ("Map and phone", "")]},
    "wedding": {
        "shots": ["Rings close-up", "Dress and shoes", "Groom getting ready", "Bride's first look", "Ceremony aisle",
                  "Exchange of vows", "Confetti", "Family group formals", "Couple portraits at sunset", "First dance",
                  "Cake cutting", "Speeches and reactions", "Table details", "Guests laughing"],
        "pack": [("Two camera bodies", "camera"), ("Standard zoom (24 to 70 mm)", "lens"), ("Telephoto (70 to 200 mm)", "lens"),
                 ("Fast prime (35 or 50 mm)", "lens"), ("Flash and diffuser", "flash"), ("Spare batteries", "battery"),
                 ("Many memory cards", "card"), ("Shot list and family group list", ""), ("Comfortable shoes", ""),
                 ("Water and snacks", "")]},
    "street": {
        "shots": ["Strong shadows and light", "A reflection", "Silhouette", "Someone absorbed in their phone",
                  "Layers: foreground, middle, background", "Colour pop against grey", "Hands and feet", "Interesting sign"],
        "pack": [("Small camera", "camera"), ("Prime lens (28 to 35 mm)", "lens"), ("Spare battery", "battery"),
                 ("Memory card", "card"), ("Comfortable shoes", ""), ("Small bag", "bag")]},
    "night": {
        "shots": ["Star field over a foreground", "Milky Way core", "Star trails", "Moon with a landscape",
                  "Light trails from cars", "City lights reflection", "Light painting"],
        "pack": [("Camera body", "camera"), ("Fast wide lens (f/2.8 or faster)", "lens"), ("Sturdy tripod", "tripod"),
                 ("Remote release", "remote"), ("Spare batteries", "battery"), ("Head torch with red light", ""),
                 ("Star chart app on phone", ""), ("Warm layers and hot drink", "")]},
    "macro": {
        "shots": ["Flower centre", "Insect on a leaf", "Water droplet", "Texture of a feather", "Frost or dew on a web",
                  "Something tiny from home, like a watch"],
        "pack": [("Camera body", "camera"), ("Macro lens (90 to 105 mm)", "lens"), ("Tripod or bean bag", "tripod"),
                 ("Ring flash or small light", "flash"), ("Spray bottle for dew", ""), ("Kneeling mat", ""),
                 ("Spare battery", "battery"), ("Memory card", "card")]},
    "wildlife": {
        "shots": ["Animal in its habitat", "Eye contact close-up", "Action or flight", "Behaviour like feeding",
                  "Silhouette at dawn", "Bird on a clean perch"],
        "pack": [("Camera body", "camera"), ("Telephoto (200 to 600 mm)", "lens"), ("Monopod or tripod", "tripod"),
                 ("Teleconverter", ""), ("Spare batteries", "battery"), ("Memory cards", "card"),
                 ("Binoculars", ""), ("Camouflage clothing", ""), ("Flask and snacks", "")]},
    "product": {
        "shots": ["Hero shot on plain background", "Three-quarter angle", "Top-down flat lay", "Close-up of a detail",
                  "In-use lifestyle shot", "Scale shot next to a hand"],
        "pack": [("Camera body", "camera"), ("Macro or 50 mm lens", "lens"), ("Tripod", "tripod"),
                 ("Two soft lights or a window", "flash"), ("White and black card", "reflector"), ("Backdrop paper", ""),
                 ("Lint roller and cloths", "")]},
    "sports": {
        "shots": ["Peak of the action", "Player's expression", "Ball in frame", "Celebration", "Wide scene with crowd",
                  "Panning shot with motion blur"],
        "pack": [("Camera body with fast burst", "camera"), ("Telephoto zoom (70 to 200 mm)", "lens"), ("Monopod", "tripod"),
                 ("Spare batteries", "battery"), ("Fast memory cards", "card"), ("Rain cover", ""), ("Ear plugs", "")]},
    "family": {
        "shots": ["Group all looking at the camera", "Candid of a child playing", "Grandparents with grandchildren",
                  "Hands together", "Everyone laughing", "Someone asleep", "Traditional and silly group shots"],
        "pack": [("Camera body", "camera"), ("Standard zoom", "lens"), ("Spare battery", "battery"),
                 ("Memory card", "card"), ("Small flash", "flash"), ("Snacks to keep children happy", "")]},
    "travel": {
        "shots": ["Famous landmark, with a twist", "Local food", "A market stall", "Street scene with people",
                  "Sunrise or sunset viewpoint", "Detail of a doorway or tiles", "A selfie with the view", "Transport"],
        "pack": [("Camera body", "camera"), ("Versatile zoom (24 to 105 mm)", "lens"), ("Wide prime", "lens"),
                 ("Travel tripod", "tripod"), ("Spare batteries and charger", "battery"), ("Memory cards", "card"),
                 ("Plug adaptor", ""), ("Padded bag", "bag"), ("Lens cloth", "")]},
    "event": {
        "shots": ["Venue and setup", "Arrivals", "Speaker on stage", "Audience reactions", "Networking candids",
                  "Group photo", "Details like signs and food", "Closing moment"],
        "pack": [("Camera body", "camera"), ("Standard zoom (24 to 70 mm)", "lens"), ("Flash and diffuser", "flash"),
                 ("Spare batteries", "battery"), ("Memory cards", "card"), ("Business cards", "")]},
    "property": {
        "shots": ["Front of the building", "Living room from the corner", "Kitchen wide", "Each bedroom",
                  "Bathroom", "Garden or view", "Details worth selling"],
        "pack": [("Camera body", "camera"), ("Wide lens (14 to 24 mm)", "lens"), ("Tripod", "tripod"),
                 ("Spirit level", ""), ("Flash for windows", "flash"), ("Spare battery", "battery")]},
}

# key -> (name, how to do it, a tip, drawing used by the pop-up)
COMPOSITION = {
    "rule-of-thirds": ("Rule of thirds", "Imagine the frame cut into a 3 by 3 grid and put the subject on a line or a crossing.",
                       "Put the eyes on the top line and leave space in the direction the subject looks.", "thirds"),
    "leading-lines": ("Leading lines", "Use roads, fences, rivers or shadows that draw the eye towards the subject.",
                      "Get low and close to the line to make it dramatic.", "leading"),
    "symmetry": ("Symmetry", "Centre the subject so both halves mirror each other, like a reflection or a building.",
                 "Check the horizon is level; symmetry shows every tilt.", "symmetry"),
    "framing": ("Frame within a frame", "Shoot through a doorway, arch, window or branches to surround the subject.",
                "Expose for the subject, not the frame, and let the frame go dark.", "framing"),
    "diagonals": ("Diagonals", "Lines running corner to corner add energy and movement.",
                  "Tilt your camera a little only when a diagonal is already there.", "diagonal"),
    "golden-ratio": ("Golden ratio", "Like thirds, but the lines sit closer together, at about 38 and 62 percent.",
                     "Handy for portraits: the eyes on the upper line.", "golden"),
    "golden-spiral": ("Golden spiral", "Let the eye travel along a curve that winds to the subject.",
                      "Shells, staircases and winding paths give a natural spiral.", "spiral"),
    "negative-space": ("Negative space", "Leave lots of empty sky, water or wall around a small subject.",
                       "Keep the empty area calm and clean; it is part of the picture.", "negative"),
    "fill-the-frame": ("Fill the frame", "Move closer until the subject fills nearly everything.",
                       "Look at the edges of the frame and remove anything that doesn't help.", "fill"),
    "layers": ("Foreground, middle, background", "Put something interesting in each layer for depth.",
               "A small foreground object adds scale to a landscape.", "layers"),
    "odd-numbers": ("Rule of odds", "Groups of three or five look more natural than two or four.",
                    "Vary the size and spacing of the items.", "odds"),
    "patterns": ("Patterns and breaking them", "Repeated shapes are pleasing; one odd one out grabs attention.",
                 "Fill the frame with the pattern and place the exception on a third.", "pattern"),
}

CHALLENGES = [
    "Something red", "A reflection", "Your shadow", "Something that makes you smile", "A pattern",
    "Look up: shoot only above your head", "Get low: shoot from ground level", "Your breakfast, styled like a magazine",
    "A door or gate", "Something round", "Texture close-up", "A leading line", "Something old",
    "A silhouette", "Someone's hands", "Your view from the window", "Something blue", "Symmetry",
    "Steam, smoke or mist", "A tiny thing photographed to look big", "Something with a number on it",
    "Something you use every day", "A doorway framing a view", "Something soft", "Something sharp and shiny",
    "Motion blur on purpose", "Light through a window", "A stranger from behind", "Something green",
    "Something that doesn't belong", "The oldest thing you own", "Water in any form", "A staircase",
    "Straight lines and angles", "A portrait of a pet or plant", "Shoot in black and white", "Something yellow",
    "Golden hour light", "A sign or letter", "The number three", "Rain or puddles", "Something edible",
    "The sky", "A view from above", "Two colours only", "Something cosy", "Just the corner of a room",
    "Something growing", "A window at night", "Your favourite mug, three ways",
]
CHALLENGE_TIPS = [
    "Take ten frames, then keep only your best one.", "Try a different angle from your first idea.",
    "Move your feet before you zoom.", "Look at the light first, then the subject.",
    "Shoot it once wide, once close.", "Check the edges of the frame before pressing.",
]

WALK_THEMES = ["colour: pick one and only shoot that", "shapes: circles, squares and triangles", "textures", "reflections",
               "signs and lettering", "doors and windows", "shadows and light", "small details", "people at work",
               "green things", "old and new side by side", "patterns", "curves and lines", "numbers", "symmetry"]
WALK_RULES = ["Use one lens or one focal length only", "Shoot everything from below eye level",
              "Keep it to 20 frames, no deleting", "Only shoot in black and white", "Shoot only what is behind you",
              "Take one photo every 100 steps", "Turn left at every corner", "No people in frame", "Shoot at f/2.8 or wider all walk",
              "Every picture needs a foreground", "Use your phone only", "Look up at every junction"]
WALK_BONUS = ["Take a portrait of a stranger's shadow", "Find a leading line", "Shoot a reflection", "Find one perfect frame",
              "Photograph a detail nobody notices", "End with a picture of where you finished"]
WALK_PLACES = {
    "town": ["Follow the oldest street you can find", "Walk to the highest car park or bridge for a view"],
    "park": ["Circle the pond or lake once", "Find the quietest bench and shoot outwards"],
    "seaside": ["Walk the tideline and shoot the patterns", "Shoot the pier from below"],
    "countryside": ["Follow a footpath to the next stile", "Stop at every gate"],
    "home": ["Walk room to room and photograph the corners", "Shoot your street from your front door"],
}

# name -> (aperture, shutter, ISO, focus mode, note)
SETTINGS = {
    "portrait": ("f/1.8 to f/2.8", "1/200 or faster", "100 to 400", "Single-point AF on the eye", "Blurs the background."),
    "landscape": ("f/8 to f/11", "Any, on a tripod", "100", "Focus a third of the way into the scene", "Sharp front to back."),
    "sports": ("f/2.8 to f/5.6", "1/1000 or faster", "Auto ISO", "Continuous AF, burst mode", "Freezes fast action."),
    "wildlife": ("f/5.6 to f/8", "1/1000 or faster", "Auto ISO", "Continuous AF with animal eye detect", "Fast to catch a moment."),
    "street": ("f/8", "1/250", "Auto ISO", "Zone focus at about 3 m", "Set and forget."),
    "night-handheld": ("Widest", "1/60 or slower with stabilisation", "1600 to 6400", "Single AF", "Brace against something."),
    "stars": ("Widest, f/2.8 or faster", "15 to 25 s (NPF rule)", "1600 to 3200", "Manual focus on a bright star", "Use a tripod."),
    "macro": ("f/8 to f/16", "1/200 or use flash", "200 to 400", "Manual focus, move the camera", "Depth of field is tiny."),
    "panning": ("f/8", "1/30 to 1/60", "100", "Continuous AF", "Follow the subject smoothly."),
    "waterfall": ("f/11 to f/16", "0.5 to 2 s", "100", "Single AF", "Needs a tripod; an ND filter helps."),
    "fireworks": ("f/8 to f/11", "2 to 4 s, bulb mode", "100", "Manual focus at infinity", "Tripod and remote release."),
    "indoor-event": ("f/2.8", "1/125", "1600 to 3200", "Continuous AF", "Bounce the flash off the ceiling."),
    "food": ("f/2.8 to f/4", "1/125", "200 to 400", "Single AF", "Window light from the side."),
    "video": ("As needed", "Twice your frame rate, e.g. 1/50 at 25 fps", "Lowest possible", "Continuous AF", "Use ND in bright light."),
}

# subject -> (lower mm, upper mm) full-frame focal length, and why
LENS_ROLES = {
    "landscape": (14, 35, "Wide lenses capture sweeping scenes with foreground interest."),
    "architecture": (16, 35, "Wide angle fits buildings in; keep the camera level."),
    "street": (24, 50, "Close and natural; you have to be near the action."),
    "portrait": (70, 135, "Flattering compression; the background blurs nicely."),
    "wildlife": (200, 600, "Long reach so you don't disturb the animal."),
    "sports": (70, 300, "Reach across a pitch with a fast aperture."),
    "macro": (90, 105, "A true macro lens focuses very close."),
    "astro": (14, 24, "Fast and wide to gather starlight."),
    "travel": (24, 105, "One flexible zoom covers most things."),
    "event": (24, 70, "Fast standard zoom for rooms and groups."),
    "food": (50, 100, "Standard to short tele for flat lays and close-ups."),
}

GLOSSARY = {
    "aperture": "The opening in the lens. A small f-number like f/1.8 is wide open: more light, blurrier background.",
    "shutter speed": "How long the sensor is exposed to light. Fast freezes action; slow blurs motion.",
    "iso": "The sensor's sensitivity. Higher ISO brightens a dark scene but adds noise.",
    "exposure triangle": "Aperture, shutter speed and ISO. Change one and balance another to keep the same brightness.",
    "stop": "A doubling or halving of light. Each full aperture, shutter or ISO step is one stop.",
    "ev": "Exposure value: one number for how bright the scene is, for a given set of settings.",
    "depth of field": "The zone in front of and behind your focus point that looks sharp.",
    "bokeh": "The look of the out-of-focus background, especially bright points of light.",
    "hyperfocal distance": "The focus distance that makes everything from half that distance to infinity sharp.",
    "focal length": "Lens length in millimetres. Low is wide, high is telephoto.",
    "crop factor": "How much smaller a sensor is than full frame. Multiply the focal length by it for the equivalent view.",
    "raw": "An uncut file with all the sensor data, for the most editing freedom.",
    "histogram": "A graph of the tones in a picture, dark on the left, light on the right.",
    "white balance": "Adjusts colour so whites look white under warm or cool light.",
    "nd filter": "A dark filter that cuts light so you can use slow shutter speeds in daytime.",
    "polariser": "A filter that cuts glare and reflections and deepens blue skies.",
    "bracketing": "Taking several shots at different exposures to keep detail in shadows and highlights.",
    "hdr": "Combining several exposures to show detail in both bright and dark areas.",
    "dynamic range": "The range from the darkest to the brightest detail a camera can record in one shot.",
    "metering": "How the camera measures light: evaluative, centre-weighted or spot.",
    "guide number": "A flash's power rating. Distance multiplied by aperture at ISO 100.",
    "golden hour": "The hour after sunrise or before sunset, when light is soft and warm.",
    "blue hour": "The short time before sunrise or after sunset when the sky is deep blue.",
    "rule of thirds": "Placing important things on the lines that divide the frame into thirds.",
    "vignette": "Darkening in the corners of a picture.",
    "chromatic aberration": "Coloured fringes around high-contrast edges.",
    "mirrorless": "A camera with no mirror box, showing the view on an electronic viewfinder.",
    "prime lens": "A lens with a fixed focal length, usually sharp and with a wide aperture.",
    "bulb mode": "A shutter setting that keeps it open as long as you hold the button.",
    "ibis": "In-body image stabilisation: the sensor moves to cancel shake.",
    "dpi": "Dots per inch: how many pixels are packed into each inch of a print. 300 is sharp.",
    "aspect ratio": "The shape of a picture, width to height, like 3:2 or 16:9.",
}

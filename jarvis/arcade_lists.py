"""Screen games: the local word lists and countries the word games and quizzes use (nothing is fetched)."""

# Wordle answers: common five-letter words.
ANSWERS = """
about above actor acute admit adopt adult after again agent agree ahead alarm album alert alike alive allow alone
along alter among anger angle angry apple apply arena argue arise aside audio avoid award aware badge basic beach
begin being below bench birth black blade blame blank blast blend bless blind block blood board boast bonus boost
booth bound brain brand brave bread break brick bride brief bring broad brown brush build bunch burst cabin cable
candy carry catch cause chain chair chalk charm chart chase cheap check cheek chess chest chief child chill claim
class clean clear click cliff climb clock close cloth cloud coach coast count court cover crack craft crane crash
cream crime crisp cross crowd crown curve cycle daily dance death delay depth diary dirty doubt dough draft drain
drama drawn dream dress drink drive eager early earth eight elbow elder empty enemy enjoy enter entry equal error
event every exact exist extra faint faith false fancy feast fence ferry field fifty fight final flame flash fleet
float flood floor flour fluid focus force forge forty found frame fresh front frost fruit funny ghost giant given
glass globe glory glove grace grade grain grand grant grape grass grave great green greet grill group guard guess
guest guide habit happy harsh heart heavy hedge hello hobby honey horse hotel house human ideal image index inner
input issue jelly jewel joint judge juice knife knock label large laser later laugh layer learn lease least leave
legal lemon level light limit linen lodge logic loose lorry lucky lunch magic major maker march match maybe mayor
medal media mercy metal might minor model money month moral motor mount mouse mouth movie music nerve never night
noble noise north novel nurse ocean offer often olive onion opera order other outer owner paint panel paper party
pasta patch peace pearl phone photo piano piece pilot pitch pizza place plain plane plant plate point polar pound
power press price pride prime print prize proof proud prove queen quick quiet quite radio raise range rapid reach
ready relax reply rider ridge right river roast robin robot rough round route royal rugby ruler salad sauce scale
scene scone score sense serve seven shade shake shape share shark sharp sheep sheet shelf shell shine shirt shock
shore short shout sight skill skirt sleep slice slide small smart smile smoke snack snake solid solve sound south
space spare speak speed spend spice spine spoon sport staff stage stair stamp stand start steam steel stick still
stone storm story stove straw sugar sunny sweet table taste teach thank theme thick thing think third three throw
thumb tiger tired title toast today tooth topic torch total touch tower track trade train treat trend trial tribe
trick truck truly trust truth twice uncle under union unity upper upset urban usual valid value video visit vital
voice waste watch water whale wheat wheel while white whole woman world worry worth write wrong yacht young youth
zebra
""".split()

# More words accepted as guesses, on top of the answers.
EXTRA = """
abbey abode abort acorn adapt added adore aisle alien align alley alloy aloud alpha amber amend ample angel ankle
annoy apart apron arrow ashes asked atlas attic avert awake awful bacon bagel baked baker bands banks barge baron
based bases basin batch bathe beans beard beast beech beefy beers began beige belly bells belts berry bikes bills
bingo birds bison bites blaze bleak bloom blown blues bluff blunt blurt blush boats bones books boots bored bossy
bowls boxer boxes brace braid brake brass bream breed briar bribe brine brink brisk broke brood brook broom broth
brunt buddy budge buggy bugle bulbs bulky bully bumpy bunny burnt bushy cacti cakes camel cameo canal canoe caper
cards cargo carol carve cases cater cedar cello chaos chaps cheer chewy chick chimp china chips choir chord chose
chunk cider cigar cinch circa civic civil clamp clang clash clasp claws clays cleat clerk cling cloak clove clown
clubs clump clung coats cocoa coins colds comet comic comma conch coral corgi corny couch cough could cower coyly
crabs cramp crate crave crawl crazy creak creek creep crept crest crews cried cries croak crook crops crude cruel
crumb crush crust cubic cumin cupid curls curly curry cushy cuter dairy daisy dated dealt decay decor decoy deeds
delta denim dense dents derby desks diced diner dingy dirge disco ditch ditto diver dizzy dodge doing dolls donor
donut doors dopey dowdy downs dozen dread dried drift drill drily drone drool droop drops drove drown drums dryer
ducks dunes dusty duvet dwarf dwell dying eagle eared earns eased easel eaten eater ebony edged edges eerie egret
elect elegy elves email ember emery ended endow enact ensue envoy epoch epoxy essay ethic evade evens evict evoke
exalt excel exert exile expel fable faced facet fades fairy fakes falls fangs farms fatal fatty fault fauna feats
feeds feels fella ferns fetch fever fewer fibre fiery files filly filmy filth finch finds fined fired firms first
fishy fists fixed fizzy flags flair flake flaky flank flaps flare flask flats flaws fleas flick flier flies fling
flint flips flirt flock flora floss flown flows flute foamy foggy foils folds folks folly foods fools forks forms
forte fours foyer frail fraud freak freed fried fries frill frisk frizz frock frond frown froze fudge fuels fully
fumes fungi funky furry fussy fuzzy gains gales gamer games gamma gases gauge gauze gavel gazed gears geese genie
genre germs giddy gifts gills girls girth gleam glean glide glint gloat gloom gloss glued gnome goals goats going
golds golly goods goody gooey goose gorge gouge gourd gowns grabs graft grate gravy graze greed grief grime grimy
grind grins gripe grips grits groan groom grope gross grove growl grown grows gruel gruff grunt guava guilt guise
gulls gully gummy gusts gusty gutsy hairs hairy halls halve hands handy hangs hardy harps harry hasty hatch hated
hater hates haunt haven havoc hazel heads heals heaps heard hears heats hefty heirs helix helps hence herbs herds
heron hides highs hiker hikes hills hilly hinge hints hippo hitch hoard hoist holds holes holly homes hooks hoops
hoped hopes horns hosts hound hours hover howls huffy hulls humid humus hunch hunts hurry hurts husky hutch hyena
hymns icing icons idiom idled igloo inbox incur inlet irate irony itchy ivory jacks jaded jails jammy jeans jeeps
jerky jests jetty jiffy joins joker jokes jolly joust jumbo jumps jumpy juror kayak kebab keeps khaki kicks kills
kinds kings kiosk kites kitty knack knead kneel knelt knits knobs knots known knows koala laces lacks laden ladle
lakes lambs lamps lance lands lanes lapse larva latch latte lawns leads leafy leaks leaky leans leant leaps leapt
leash leech leeks lends lever licks lifts liked likes lilac limbs limes limbo lined liner lines lingo lions lists
litre lived liver lives llama loads loafs loans lobby local locks locus lofty loins lolly loner longs looks looms
loops loopy lords loser loses lotus lousy loved lover loves lower lowly loyal lumps lumpy lunar lurch lured lurks
lying lyric madam mains maize males malls malts mango mania manly manor maple marks marry marsh masks mason masts
mates maths mauve meals mealy meant meats meaty melon melts menus merit merry messy miles mimic mince minds mined
miner mines minty minus mirth miser mists misty mixed mixer moans moats mocha modem moist molar molds moldy monks
moody moons moose moped mossy motel moths motto mould mound mourn mousy moved mover moves mower mucky muddy mulch
mummy munch mural murky mushy musty muted myths nails naive naked names nanny nasal nasty naval navel necks needs
needy neigh nests newer newly nicer niche ninja ninth nippy nodes noisy nomad nooks noose norms nosey notch noted
notes nouns nudge nutty nylon oaken oasis oaths occur octet oddly odour offal oiled olden oldie omega omens onset
oozed opens optic orbit organ otter ought ounce outdo ovals ovary ovens overs overt owing owned oxide ozone packs
paddy pagan pager pages pains pairs palms panda panic pansy pants parks parts patio paved paves peach peaks pears
pecan pedal peels peeps penny perch peril perks perky pesky pesto petal petty phase picks picky piety piggy pinch
pines pinks pints pious piped pipes pique pixel pixie plaid plank plans plays plaza plead pleat plods plots pluck
plugs plumb plume plump plums plush poach poems poets poker polka ponds pooch poppy porch pores posed poser poses
posse posts pouch pours prank prawn prays preen prick pried pries prism privy probe prone prong props prose prowl
prune psalm pudgy puffs puffy pulls pulse pumps punch pupil puppy purse pushy putty quack quail qualm quart quash
query quest queue quill quilt quirk quits quota quote races racks radar radii rafts raged rails rainy rains raked
rally ramps ranch rangy ranks rants raspy rated rates ratio raven raves rayon razor reads realm reams reaps rears
rebel recap refer reign reins relay remit renew repay reset resin rests retro revel rhino rhyme rides rifle rigid
rinse riots ripen risen rises risks risky rites rival rivet roads roams roars robes rocks rocky rodeo rogue roles
rolls roman roofs rooms roomy roost roots roped ropes roses rotor rouge rowdy rower ruins ruled rules rumba runny
rural rusty sadly safer saint sales salon salsa salty salve sandy sassy satin sauna saved saver saves savvy scald
scalp scaly scamp scant scare scarf scary scent scoff scold scoop scope scorn scout scowl scram scrap scree screw
scrub seals seams seats seeds seedy seems seize sells sends sepia setup sever sewer shack shady shaft shaky shall
shame shams shawl sheds sheen sheer shied shift shiny ships shire shoal shone shook shoot shops shorn shots shove
shown shows showy shred shrew shrub shrug shuck shunt shush shyly sided sides siege sieve sighs sigma signs silks
silky silly since sinew singe sings sinks siren sites sixth sixty sized sizes skate skids skied skier skies skimp
skins skips skull skunk slabs slack slain slang slant slaps slash slate slave sleek sleet slept slick slime slimy
sling slink slips slope slosh sloth slots slump slung slurp slush smack smash smear smell smelt smirk smith smock
snags snail snare snarl sneak sneer sniff snipe snoop snore snort snout snowy snuck snuff soapy sober socks sofas
softy soggy solar soles sonic sooty sorry sorts souls soupy spade spank spark spasm spawn spear specs spell spelt
spent spied spies spike spiky spill spilt spire spite splat split spoil spoke spoof spook spool spore spots spout
spray spree sprig spunk spurt squad squat squid stack stain stake stale stalk stall stank stare stark stars stash
state stays steak steal steed steep steer stems steps stern stews stiff sting stink stint stock stoic stoke stole
stomp stony stood stool stoop stops store stork stout strap stray strip strut stuck study stuff stump stung stunk
stunt style suave sucks suede suits sulky sumac super surge surly sushi swabs swamp swans swaps swarm swear sweat
swede sweep swell swept swift swill swims swing swipe swirl swish swoop sword swore sworn swung syrup tabby taboo
tacky tacos taffy tails taint taken takes tales talks tally talon tamed tango tangy tanks taper tapes tardy tarot
tarts tasks tasty taunt tawny taxed taxes taxis teams tears teary tease teddy teens teeth tempo tends tenor tense
tenth tents tepid terms terse tests texts thaws theft their there these thief thigh thorn those threw thugs tiara
tidal tides tiers tight tiled tiles tilts timer times timid tinge tints tipsy titan toads toils token tolls tombs
tonal toned tones tongs tonic tools toots topaz torso totem tough tours towel towns toxic trace tract trail trait
tramp trams traps trash trawl trays tread treks tress trims tripe trips trite troll troop trots trout truce trunk
truss tubas tubes tucks tulip tummy tunas tuned tunes tunic turbo turns tutor tweak tweed tweet twigs twine twins
twirl twist tying udder ulcer ultra umber uncut undid undue unfit unify unite units unlit untie until unzip usage
usher using utter vague valet valve vases vault veils veins venom vents venue verbs verge verse vicar vices views
vigil villa vines vinyl viola viper viral virus visas visor vista vivid vocal vogue voted voter votes vouch vowel
wacky wafer waged wager wages wagon waist waits waive wakes walks walls waltz wands wants wards wares warms warns
warps warts washy wasps watts waved waver waves waxed weary weave wedge weeds weedy weeks weigh weird wells welsh
whack wharf where which whiff whine whiny whips whirl whisk whist wicks widen wider widow width wield wills wimpy
wince winch winds windy wines wings winks wiped wiper wipes wired wires wiser wisps witch witty wives woken woods
woody wooed woozy words wordy works worms wormy worse worst would wound woven wraps wrath wreak wreck wrens wrest
wring wrist wrote wrung yards yarns yawns yearn years yeast yells yelps yield yodel yokel yolks yours yummy zesty
zippy zones
""".split()

# Hangman words (all letters, no spaces).
HANGMAN = """
adventure airport alphabet anchor apricot astronaut avalanche backpack badminton balloon banana bandage biscuit
blizzard blossom bookshelf broccoli bubble butterfly cabbage calendar camera candle canyon caravan carnival castle
caterpillar cathedral champion chimney chocolate cinnamon compass computer crocodile crossword crystal cupboard
cushion daffodil dinosaur dolphin dragon drizzle earthquake elephant envelope escalator explorer festival fireworks
flamingo football fortune fountain galaxy garden giraffe glacier gondola gorilla grandfather guitar hamster
harbour hedgehog helicopter horizon hurricane iceberg igloo island jellyfish journey jungle kangaroo kettle keyboard
kitchen ladder lantern library lighthouse lobster magazine magician mammoth marathon meadow microwave mountain
mushroom museum necklace notebook octopus orchestra ostrich paddle pancake parachute passport peacock penguin
pineapple planet porcupine postcard pumpkin puzzle pyramid quartz rainbow raspberry reindeer rhubarb rocket
sandcastle satellite saxophone scarecrow scissors seahorse shipwreck skeleton snowman spaghetti squirrel stadium
strawberry submarine sunflower suitcase swimming telescope thunder tortoise tractor treasure trumpet tulip umbrella
unicorn universe vampire vegetable violin volcano waterfall whistle windmill wizard yoghurt zookeeper
""".split()

# (country, capital, flagcdn code) for the capitals and flags quizzes.
COUNTRIES = [
    ("Afghanistan", "Kabul", "af"), ("Albania", "Tirana", "al"), ("Algeria", "Algiers", "dz"),
    ("Argentina", "Buenos Aires", "ar"), ("Australia", "Canberra", "au"), ("Austria", "Vienna", "at"),
    ("Bahamas", "Nassau", "bs"), ("Bangladesh", "Dhaka", "bd"), ("Barbados", "Bridgetown", "bb"),
    ("Belgium", "Brussels", "be"), ("Bolivia", "Sucre", "bo"), ("Botswana", "Gaborone", "bw"),
    ("Brazil", "Brasilia", "br"), ("Bulgaria", "Sofia", "bg"), ("Cambodia", "Phnom Penh", "kh"),
    ("Cameroon", "Yaounde", "cm"), ("Canada", "Ottawa", "ca"), ("Chile", "Santiago", "cl"),
    ("China", "Beijing", "cn"), ("Colombia", "Bogota", "co"), ("Costa Rica", "San Jose", "cr"),
    ("Croatia", "Zagreb", "hr"), ("Cuba", "Havana", "cu"), ("Cyprus", "Nicosia", "cy"),
    ("Czechia", "Prague", "cz"), ("Denmark", "Copenhagen", "dk"), ("Ecuador", "Quito", "ec"),
    ("Egypt", "Cairo", "eg"), ("Estonia", "Tallinn", "ee"), ("Ethiopia", "Addis Ababa", "et"),
    ("Fiji", "Suva", "fj"), ("Finland", "Helsinki", "fi"), ("France", "Paris", "fr"),
    ("Georgia", "Tbilisi", "ge"), ("Germany", "Berlin", "de"), ("Ghana", "Accra", "gh"),
    ("Greece", "Athens", "gr"), ("Hungary", "Budapest", "hu"), ("Iceland", "Reykjavik", "is"),
    ("India", "New Delhi", "in"), ("Indonesia", "Jakarta", "id"), ("Iran", "Tehran", "ir"),
    ("Iraq", "Baghdad", "iq"), ("Ireland", "Dublin", "ie"), ("Israel", "Jerusalem", "il"),
    ("Italy", "Rome", "it"), ("Jamaica", "Kingston", "jm"), ("Japan", "Tokyo", "jp"),
    ("Jordan", "Amman", "jo"), ("Kazakhstan", "Astana", "kz"), ("Kenya", "Nairobi", "ke"),
    ("Latvia", "Riga", "lv"), ("Lebanon", "Beirut", "lb"), ("Lesotho", "Maseru", "ls"),
    ("Lithuania", "Vilnius", "lt"), ("Luxembourg", "Luxembourg", "lu"), ("Madagascar", "Antananarivo", "mg"),
    ("Malawi", "Lilongwe", "mw"), ("Malaysia", "Kuala Lumpur", "my"), ("Malta", "Valletta", "mt"),
    ("Mexico", "Mexico City", "mx"), ("Mongolia", "Ulaanbaatar", "mn"), ("Morocco", "Rabat", "ma"),
    ("Mozambique", "Maputo", "mz"), ("Namibia", "Windhoek", "na"), ("Nepal", "Kathmandu", "np"),
    ("Netherlands", "Amsterdam", "nl"), ("New Zealand", "Wellington", "nz"), ("Nigeria", "Abuja", "ng"),
    ("North Korea", "Pyongyang", "kp"), ("Norway", "Oslo", "no"), ("Pakistan", "Islamabad", "pk"),
    ("Peru", "Lima", "pe"), ("Philippines", "Manila", "ph"), ("Poland", "Warsaw", "pl"),
    ("Portugal", "Lisbon", "pt"), ("Qatar", "Doha", "qa"), ("Romania", "Bucharest", "ro"),
    ("Russia", "Moscow", "ru"), ("Rwanda", "Kigali", "rw"), ("Saudi Arabia", "Riyadh", "sa"),
    ("Senegal", "Dakar", "sn"), ("Serbia", "Belgrade", "rs"), ("Singapore", "Singapore", "sg"),
    ("Slovakia", "Bratislava", "sk"), ("Slovenia", "Ljubljana", "si"), ("South Africa", "Pretoria", "za"),
    ("South Korea", "Seoul", "kr"), ("Spain", "Madrid", "es"), ("Sri Lanka", "Colombo", "lk"),
    ("Sweden", "Stockholm", "se"), ("Switzerland", "Bern", "ch"), ("Syria", "Damascus", "sy"),
    ("Tanzania", "Dodoma", "tz"), ("Thailand", "Bangkok", "th"), ("Tunisia", "Tunis", "tn"),
    ("Turkey", "Ankara", "tr"), ("Uganda", "Kampala", "ug"), ("Ukraine", "Kyiv", "ua"),
    ("United Arab Emirates", "Abu Dhabi", "ae"), ("United Kingdom", "London", "gb"),
    ("United States", "Washington, D.C.", "us"), ("Uruguay", "Montevideo", "uy"), ("Venezuela", "Caracas", "ve"),
    ("Vietnam", "Hanoi", "vn"), ("Zambia", "Lusaka", "zm"), ("Zimbabwe", "Harare", "zw"),
]

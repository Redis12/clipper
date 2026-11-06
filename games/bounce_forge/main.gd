extends Node2D
# Bounce Forge — World 1 (Candy Tubes). See GAME_DESIGN.md.
# Candies bounce on gummy pads inside a striped tube; each pad bounce earns $. Buy candies, merge 2 of the same level, add pads.

const TR = 30.0
const G = 1500.0
const KICK = 960.0
const MAXBALLS = 30
const PADLEN = 120.0
const SLOTS = [0.5, 0.4, 0.6, 0.3, 0.7, 0.2, 0.8, 0.12, 0.88]
const PENTA = [0, 2, 4, 7, 9]
const CARDS = [Rect2(42, 1028, 196, 212), Rect2(262, 1028, 196, 212), Rect2(482, 1028, 196, 212)]
const MAPBTN = Rect2(34, 148, 76, 76)
const SKINBTN = Rect2(34, 238, 76, 76)
const SKINS = [
	{"id": "candy", "name": "CANDY", "how": "start", "col": "#ff5fa2", "objs": ["Dragee", "Hard Candy", "Marshmallow", "Bubble Gum", "Cookie", "Donut", "Cupcake", "Lollipop", "Cake", "Golden Candy"]},
	{"id": "fruits", "name": "FRUITS", "how": "boss", "boss": 5, "col": "#ff5d73", "objs": ["Blueberry", "Cherry", "Strawberry", "Lemon", "Orange", "Apple", "Peach", "Pineapple", "Melon", "Watermelon"]},
	{"id": "space", "name": "SPACE", "how": "boss", "boss": 10, "col": "#6a4ee0", "objs": ["Stardust", "Asteroid", "Moon", "Mars", "Earth", "Neptune", "Saturn", "Jupiter", "Sun", "Black Hole"]},
	{"id": "gems", "name": "GEMS", "how": "boss", "boss": 15, "col": "#3fbfd9", "objs": ["Quartz", "Amethyst", "Topaz", "Emerald", "Sapphire", "Ruby", "Opal", "Pink Diamond", "Black Pearl", "Diamond"]},
	{"id": "donuts", "name": "DONUTS", "how": "boss", "boss": 25, "col": "#ff8fc6", "objs": ["Mini Donut", "Glazed", "Sprinkled", "Choco", "Strawberry", "Matcha", "Caramel", "Rainbow", "Cream Filled", "Golden Donut"]},
	{"id": "icecream", "name": "ICE CREAM", "how": "boss", "boss": 30, "col": "#8fd8ff", "objs": ["Sorbet", "Vanilla", "Strawberry", "Mint", "Choco", "Cone", "Double Cone", "Sundae", "Banana Split", "Golden Scoop"]},
	{"id": "cookies", "name": "COOKIES", "how": "boss", "boss": 35, "col": "#c97a3a", "objs": ["Crumb", "Biscuit", "Choc Chip", "Oreo", "Ginger Star", "Macaron", "Shortbread", "Gingerbread", "Cookie Jar", "Golden Cookie"]},
	{"id": "jellybeans", "name": "JELLY BEANS", "how": "boss", "boss": 40, "col": "#7df0c8", "objs": ["Tiny Bean", "Lime", "Cherry", "Lemon", "Grape", "Orange", "Blueberry", "Bubblegum", "Rainbow", "Golden Bean"]},
	{"id": "planets", "name": "CANDY PLANETS", "how": "boss", "boss": 45, "col": "#9b7bff", "objs": ["Comet", "Mint Moon", "Berry World", "Caramel Rock", "Gum Giant", "Ice Planet", "Ring World", "Lava Candy", "Twin Stars", "Candy Sun"]},
	{"id": "clouds", "name": "COTTON CLOUDS", "how": "boss", "boss": 50, "col": "#ff9fd0", "objs": ["Puff", "Pink Puff", "Blue Puff", "Swirl", "Rain Cloud", "Rainbow", "Storm", "Big Fluff", "Dream Cloud", "Golden Cloud"]},
	{"id": "gumballs", "name": "GUMBALLS", "how": "boss", "boss": 55, "col": "#ff4d6d", "objs": ["Mini Gum", "Red Gum", "Blue Gum", "Green Gum", "Yellow Gum", "Purple Gum", "Striped Gum", "Galaxy Gum", "Mega Gum", "Golden Gum"]},
	{"id": "crown", "name": "ROYAL", "how": "boss", "boss": 60, "col": "#ffd36b", "objs": ["Copper Coin", "Silver Coin", "Gold Coin", "Ruby Ring", "Sapphire Ring", "Scepter Gem", "Royal Orb", "Crown Jewel", "Golden Crown", "Sugar Throne"]},
	{"id": "star1", "name": "STAR CANDY", "how": "stars", "world": 1, "base": "candy", "col": "#ffd36b"},
	{"id": "star2", "name": "STAR GEMS", "how": "stars", "world": 2, "base": "gems", "col": "#8fd8ff"},
	{"id": "star3", "name": "STAR DONUTS", "how": "stars", "world": 3, "base": "donuts", "col": "#ff8fc6"},
	{"id": "star4", "name": "STAR BEANS", "how": "stars", "world": 4, "base": "jellybeans", "col": "#7df0c8"},
	{"id": "star5", "name": "STAR PLANETS", "how": "stars", "world": 5, "base": "planets", "col": "#c06bff"},
	{"id": "retro", "name": "RETRO", "how": "shop", "price": 800, "col": "#3fcf5f", "objs": ["Berries", "Plum", "Strawberry", "Orange", "Apple", "Peach", "Mango", "Pineapple", "Banana", "Golden Pear"]},
	{"id": "music", "name": "MUSIC", "how": "boss", "boss": 20, "col": "#ffb21e", "objs": ["Note", "Double Note", "Drum", "Maracas", "Trumpet", "Guitar", "Saxophone", "Piano", "Harp", "Gold Record"]},
]
const MILE10 = [5, 10, 16, 23, 30]
const MILE20 = [8, 16, 26, 38, 50, 60]
const TRAILS = ["rainbow", "stars", "hearts", "bubbles", "comet"]
const MELODY = [0, 4, 7, 12, 11, 7, 4, 5, 9, 12, 14, 12, 9, 7, 5, 4, 2, 4, 7, 4]
const INKH = "#4a1f52"

const CANDY_NAMES = ["Dragee", "Hard Candy", "Marshmallow", "Bubble Gum", "Cookie", "Donut", "Cupcake", "Lollipop", "Cake", "Golden Candy"]
const SHAPE_COLS = [["#ff5fa2", "#7df0c8"], ["#9b7bff", "#ffd36b"], ["#ff9a5a", "#8fd8ff"], ["#3fcf9f", "#ff8fc6"], ["#ff4d6d", "#fff1a8"], ["#2fb8a0", "#ffd36b"], ["#4a6cf0", "#ff9a2e"], ["#6a4ee0", "#ffd36b"]]
const BUCKET_Y = 925.0
const BOSS_NAMES = {"gummy": "GRUMPY GUMMY", "cupcake": "KING CUPCAKE", "choco": "CHOCO BRICK", "lolli": "LOLLIPOP LORD", "donut": "DONUT DUKE", "sundae": "SUNDAE SORCERER", "ginger": "GINGERBREAD GOLEM", "jelly": "JELLY TRIO", "mallow": "MARSHMALLOW MOON", "cloud": "COTTON CLOUD", "gumball": "GUMBALL MACHINE", "overlord": "SUGAR OVERLORD"}
const BOSS_SIZE = {"gummy": Vector2(156, 108), "cupcake": Vector2(140, 150), "choco": Vector2(180, 112), "lolli": Vector2(140, 140), "donut": Vector2(128, 128), "sundae": Vector2(120, 150), "ginger": Vector2(120, 170), "jelly": Vector2(200, 110), "mallow": Vector2(130, 130), "cloud": Vector2(190, 110), "gumball": Vector2(130, 170), "overlord": Vector2(150, 170)}
const FL_PIV = [Vector2(278, 966), Vector2(442, 966)]
const FL_LEN = 84.0
const WORLD_NAMES = ["CANDY TUBES", "SUGAR PLINKO", "FLIPPER FAIR", "PORTAL POPS", "COSMIC CANDY"]
const FL_DOWN = 0.5
const FL_UP = -0.45
const FB_SLOTS = [Vector2(360, 470), Vector2(262, 560), Vector2(458, 560), Vector2(360, 650), Vector2(230, 400), Vector2(490, 400), Vector2(250, 750), Vector2(470, 750)]
const BUCKET_MULTS = [8.0, 3.0, 1.5, 1.0, 1.5, 3.0, 8.0]

# World 1 levels. m = economy multiplier, target = $ to earn, stars = [3-star time, 2-star time] in seconds.
# Values for target / boss hp are tuned with --sim (see tune()).
var LEVELS = [
	{"shape": 0, "m": 1.0, "balls": 1, "pads": [0], "target": 60.0, "stars": [32, 50], "tut": "ball"},
	{"shape": 0, "m": 1.0, "balls": 2, "pads": [0], "target": 230.0, "stars": [45, 70], "tut": "merge"},
	{"shape": 1, "m": 2.0, "balls": 2, "pads": [0], "target": 800.0, "stars": [58, 90], "tut": "pad"},
	{"shape": 1, "m": 3.0, "balls": 3, "pads": [0, 1], "target": 8500.0, "stars": [58, 90], "tut": "candy", "gift": true},
	{"shape": 2, "m": 4.0, "balls": 4, "pads": [0, 1], "boss": 400, "bkind": "gummy", "stars": [85, 130], "gift": false},
	{"shape": 2, "m": 6.0, "balls": 3, "pads": [0, 1], "target": 18000.0, "stars": [55, 85], "tut": "stars", "gift": true},
	{"shape": 3, "m": 8.0, "balls": 3, "pads": [3, 4], "money": 200.0, "target": 64000.0, "stars": [85, 130], "gift": true},
	{"shape": 3, "m": 10.0, "balls": 2, "pads": [0], "target": 130000.0, "stars": [105, 118], "limit": 125.0, "gift": true},
	{"shape": 0, "m": 12.0, "balls": 5, "pads": [0, 1, 2], "target": 40000.0, "stars": [40, 65], "golden": 0.12, "gift": true},
	{"shape": 4, "m": 15.0, "balls": 4, "pads": [0, 1, 2], "boss": 1340, "bkind": "cupcake", "stars": [115, 170], "gift": false},
	{"world": 2, "type": "plinko", "shape": 5, "m": 20.0, "balls": 3, "pads": [], "target": 160000.0, "stars": [60, 95], "tut": "aim"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 24.0, "balls": 3, "pads": [], "target": 137000.0, "stars": [55, 85], "mults": [10.0, 2.0, 1.0, 1.0, 1.0, 2.0, 10.0], "tut": "edges"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 28.0, "balls": 3, "pads": [], "target": 450000.0, "stars": [70, 105], "moving": [2, 4], "tut": "moving"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 32.0, "balls": 3, "pads": [], "target": 290000.0, "stars": [65, 100], "mults": [8.0, 0.0, 3.0, 1.0, 3.0, 0.0, 8.0], "tut": "sour"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 36.0, "balls": 4, "pads": [], "boss": 1900, "bkind": "choco", "stars": [85, 130]},
	{"world": 2, "type": "plinko", "shape": 5, "m": 40.0, "balls": 3, "pads": [], "target": 700000.0, "stars": [60, 95], "bumpers": [Vector2(250, 600), Vector2(546, 600)], "tut": "bumper"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 45.0, "balls": 3, "pads": [], "target": 1100000.0, "stars": [75, 110], "jackpot": true, "mults": [2.0, 1.5, 1.0, 1.0, 1.0, 1.5, 2.0], "tut": "jackpot"},
	{"world": 2, "type": "plinko", "shape": 5, "m": 50.0, "balls": 2, "pads": [], "target": 900000.0, "stars": [100, 115], "limit": 122.0, "mults": [8.0, 0.0, 2.0, 0.0, 2.0, 0.0, 8.0], "moving": [1, 3, 5]},
	{"world": 2, "type": "plinko", "shape": 5, "m": 55.0, "balls": 5, "pads": [], "target": 700000.0, "stars": [40, 65], "golden": 0.12, "goldpegs": 6, "bumpers": [Vector2(398, 520)]},
	{"world": 2, "type": "plinko", "shape": 5, "m": 60.0, "balls": 4, "pads": [], "boss": 1600, "bkind": "lolli", "stars": [100, 150], "moving": [5], "bumpers": [Vector2(230, 760), Vector2(566, 760)]},
	{"world": 3, "type": "flipper", "shape": 6, "m": 70.0, "balls": 3, "pads": [], "fb": 2, "target": 110000.0, "stars": [55, 85], "tut": "flip"},
	{"world": 3, "type": "flipper", "shape": 6, "m": 80.0, "balls": 3, "pads": [], "fb": 2, "targets": 4, "target": 2300000.0, "stars": [55, 85], "tut": "targets"},
	{"world": 3, "type": "flipper", "shape": 6, "m": 90.0, "balls": 3, "pads": [], "fb": 3, "targets": 4, "movefb": true, "target": 1750000.0, "stars": [60, 95], "tut": "movefb"},
	{"world": 3, "type": "flipper", "shape": 6, "m": 100.0, "balls": 3, "pads": [], "fb": 3, "targets": 5, "super": 1, "target": 5000000.0, "stars": [60, 95], "tut": "super"},
	{"world": 3, "type": "flipper", "shape": 6, "m": 110.0, "balls": 4, "pads": [], "fb": 2, "boss": 380, "bkind": "donut", "stars": [85, 130]},
	{"world": 3, "type": "flipper", "shape": 6, "m": 120.0, "balls": 6, "pads": [], "fb": 3, "targets": 4, "target": 4000000.0, "stars": [50, 80], "tut": "multi"},
	{"world": 3, "type": "flipper", "shape": 6, "m": 135.0, "balls": 3, "pads": [], "fb": 3, "targets": 5, "super": 2, "movefb": true, "target": 6600000.0, "stars": [65, 100]},
	{"world": 3, "type": "flipper", "shape": 6, "m": 150.0, "balls": 2, "pads": [], "fb": 2, "targets": 5, "target": 5400000.0, "stars": [100, 115], "limit": 122.0, "movefb": true},
	{"world": 3, "type": "flipper", "shape": 6, "m": 170.0, "balls": 5, "pads": [], "fb": 4, "targets": 4, "super": 2, "golden": 0.12, "target": 7000000.0, "stars": [40, 65]},
	{"world": 3, "type": "flipper", "shape": 6, "m": 190.0, "balls": 4, "pads": [], "fb": 3, "boss": 370, "bkind": "sundae", "stars": [100, 150]},
	{"world": 4, "shape": 0, "cols": ["#9b7bff", "#7df0c8"], "m": 220.0, "balls": 2, "pads": [0, 1], "portals": [[Vector2(250, 760), Vector2(470, 520)]], "target": 210000.0, "stars": [55, 85], "tut": "portal"},
	{"world": 4, "shape": 1, "cols": ["#4a6cf0", "#ffd36b"], "m": 250.0, "balls": 2, "pads": [0], "portals": [[Vector2(250, 800), Vector2(470, 560)], [Vector2(470, 800), Vector2(250, 560)]], "target": 345000.0, "stars": [55, 85]},
	{"world": 4, "shape": 2, "cols": ["#3fcf9f", "#ff8fc6"], "m": 280.0, "balls": 3, "pads": [0, 1], "portals": [[Vector2(220, 720), Vector2(500, 520)]], "movp": true, "target": 395000.0, "stars": [60, 95], "tut": "movp"},
	{"world": 4, "shape": 3, "cols": ["#ff9a5a", "#8fd8ff"], "m": 310.0, "balls": 3, "pads": [0], "portals": [[Vector2(250, 780), Vector2(470, 600)]], "gold_portal": true, "target": 920000.0, "stars": [60, 95], "tut": "goldp"},
	{"world": 4, "shape": 2, "cols": ["#c97a3a", "#fff1d6"], "m": 340.0, "balls": 4, "pads": [0, 1], "portals": [[Vector2(200, 760), Vector2(520, 760)]], "boss": 1140, "bkind": "ginger", "stars": [85, 130]},
	{"world": 4, "shape": 1, "cols": ["#ff5fa2", "#7df0c8"], "m": 380.0, "balls": 3, "pads": [0, 1], "portals": [[Vector2(205, 860), Vector2(360, 470)]], "target": 360000.0, "stars": [55, 85], "tut": "trap"},
	{"world": 4, "shape": 0, "cols": ["#4a6cf0", "#ff9a2e"], "m": 420.0, "balls": 3, "pads": [0], "portals": [[Vector2(260, 760), Vector2(460, 520)], [Vector2(460, 760), Vector2(260, 520)]], "movp": true, "target": 1170000.0, "stars": [65, 100]},
	{"world": 4, "shape": 3, "cols": ["#9b7bff", "#ffd36b"], "m": 460.0, "balls": 2, "pads": [0], "portals": [[Vector2(250, 760), Vector2(470, 560)]], "movp": true, "target": 1700000.0, "stars": [100, 115], "limit": 122.0},
	{"world": 4, "shape": 0, "cols": ["#ffd36b", "#ff5fa2"], "m": 500.0, "balls": 5, "pads": [0, 1, 2], "portals": [[Vector2(250, 760), Vector2(470, 520)]], "gold_portal": true, "golden": 0.12, "target": 1300000.0, "stars": [40, 65]},
	{"world": 4, "shape": 4, "cols": ["#3fcf9f", "#ff8fc6"], "m": 550.0, "balls": 4, "pads": [0, 1, 2], "portals": [[Vector2(200, 700), Vector2(520, 700)]], "boss": 2100, "bkind": "jelly", "stars": [100, 150]},
	{"world": 5, "type": "space", "shape": 7, "m": 600.0, "balls": 2, "pads": [], "planets": [Vector2(360, 640)], "target": 718000.0, "stars": [55, 85], "tut": "orbit"},
	{"world": 5, "type": "space", "shape": 7, "m": 650.0, "balls": 2, "pads": [], "planets": [Vector2(360, 640)], "moons": 1, "target": 1100000.0, "stars": [55, 85], "tut": "moon"},
	{"world": 5, "type": "space", "shape": 7, "m": 700.0, "balls": 3, "pads": [], "planets": [Vector2(270, 560), Vector2(450, 720)], "target": 1400000.0, "stars": [60, 95], "tut": "two"},
	{"world": 5, "type": "space", "shape": 7, "m": 760.0, "balls": 3, "pads": [], "planets": [Vector2(360, 640)], "moons": 1, "hole": Vector2(520, 470), "target": 448000.0, "stars": [60, 95], "tut": "hole"},
	{"world": 5, "type": "space", "shape": 7, "m": 820.0, "balls": 4, "pads": [], "planets": [Vector2(360, 780)], "moons": 1, "boss": 777, "bkind": "mallow", "stars": [85, 130]},
	{"world": 5, "type": "space", "shape": 7, "m": 900.0, "balls": 3, "pads": [], "planets": [Vector2(360, 640)], "moons": 2, "comets": true, "target": 2900000.0, "stars": [55, 85], "tut": "comet"},
	{"world": 5, "type": "space", "shape": 7, "m": 980.0, "balls": 3, "pads": [], "planets": [Vector2(360, 640)], "moons": 1, "movplanet": true, "target": 1690000.0, "stars": [65, 100], "tut": "movplanet"},
	{"world": 5, "type": "space", "shape": 7, "m": 1060.0, "balls": 2, "pads": [], "planets": [Vector2(270, 560), Vector2(450, 720)], "hole": Vector2(360, 640), "target": 2400000.0, "stars": [100, 115], "limit": 122.0},
	{"world": 5, "type": "space", "shape": 7, "m": 1150.0, "balls": 5, "pads": [], "planets": [Vector2(360, 640)], "moons": 3, "comets": true, "golden": 0.12, "target": 3800000.0, "stars": [40, 65]},
	{"world": 5, "type": "space", "shape": 7, "m": 1250.0, "balls": 4, "pads": [], "planets": [Vector2(360, 800)], "moons": 2, "boss": 1320, "bkind": "cloud", "stars": [100, 150]},
	{"world": 5, "shape": 0, "cols": ["#6a4ee0", "#7df0c8"], "space_bg": true, "grav": 0.55, "m": 1350.0, "balls": 3, "pads": [0, 1], "portals": [[Vector2(250, 760), Vector2(470, 520)]], "target": 1567000.0, "stars": [55, 85], "tut": "remix"},
	{"world": 5, "type": "plinko", "shape": 5, "cols": ["#6a4ee0", "#ffd36b"], "space_bg": true, "grav": 0.6, "m": 1450.0, "balls": 3, "pads": [], "mults": [10.0, 3.0, 1.0, 0.0, 1.0, 3.0, 10.0], "target": 5700000.0, "stars": [60, 95]},
	{"world": 5, "type": "flipper", "shape": 6, "cols": ["#6a4ee0", "#ff9a2e"], "space_bg": true, "grav": 0.65, "m": 1550.0, "balls": 3, "pads": [], "fb": 3, "targets": 4, "super": 1, "target": 94000000.0, "stars": [60, 95]},
	{"world": 5, "type": "space", "shape": 7, "m": 1650.0, "balls": 3, "pads": [], "planets": [Vector2(270, 560), Vector2(450, 720)], "moons": 2, "hole": Vector2(520, 480), "comets": true, "target": 1300000.0, "stars": [65, 100]},
	{"world": 5, "type": "space", "shape": 7, "m": 1750.0, "balls": 4, "pads": [], "planets": [Vector2(360, 800)], "moons": 2, "boss": 1790, "bkind": "gumball", "stars": [100, 150]},
	{"world": 5, "shape": 4, "cols": ["#9b7bff", "#ffd36b"], "space_bg": true, "grav": 0.5, "m": 1900.0, "balls": 3, "pads": [0, 1], "portals": [[Vector2(200, 700), Vector2(520, 700)]], "gold_portal": true, "movp": true, "target": 8000000.0, "stars": [60, 95]},
	{"world": 5, "type": "plinko", "shape": 5, "cols": ["#6a4ee0", "#ff8fc6"], "space_bg": true, "grav": 0.6, "m": 2050.0, "balls": 3, "pads": [], "jackpot": true, "mults": [2.0, 1.5, 1.0, 1.0, 1.0, 1.5, 2.0], "moving": [2, 4], "target": 21000000.0, "stars": [70, 105]},
	{"world": 5, "type": "flipper", "shape": 6, "cols": ["#6a4ee0", "#7df0c8"], "space_bg": true, "grav": 0.65, "m": 2200.0, "balls": 2, "pads": [], "fb": 3, "targets": 5, "movefb": true, "target": 167000000.0, "stars": [100, 115], "limit": 122.0},
	{"world": 5, "type": "space", "shape": 7, "m": 2400.0, "balls": 6, "pads": [], "planets": [Vector2(360, 640)], "moons": 4, "comets": true, "golden": 0.15, "target": 7000000.0, "stars": [40, 65]},
	{"world": 5, "type": "space", "shape": 7, "m": 2600.0, "balls": 4, "pads": [], "planets": [Vector2(270, 760), Vector2(450, 760)], "moons": 2, "comets": true, "boss": 2290, "bkind": "overlord", "stars": [120, 180]},
]
const BOSS_SKINS = {4: "fruits", 9: "space", 14: "gems", 19: "music", 24: "donuts", 29: "icecream", 34: "cookies", 39: "jellybeans", 44: "planets", 49: "clouds", 54: "gumballs", 59: "crown"}

var font: Font
var rng = RandomNumberGenerator.new()

# save
var coins = 0
var best_stars = {}
var unlocked = 1
var seen = {1: true}
var skins = {"candy": true}
var equip = "candy"
var sel_skin = 0
var skins_from = "play"
var mel_i = 0
var tex = {}
var claimed = {}
var boost_gold = 0
var boost_time = 0
var trail_style = ""
var skin_page = 0
var map_scroll = 0.0
var map_drag = false
var map_moved = false
var map_last = 0.0
var prev_state = ""
var base_off = Vector2.ZERO
var overtime = false
var gift_day = 0
var gift_date = ""
var book_page = 0
var book_from = "skins"
var icon_v = 0
var mus_on = true
var sfx_on = true
var vib_on = true
var music_player = null
var cur_track = ""
var set_from = "play"
var want_screen = ""
var pegs = []
var buckets = []
var spout_x = 360.0
var spout_tx = 360.0
var drop_t = 0.0
var boosts = 0
var only_level = -1
var bumpers = []
var jack_t = 0.0
var jack_i = -1
var map_world = 1
var fbumps = []
var ftargets = []
var flips = [{"a": FL_DOWN, "pa": FL_DOWN, "hold": false, "t": 0.0}, {"a": FL_DOWN, "pa": FL_DOWN, "hold": false, "t": 0.0}]
var tbonus = 0.0
var portals = []
var planets = []
var moons = []
var hole = null
var comet = null
var comet_t = 6.0
var my_song_on = false
var my_song_ok = false
var song_player = null
var song_until = 0.0
const SETBTN = Rect2(34, 328, 76, 76)

# run
var li = 0
var L = {}
var money = 0.0
var earned = 0.0
var nb = 0
var nm = 0
var np = 0
var balls = []
var pads = []
var shp = {}
var parts = []
var floats = []
var gift = null
var gift_timer = 6.0
var boss = null
var hist = []
var t = 0.0
var lt = 0.0
var shake = 0.0
var hitstop = 0.0
var slowmo = 0.0
var flash = 0.0
var banner = null
var ending = -1.0
var state = "play"
var endinfo = {}
var popup = null
var autoplay = false
var sim = false
var bot_t = 0.0
var card_press = [0.0, 0.0, 0.0]
var players = []
var pidx = 0
var sfx = {}
var last_pop = 0.0
var combo = 0
var combo_t = 0.0
var bgtex = null
var show_map_only = false
var demo = false
var tut_done = {}
var screen_t = 0.0
var tune_mode = false

# ================================================================ helpers
func C(h: String, mul = 1.0, a = 1.0) -> Color:
	var c = Color(h).srgb_to_linear()
	return Color(c.r * mul, c.g * mul, c.b * mul, a)

func INK() -> Color:
	return C(INKH)

func gray(c: Color) -> Color:
	var l = c.r * 0.3 + c.g * 0.59 + c.b * 0.11
	return Color(l * 1.1, l * 1.05, l * 1.15, c.a)

func fmt(n: float) -> String:
	if n < 1000.0:
		return str(int(floor(n)))
	var units = ["k", "m", "b", "t", "q"]
	var v = n
	var i = -1
	while v >= 1000.0 and i < units.size() - 1:
		v /= 1000.0
		i += 1
	if v < 100.0:
		return "%.1f%s" % [v, units[i]]
	return "%d%s" % [int(v), units[i]]

func ftime(s: float) -> String:
	var x = int(ceil(maxf(0.0, s)))
	return "%d:%02d" % [x / 60, x % 60]

func rrect(r: Rect2, col: Color, rad = 14, border = 0, bcol = Color.BLACK, center = true, corners = [1, 1, 1, 1]) -> void:
	var s = StyleBoxFlat.new()
	s.bg_color = col
	s.draw_center = center
	s.corner_radius_top_left = rad * corners[0]
	s.corner_radius_top_right = rad * corners[1]
	s.corner_radius_bottom_right = rad * corners[2]
	s.corner_radius_bottom_left = rad * corners[3]
	s.anti_aliasing = true
	if border > 0:
		s.set_border_width_all(border)
		s.border_color = bcol
	draw_style_box(s, r)

func text_c(pos: Vector2, s: String, size: int, col: Color, outline = 8, ocol = null) -> void:
	var w = font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var p = Vector2(pos.x - w / 2.0, pos.y + size * 0.35)
	var oc: Color = INK() if ocol == null else ocol
	if outline > 0:
		draw_string_outline(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, outline, oc)
	draw_string(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func text_l(pos: Vector2, s: String, size: int, col: Color, outline = 8, right = false) -> void:
	var w = font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
	var p = Vector2(pos.x - (w if right else 0.0), pos.y + size * 0.35)
	if outline > 0:
		draw_string_outline(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, outline, INK())
	draw_string(font, p, s, HORIZONTAL_ALIGNMENT_LEFT, -1, size, col)

func load_wav(path: String):
	if not FileAccess.file_exists(path):
		return null
	var f = FileAccess.open(path, FileAccess.READ)
	var bytes = f.get_buffer(f.get_length())
	var s = AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = 44100
	s.stereo = false
	s.data = bytes.slice(44)
	return s

func play(name: String, pitch = 1.0, vol = 0.0) -> void:
	if sim or not sfx_on or not sfx.has(name) or sfx[name] == null:
		return
	var p: AudioStreamPlayer = players[pidx]
	pidx = (pidx + 1) % players.size()
	p.stream = sfx[name]
	p.pitch_scale = pitch
	p.volume_db = vol
	p.play()

func buzz(ms = 18) -> void:
	if not sim and not autoplay and vib_on:
		Input.vibrate_handheld(ms)

func semis(i: int) -> float:
	var o = int(floor(i / 5.0))
	return pow(2.0, (o * 12 + PENTA[((i % 5) + 5) % 5]) / 12.0)

# ================================================================ economy
func m() -> float: return L.m
func val(lv: int) -> float: return pow(3.0, lv - 1) * m()
func is_boss() -> bool: return L.has("boss")
func is_plinko() -> bool: return L.get("type", "") == "plinko"
func is_flipper() -> bool: return L.get("type", "") == "flipper"
func queued_world() -> bool: return is_plinko() or is_flipper()
func is_space() -> bool: return L.get("type", "") == "space"
func grav() -> float: return L.get("grav", 1.0)
func cost_boost() -> float: return round(15.0 * pow(2.0, boosts) * m())
func boost_mult() -> float: return pow(1.5, boosts)
func lvl_label() -> String:
	return "LEVEL " + lvl_name(li)

func lvl_name(i: int) -> String:
	var w = LEVELS[i].get("world", 1) if i < LEVELS.size() else 1
	return str(i + 1) if w == 1 else "%d-%d" % [w, i - (w - 1) * 10 + 1]
func target() -> float: return L.get("target", 0.0)
func cost_ball() -> float: return round(3.0 * pow(1.28, nb) * m())
func cost_merge() -> float: return round(5.0 * pow(1.42, nm) * m())
func cost_pad() -> float: return round(12.0 * pow(2.0, np) * m())
func rate() -> float:
	var s = 0.0
	for h in hist:
		s += h[1]
	return s / 5.0

# ================================================================ shapes
func catmull(ctrl: Array, step = 10.0) -> PackedVector2Array:
	var out = PackedVector2Array()
	var n = ctrl.size()
	for i in range(n - 1):
		var p0: Vector2 = ctrl[max(i - 1, 0)]
		var p1: Vector2 = ctrl[i]
		var p2: Vector2 = ctrl[i + 1]
		var p3: Vector2 = ctrl[min(i + 2, n - 1)]
		var k = int(ceil(p1.distance_to(p2) / step))
		for j in range(k):
			var u = float(j) / k
			out.append(0.5 * ((2.0 * p1) + (-p0 + p2) * u + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * u * u + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * u * u * u))
	out.append(ctrl[n - 1])
	return out

func make_shape(idx: int) -> Dictionary:
	var pts = PackedVector2Array()
	var net = false
	match idx:
		0:
			var c = Vector2(360, 650)
			for k in range(121):
				var a = lerpf(deg_to_rad(-57.0), deg_to_rad(237.0), k / 120.0)
				pts.append(c + Vector2(cos(a), sin(a)) * 270.0)
			net = true
		1:
			pts = catmull([Vector2(268, 330), Vector2(268, 470), Vector2(160, 620), Vector2(118, 790), Vector2(160, 930), Vector2(262, 978), Vector2(458, 978), Vector2(560, 930), Vector2(602, 790), Vector2(560, 620), Vector2(452, 470), Vector2(452, 330)])
		2:
			pts = catmull([Vector2(110, 360), Vector2(104, 620), Vector2(150, 860), Vector2(268, 975), Vector2(452, 975), Vector2(570, 860), Vector2(616, 620), Vector2(610, 360)])
		3:
			pts = catmull([Vector2(262, 392), Vector2(140, 560), Vector2(112, 730), Vector2(190, 905), Vector2(300, 975), Vector2(420, 975), Vector2(530, 905), Vector2(608, 730), Vector2(580, 560), Vector2(458, 392)])
			net = true
		4:
			# heart-like bowl for the world boss
			pts = catmull([Vector2(300, 420), Vector2(220, 360), Vector2(120, 420), Vector2(96, 580), Vector2(170, 780), Vector2(290, 920), Vector2(360, 975), Vector2(430, 920), Vector2(550, 780), Vector2(624, 580), Vector2(600, 420), Vector2(500, 360), Vector2(420, 420)])
			net = true
		5:
			# plinko board: tall rounded box, open at the top
			pts = catmull([Vector2(156, 300), Vector2(150, 640), Vector2(152, 940), Vector2(192, 1000), Vector2(398, 1004), Vector2(604, 1000), Vector2(642, 940), Vector2(644, 640), Vector2(638, 300)])
		7:
			var c7 = Vector2(360, 640)
			for k in range(145):
				var a7 = k * TAU / 144.0
				pts.append(c7 + Vector2(cos(a7), sin(a7)) * 300.0)
		6:
			# pinball table: arched roof, funnel down to the two flippers
			pts = catmull([Vector2(268, 972), Vector2(150, 860), Vector2(134, 620), Vector2(150, 360), Vector2(230, 252), Vector2(360, 224), Vector2(490, 252), Vector2(570, 360), Vector2(586, 620), Vector2(570, 860), Vector2(452, 972)])
	var cum = PackedFloat32Array([0.0])
	for i in range(1, pts.size()):
		cum.append(cum[i - 1] + pts[i].distance_to(pts[i - 1]))
	var ctr = Vector2(360, 690)
	var nrm = PackedVector2Array()
	for i in range(pts.size()):
		var a: Vector2 = pts[max(i - 1, 0)]
		var b: Vector2 = pts[min(i + 1, pts.size() - 1)]
		var tg = (b - a).normalized()
		var n = Vector2(-tg.y, tg.x)
		if n.dot(ctr - pts[i]) < 0:
			n = -n
		nrm.append(n)
	var top = 9999.0
	for p in pts:
		top = min(top, p.y)
	var cc = L.get("cols", SHAPE_COLS[idx]) if L != null and L.size() > 0 else SHAPE_COLS[idx]
	return {"pts": pts, "cum": cum, "len": cum[cum.size() - 1], "nrm": nrm, "net": net, "col": cc[0], "padc": cc[1], "spawn": Vector2(360, top + 70), "top": top}

func at_s(s: float) -> Array:
	var cum: PackedFloat32Array = shp.cum
	var pts: PackedVector2Array = shp.pts
	var nrm: PackedVector2Array = shp.nrm
	s = clampf(s, 0.0, shp.len)
	var i = clampi(cum.bsearch(s) - 1, 0, pts.size() - 2)
	var seg = cum[i + 1] - cum[i]
	var u = 0.0 if seg <= 0.0 else (s - cum[i]) / seg
	return [pts[i].lerp(pts[i + 1], u), nrm[i].lerp(nrm[i + 1], u).normalized()]

# ================================================================ lifecycle
func _ready() -> void:
	rng.randomize()
	var ff = FontFile.new()
	ff.load_dynamic_font("res://fonts/LilitaOne.ttf")
	font = ff
	for n in ["pop1", "pop2", "pop3", "pop4", "pop5", "match1", "match2", "match3", "match4", "match5", "match6", "match7", "match8", "match9", "buy", "pad", "hit", "bosshit", "cash", "ko", "clear", "drop", "spawn", "fail", "swipe", "fruit_pop1", "fruit_pop2", "fruit_pop3", "fruit_merge", "gem_pop1", "gem_pop2", "gem_pop3", "gem_merge", "marimba", "chord", "space_pop1", "space_pop2", "space_pop3", "space_merge", "space_spawn", "retro_pop", "retro_merge", "retro_spawn"]:
		sfx[n] = load_wav("res://snd/%s.wav" % n)
	for i in range(20):
		var p = AudioStreamPlayer.new()
		add_child(p)
		players.append(p)
	var we = WorldEnvironment.new()
	var e = Environment.new()
	e.background_mode = Environment.BG_CANVAS
	e.glow_enabled = true
	e.glow_intensity = 0.8
	e.glow_strength = 1.0
	e.glow_hdr_threshold = 1.0
	e.glow_blend_mode = Environment.GLOW_BLEND_MODE_ADDITIVE
	we.environment = e
	add_child(we)
	var start = -1
	for a in OS.get_cmdline_user_args():
		if a == "--autoplay":
			autoplay = true
		elif a == "--tune":
			sim = true
			autoplay = true
			tune_mode = true
		elif a == "--sim":
			sim = true
			autoplay = true
		elif a == "--map":
			show_map_only = true
		elif a == "--demo":
			demo = true
		elif a.begins_with("--level="):
			start = int(a.substr(8)) - 1
		elif a.begins_with("--only="):
			only_level = int(a.substr(7)) - 1
		elif a.begins_with("--iconv="):
			icon_v = int(a.substr(8))
		elif a.begins_with("--bookpage="):
			book_page = int(a.substr(11))
		elif a.begins_with("--screen="):
			want_screen = a.substr(9)
		elif a.begins_with("--song="):
			import_song(a.substr(7))
			my_song_on = true
		elif a.begins_with("--skin="):
			equip = a.substr(7)
		elif a.begins_with("--seed="):
			rng.seed = int(a.substr(7))
	if not autoplay and not demo and not show_map_only:
		load_save()
	if tune_mode:
		run_tune()
		return
	var today = Time.get_date_string_from_system()
	var daily_due = not autoplay and not demo and not show_map_only and gift_date != today
	if sim:
		run_sim()
		return
	li = clampi(start if start >= 0 else unlocked - 1, 0, LEVELS.size() - 1)
	start_level(li)
	if show_map_only:
		state = "map"
		map_world = L.get("world", 1)
		var mb = (map_world - 1) * 10
		unlocked = mb + 7
		for k in range(mb + 6):
			best_stars[k] = [3, 2, 3, 1, 3, 2][k % 6]
		claimed = {"%d:0" % map_world: true}
		prev_state = "x"
	if daily_due:
		state = "daily"
		popup = {"t": 0.0}
	if want_screen == "daily":
		gift_day = 2
		popup = {"t": 0.0}
	if want_screen == "book":
		for sk in SKINS:
			skins[sk.id] = true
			for lv in range(1, 11):
				seen["%s:%d" % [sk.id, lv]] = true
	if want_screen != "":
		coins = 640
		skins = {"candy": true, "fruits": true, "retro": true}
		for k in range(1, 8):
			seen["candy:%d" % k] = true
		for k in range(1, 5):
			seen["fruits:%d" % k] = true
		state = want_screen
		sel_skin = 1
	if demo:
		for i in range(3):
			add_pad_slot(pads.size() + 1, true)
		for lv in [1, 1, 2, 3, 4, 5, 6, 7]:
			spawn_ball(lv, true)
		earned = target() * 0.62
		money = 900.0 * m()
		gift = {"pos": Vector2(410, 690), "hp": 23, "max": 30, "wob": 0.0, "born": 1.0}
		banner = null

func load_save() -> void:
	var cf = ConfigFile.new()
	if cf.load("user://save.cfg") == OK:
		coins = cf.get_value("p", "coins", 0)
		best_stars = cf.get_value("p", "stars", {})
		unlocked = cf.get_value("p", "unlocked", 1)
		seen = cf.get_value("p", "seen", {1: true})
		skins = cf.get_value("p", "skins", {"candy": true})
		tut_done = cf.get_value("p", "tut", {})
		equip = cf.get_value("p", "equip", "candy")
		mus_on = cf.get_value("p", "music", true)
		sfx_on = cf.get_value("p", "sfx", true)
		vib_on = cf.get_value("p", "vib", true)
		my_song_on = cf.get_value("p", "mysong", false)
		claimed = cf.get_value("p", "claimed", {})
		boost_gold = cf.get_value("p", "bgold", 0)
		boost_time = cf.get_value("p", "btime", 0)
		trail_style = cf.get_value("p", "trail", "")
		gift_day = cf.get_value("p", "gday", 0)
		gift_date = cf.get_value("p", "gdate", "")
		if FileAccess.file_exists("user://my_song.mp3") or FileAccess.file_exists("user://my_song.ogg"):
			load_my_song()

func save_game() -> void:
	if autoplay or demo:
		return
	var cf = ConfigFile.new()
	cf.set_value("p", "coins", coins)
	cf.set_value("p", "stars", best_stars)
	cf.set_value("p", "unlocked", unlocked)
	cf.set_value("p", "seen", seen)
	cf.set_value("p", "skins", skins)
	cf.set_value("p", "tut", tut_done)
	cf.set_value("p", "equip", equip)
	cf.set_value("p", "music", mus_on)
	cf.set_value("p", "sfx", sfx_on)
	cf.set_value("p", "vib", vib_on)
	cf.set_value("p", "mysong", my_song_on)
	cf.set_value("p", "claimed", claimed)
	cf.set_value("p", "bgold", boost_gold)
	cf.set_value("p", "btime", boost_time)
	cf.set_value("p", "trail", trail_style)
	cf.set_value("p", "gday", gift_day)
	cf.set_value("p", "gdate", gift_date)
	cf.save("user://save.cfg")

func start_level(i: int) -> void:
	li = i
	L = LEVELS[i]
	shp = make_shape(L.shape)
	balls.clear(); pads.clear(); parts.clear(); floats.clear(); hist.clear()
	overtime = false
	money = L.get("money", 0.0); earned = 0.0; nb = 0; nm = 0; np = 0; lt = 0.0
	ending = -1.0; state = "play"; popup = null; endinfo = {}
	gift = null; gift_timer = 5.0 if L.get("tut", "") == "candy" else 9.0; boss = null
	for sidx in L.pads:
		add_pad_slot(sidx, true)
	pegs.clear(); buckets.clear(); boosts = 0; spout_x = 398.0; spout_tx = 398.0; drop_t = 0.4
	bumpers.clear(); jack_t = 0.0; jack_i = -1
	fbumps.clear(); ftargets.clear(); tbonus = 0.0
	portals.clear(); planets.clear(); moons.clear(); hole = null; comet = null; comet_t = 6.0
	for pl in L.get("planets", []):
		planets.append({"p": pl, "b": pl, "r": 62.0 if L.get("planets", []).size() == 1 else 48.0, "f": 0.0})
	for k in range(int(L.get("moons", 0))):
		add_moon(true)
	if L.has("hole"):
		hole = {"p": L.hole, "f": 0.0}
	if L.get("world", 1) == 5 and li == 40:
		banner = {"t": 0.0, "txt": "WORLD 5", "col": "#ffd36b", "big": true}
	for pr in L.get("portals", []):
		portals.append({"a": pr[0], "b": pr[1], "ba": pr[0], "bb": pr[1], "f": 0.0})
	if L.get("world", 1) == 4 and li == 30:
		banner = {"t": 0.0, "txt": "WORLD 4", "col": "#ffd36b", "big": true}
	for f in flips:
		f.a = FL_DOWN; f.pa = FL_DOWN; f.hold = false; f.t = 0.0
	if is_flipper():
		for k in range(int(L.get("fb", 2))):
			add_fbump(k, true)
		var nt = int(L.get("targets", 0))
		for k in range(nt):
			ftargets.append({"p": Vector2(360 + (k - (nt - 1) / 2.0) * 52.0, 330), "down": false, "f": 0.0})
		for k in range(int(L.get("super", 0))):
			fbumps[k].super = true
		if li == 20:
			banner = {"t": 0.0, "txt": "WORLD 3", "col": "#ffd36b", "big": true}
	if is_plinko():
		var mov = L.get("moving", [])
		for row in range(7):
			var y = 410.0 + row * 72.0
			var n = 7 if row % 2 == 0 else 6
			for k in range(n):
				var x = 398.0 + (k - (n - 1) / 2.0) * 66.0
				var pp = Vector2(x, y)
				if is_boss() and absf(pp.x - 398.0) < 125.0 and absf(pp.y - 610.0) < 90.0:
					continue
				var skip = false
				for bp in L.get("bumpers", []):
					if pp.distance_to(bp) < 60.0:
						skip = true
				if skip:
					continue
				pegs.append({"p": pp, "bx": x, "row": row, "f": 0.0, "gold": (row == 3 and k == n / 2), "mv": mov.has(row)})
		var ng = L.get("goldpegs", 0)
		for k in range(ng):
			pegs[rng.randi() % pegs.size()].gold = true
		for bp in L.get("bumpers", []):
			bumpers.append({"p": bp, "f": 0.0})
		var ms = L.get("mults", BUCKET_MULTS)
		var bw = (630.0 - 166.0) / ms.size()
		for k in range(ms.size()):
			buckets.append({"x0": 166.0 + k * bw, "x1": 166.0 + (k + 1) * bw, "m": ms[k], "base": ms[k], "f": 0.0})
		if li == 10:
			banner = {"t": 0.0, "txt": "WORLD 2", "col": "#ffd36b", "big": true}
	banner = {"t": 0.0, "txt": "LEVEL " + lvl_name(i), "col": "#ffffff", "big": false}
	if is_boss():
		var hp = int(L.boss)
		var kind = L.get("bkind", "gummy")
		var sz: Vector2 = BOSS_SIZE[kind]
		boss = {"pos": Vector2(360, 600), "hp": hp, "max": hp, "w": sz.x, "h": sz.y, "wob": 0.0, "t": 0.0, "dead": 0.0, "kind": kind, "shield": false, "rot": 0.0, "tp": 0}
		if is_plinko():
			boss.pos = Vector2(398, 610)
		elif is_flipper():
			boss.pos = Vector2(360, 520)
		elif is_space():
			boss.pos = Vector2(360, 500)
		banner = {"t": 0.0, "txt": BOSS_NAMES[kind] + "!", "col": "#ff4d6d", "big": false}
	for k in range(int(L.balls)):
		spawn_ball(1, true)
	if boost_gold > 0 and not autoplay and not demo:
		boost_gold -= 1
		balls[balls.size() - 1].gold = true
		banner = {"t": 0.0, "txt": "BOOSTER: GOLDEN CANDY!", "col": "#ffd36b", "big": false}
		save_game()

func add_pad_slot(sidx: int, quiet = false) -> void:
	var mid: float = SLOTS[sidx] * shp.len
	pads.append({"slot": sidx, "s0": mid - PADLEN / 2.0, "s1": mid + PADLEN / 2.0, "f": 1.0})
	if not quiet:
		var a = at_s(mid)
		var p: Vector2 = a[0] + a[1] * TR * 0.6
		burst(p, C(shp.padc, 1.6), 24, 320.0, 4.0, 0.6)
		ring(p, C(shp.padc, 1.4), 90.0)

func free_slots() -> Array:
	var used = {}
	for pd in pads:
		used[pd.slot] = true
	var out = []
	for k in range(SLOTS.size()):
		if not used.has(k):
			out.append(k)
	return out

func spawn_ball(lv: int, quiet = false) -> void:
	var sp: Vector2 = shp.spawn + Vector2(rng.randf_range(-40, 40), 0)
	if is_space():
		sp = Vector2(200 + rng.randf_range(-40, 40), 430)
	var gold = rng.randf() < L.get("golden", 0.015) and not quiet
	balls.append({"p": sp, "v": Vector2(rng.randf_range(-120, 120), 60) if not is_space() else Vector2(rng.randf_range(80, 160), 0), "lv": lv, "r": rad(lv), "tr": [], "cd": 0.0, "sq": 0.0, "mg": null, "rot": rng.randf() * TAU, "gold": gold, "q": queued_world(), "lift": -1.0})
	if gold:
		banner = {"t": 0.0, "txt": "GOLDEN CANDY! x10", "col": "#ffd36b", "big": false}
		burst(sp, C("#ffd36b", 2.0), 30, 300.0, 4.0, 0.7)
		play("drop", 1.2, -4.0)
	elif not quiet:
		burst(sp, C("#ffffff", 1.4), 10, 160.0, 3.0, 0.35)
		snd_spawn()

func rad(lv: int) -> float:
	return 14.0 + 1.6 * (lv - 1)

func merge_pair() -> Array:
	var by = {}
	for b in balls:
		if b.mg != null or b.gold:
			continue
		if not by.has(b.lv):
			by[b.lv] = []
		by[b.lv].append(b)
	var keys = by.keys()
	keys.sort()
	for k in keys:
		if by[k].size() >= 2 and k < 10:
			return [by[k][0], by[k][1]]
	return []

# ================================================================ actions
func can_ball() -> bool: return state == "play" and ending < 0 and balls.size() < MAXBALLS and money >= cost_ball()
func can_merge() -> bool: return state == "play" and ending < 0 and merge_pair().size() == 2 and money >= cost_merge()
func can_pad() -> bool:
	if is_space():
		return state == "play" and ending < 0 and moons.size() < 6 and money >= cost_pad()
	if is_flipper():
		return state == "play" and ending < 0 and fbumps.size() < FB_SLOTS.size() and money >= cost_pad()
	if is_plinko():
		return state == "play" and ending < 0 and boosts < 8 and money >= cost_boost()
	return state == "play" and ending < 0 and free_slots().size() > 0 and money >= cost_pad()

func act(i: int) -> void:
	card_press[i] = 1.0
	if i == 0 and can_pad() and is_space():
		money -= cost_pad(); np += 1; add_moon(); play("pad", 1.0, -4.0); buzz()
	elif i == 0 and can_pad() and is_flipper():
		money -= cost_pad(); np += 1; add_fbump(fbumps.size()); play("pad", 1.0, -4.0); buzz()
	elif i == 0 and can_pad() and is_plinko():
		money -= cost_boost(); boosts += 1; play("pad", 1.1, -4.0); buzz()
		for bk in buckets:
			bk.f = 1.0
		banner = {"t": 0.0, "txt": "BUCKETS x%.1f" % boost_mult(), "col": "#ffd36b", "big": false}
	elif i == 0 and can_pad():
		money -= cost_pad(); np += 1; add_pad_slot(free_slots()[0]); play("pad", 1.0, -4.0); buzz(); tut_seen("pad")
	elif i == 1 and can_ball():
		money -= cost_ball(); nb += 1; spawn_ball(1); play("buy", 1.0, -7.0); buzz(); tut_seen("ball")
	elif i == 2 and can_merge():
		money -= cost_merge(); nm += 1
		var pr = merge_pair()
		var mid: Vector2 = (pr[0].p + pr[1].p) / 2.0
		mid.y = minf(mid.y, 900.0)
		if is_plinko():
			mid = Vector2(spout_x, 250.0)
		elif is_flipper():
			mid = Vector2(360, 300)
		for b in pr:
			b.mg = {"t": 0.0, "from": b.p, "to": mid}
		play("pop4", 1.0, -7.0); buzz(25); tut_seen("merge")

func tut_seen(k: String) -> void:
	tut_done[k] = true

func _input(ev: InputEvent) -> void:
	if state == "map":
		if ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
			if ev.pressed:
				map_drag = true; map_moved = false; map_last = get_global_mouse_position().y
				return
			else:
				map_drag = false
				if not map_moved:
					map_click(get_global_mouse_position())
				map_moved = false
				return
		if ev is InputEventMouseMotion and map_drag:
			var y = get_global_mouse_position().y
			if absf(y - map_last) > 2.0 or map_moved:
				map_scroll = clampf(map_scroll + (y - map_last), 0.0, map_max_scroll())
				if absf(y - map_last) > 6.0:
					map_moved = true
			map_last = y
			return
		return
	_input_click(ev)

func map_click(pos: Vector2) -> void:
	var ev = InputEventMouseButton.new()
	ev.button_index = MOUSE_BUTTON_LEFT
	ev.pressed = true
	ev.position = pos
	_input_click(ev, pos)

func _input_click(ev: InputEvent, forced = null) -> void:
	if state == "play" and is_flipper():
		var pp = null
		var down = false
		if ev is InputEventScreenTouch:
			pp = get_canvas_transform().affine_inverse() * ev.position
			down = ev.pressed
		elif ev is InputEventMouseButton and ev.button_index == MOUSE_BUTTON_LEFT:
			pp = get_global_mouse_position()
			down = ev.pressed
		if pp != null and pp.y > 240.0 and pp.y < 1010.0 and pp.x > 120.0:
			flips[0 if pp.x < 360.0 else 1].hold = down
			if down:
				tut_seen("flip")
				play("pop2", 0.7, -14.0)
			return
		if pp != null and not down:
			flips[0].hold = false
			flips[1].hold = false
	if not (ev is InputEventMouseButton and ev.pressed and ev.button_index == MOUSE_BUTTON_LEFT):
		return
	var pos: Vector2 = get_global_mouse_position() if forced == null else forced
	if state == "play":
		for i in range(3):
			if CARDS[i].has_point(pos):
				act(i)
		if MAPBTN.has_point(pos):
			map_world = L.get("world", 1)
			state = "map"; screen_t = 0.0; play("swipe", 1.0, -6.0)
		elif SKINBTN.has_point(pos):
			open_skins("play")
		elif SETBTN.has_point(pos):
			set_from = "play"; state = "settings"; play("swipe", 1.1, -6.0)
		elif is_plinko() and pos.y > 240 and pos.y < 1000:
			spout_tx = clampf(pos.x, 196.0, 600.0)
			tut_seen("aim")
	elif state == "end":
		if screen_t > 0.6:
			if Rect2(190, 830, 340, 92).has_point(pos):
				next_level()
			elif Rect2(250, 950, 220, 64).has_point(pos):
				state = "map"; screen_t = 0.0; play("swipe", 1.0, -6.0)
	elif state == "fail":
		if boost_time > 0 and Rect2(190, 700, 340, 84).has_point(pos):
			boost_time -= 1
			L = L.duplicate()
			L.limit = L.limit + 15.0
			state = "play"
			banner = {"t": 0.0, "txt": "+15 s!", "col": "#7df0c8", "big": true}
			play("pad", 1.2, -4.0)
			save_game()
		elif Rect2(190, 830, 340, 92).has_point(pos):
			start_level(li)
	elif state == "skins":
		skins_input(pos)
	elif state == "settings":
		settings_input(pos)
	elif state == "map":
		if map_moved:
			return
		if Rect2(600, 1180, 90, 90).has_point(pos):
			open_skins("map")
			return
		if Rect2(30, 1180, 90, 90).has_point(pos):
			set_from = "map"; state = "settings"; play("swipe", 1.1, -6.0)
			return
		for k in range(miles(map_world).size()):
			if pos.distance_to(chest_pos(map_world, k)) < 36.0:
				claim_chest(map_world, k)
				return
		var base = (map_world - 1) * 10
		var nodes = map_nodes()
		var cpos = pos - Vector2(0, map_scroll)
		if pos.y > 316 and pos.y < 1120 and Rect2(220, nodes[nodes.size() - 1].y - 200.0, 280, 64).has_point(cpos) and unlocked > base + 10 and base + 10 < LEVELS.size():
			map_world += 1; play("swipe", 1.3, -6.0); focus_map()
			return
		if map_world > 1 and Rect2(520, 1124, 170, 50).has_point(pos):
			map_world -= 1; play("swipe", 0.9, -6.0); focus_map()
			return
		for i in range(nodes.size()):
			if pos.y > 316 and pos.y < 1120 and base + i < unlocked and cpos.distance_to(nodes[i]) < 52.0:
				play("swipe", 1.2, -6.0)
				start_level(base + i)
				return
		if Rect2(180, 1170, 360, 86).has_point(pos):
			start_level(clampi(unlocked - 1, 0, LEVELS.size() - 1))
	elif state == "newcandy" or state == "drop":
		if popup != null and popup.t > 0.5:
			close_popup()
	elif state == "chest":
		if popup != null and popup.t > 0.5:
			state = "map"; popup = null
	elif state == "daily":
		if popup != null and popup.t > 0.4 and Rect2(190, 960, 340, 92).has_point(pos):
			claim_daily()
	elif state == "book":
		book_input(pos)

func next_level() -> void:
	if li + 1 < LEVELS.size():
		start_level(li + 1)
	else:
		state = "map"

# ================================================================ simulation step
func _process(dt: float) -> void:
	dt = minf(dt, 1.0 / 30.0)
	tick(dt)
	if state == "map" and prev_state != "map" and prev_state != "chest":
		focus_map()
	prev_state = state
	if not sim:
		update_music()
		drive_song()
		queue_redraw()

func tick(dt: float) -> void:
	t += dt
	screen_t += dt
	for i in range(3):
		card_press[i] = maxf(0.0, card_press[i] - dt * 6.0)
	flash = maxf(0.0, flash - dt * 3.0)
	if state == "newcandy" or state == "drop":
		popup.t += dt
		if autoplay and popup.t > 2.2:
			close_popup()
		fx(dt)
		return
	if state == "end" or state == "fail":
		fx(dt)
		if autoplay and screen_t > 3.0:
			if state == "end":
				next_level()
			else:
				start_level(li)
		return
	if state == "chest" or state == "daily":
		popup.t += dt
		fx(dt)
		return
	if state == "map" or state == "skins" or state == "settings" or state == "book":
		fx(dt)
		return
	if hitstop > 0.0:
		hitstop -= dt
		fx(dt * 0.1)
		return
	var sdt = dt * (0.35 if slowmo > 0.0 else 1.0)
	slowmo = maxf(0.0, slowmo - dt)
	if ending < 0:
		lt += sdt
	for k in range(3):
		step(sdt / 3.0)
	while hist.size() > 0 and hist[0][0] < t - 5.0:
		hist.pop_front()
	combo_t -= sdt
	if combo_t <= 0.0:
		combo = 0
	if L.get("gift", false) or L.get("tut", "") == "candy":
		if ending < 0 and gift == null:
			gift_timer -= sdt
			if gift_timer <= 0.0:
				var hp = 10 + li * 2
				gift = {"pos": Vector2(rng.randf_range(260, 460), rng.randf_range(610, 760)), "hp": hp, "max": hp, "wob": 0.0, "born": 0.0}
		elif gift != null:
			gift.born += sdt
	if boss != null:
		boss.t += sdt
		if boss.hp > 0:
			boss_ai(sdt)
	if ending < 0:
		var done = (boss != null and boss.hp <= 0) or (boss == null and earned >= target())
		if done:
			ending = 2.4 if boss != null else 1.6
			if boss == null:
				banner = {"t": 0.0, "txt": "SWEET!", "col": "#ff5fa2", "big": true}
				play("clear", 1.0, -3.0)
				confetti()
		elif L.has("limit") and lt >= L.limit and not overtime:
			if boost_time > 0:
				boost_time -= 1
				L = L.duplicate()
				L.limit = L.limit + 15.0
				banner = {"t": 0.0, "txt": "+15 s BOOSTER!", "col": "#7df0c8", "big": false}
				play("pad", 1.2, -4.0)
				save_game()
			else:
				overtime = true
				banner = {"t": 0.0, "txt": "Time's up! Keep going", "col": "#ffffff", "big": false}
				play("swipe", 0.8, -8.0)
	else:
		ending -= dt
		if ending <= 0.0:
			finish_level()
	if ending < 0 and not queued_world() and not is_space() and lt > 8.0 and rate() == 0.0 and not can_ball() and not can_pad() and not can_merge() and free_slots().has(0):
		add_pad_slot(0)
		banner = {"t": 0.0, "txt": "FREE PAD!", "col": "#7df0c8", "big": false}
		play("pad", 1.0, -4.0)
	if autoplay:
		bot(dt)
	fx(sdt)

func finish_level() -> void:
	var st = 1
	if overtime:
		st = 1
	elif lt <= L.stars[0]:
		st = 3
	elif lt <= L.stars[1]:
		st = 2
	var gain = 10 + 5 * st
	coins += gain
	best_stars[li] = max(best_stars.get(li, 0), st)
	unlocked = max(unlocked, li + 2)
	endinfo = {"stars": st, "coins": gain, "time": lt}
	screen_t = 0.0
	if BOSS_SKINS.has(li):
		var sk = skin_by_id(BOSS_SKINS[li])
		skins[sk.id] = true
		popup = {"t": 0.0, "kind": "drop", "skin": sk}
		state = "drop"
		play("drop", 1.0, -3.0)
	else:
		state = "end"
	save_game()

func close_popup() -> void:
	if state == "drop":
		state = "end"; screen_t = 0.0; popup = null
	else:
		state = "play"; popup = null

func bot(dt: float) -> void:
	bot_t -= dt
	if bot_t > 0.0 or state != "play":
		return
	bot_t = 0.45 + rng.randf() * 0.3
	if is_plinko() and jack_i >= 0 and rng.randf() < 0.6:
		spout_tx = clampf((buckets[jack_i].x0 + buckets[jack_i].x1) / 2.0, 196.0, 600.0)
	elif is_plinko() and rng.randf() < 0.3:
		spout_tx = [205.0, 398.0, 590.0][rng.randi() % 3]
		tut_seen("aim")
	if can_merge() and cost_merge() < money * 0.95:
		act(2)
	elif can_pad() and (pads.size() < 3 or cost_pad() < cost_ball() * 4.0):
		act(0)
	elif can_ball():
		act(1)
	elif can_pad():
		act(0)

func step(dt: float) -> void:
	if is_space():
		step_space(dt)
		return
	if is_flipper():
		step_flipper(dt)
		return
	if is_plinko():
		step_plinko(dt)
		return
	var pts: PackedVector2Array = shp.pts
	var cum: PackedFloat32Array = shp.cum
	var dead = []
	for b in balls:
		b.rot += b.v.x * dt * 0.01
		if b.mg != null:
			b.mg.t += dt
			var k = minf(1.0, b.mg.t / 0.3)
			b.p = b.mg.from.lerp(b.mg.to, k * k)
			if k >= 1.0:
				dead.append(b)
			continue
		b.cd -= dt
		b.v.y += G * grav() * dt
		b.p += b.v * dt
		var r: float = b.r
		var best = 1e9
		var bq = Vector2.ZERO
		var bs = 0.0
		for i in range(pts.size() - 1):
			var a = pts[i]
			if absf(a.x - b.p.x) > 70.0 or absf(a.y - b.p.y) > 70.0:
				continue
			var ab = pts[i + 1] - a
			var u = clampf((b.p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
			var q = a + ab * u
			var d = b.p.distance_to(q)
			if d < best:
				best = d; bq = q; bs = cum[i] + u * ab.length()
		if best < TR + r and best > 0.001:
			var n: Vector2 = (b.p - bq) / best
			b.p = bq + n * (TR + r)
			var vn: float = b.v.dot(n)
			if vn < 0.0:
				var pi = pad_at(bs)
				if pi >= 0:
					var dir = (n + Vector2(0, -0.55)).normalized()
					var tg = Vector2(-dir.y, dir.x)
					b.v = dir * KICK * rng.randf_range(0.92, 1.05) + tg * rng.randf_range(-170, 170)
					b.sq = 1.0
					pads[pi].f = 1.0
					if b.cd <= 0.0:
						b.cd = 0.05
						earn(b, pi, bq + n * TR * 0.6)
				else:
					b.v -= n * vn * 1.42
					b.v *= 0.97
		if portals.size() > 0:
			b.pcd = b.get("pcd", 0.0) - dt
			if b.pcd <= 0.0:
				for k in range(portals.size()):
					var po = portals[k]
					for side in [0, 1]:
						var src: Vector2 = po.a if side == 0 else po.b
						var dst: Vector2 = po.b if side == 0 else po.a
						if b.p.distance_to(src) < 30.0 + b.r * 0.5:
							b.p = dst + (b.p - src)
							b.pcd = 0.45
							var mx = 4.0 if L.get("gold_portal", false) and k == 0 else 2.0
							b.pm = minf(b.get("pm", 1.0) * mx, 16.0 if mx > 2.0 else 8.0)
							po.f = 1.0
							if not sim:
								ring(src, C("#ffffff", 1.8), 60.0, 0.3)
								ring(dst, C("#ffffff", 1.8), 60.0, 0.3)
								floats.append({"p": dst + Vector2(0, -40), "txt": "x%d" % int(b.pm), "col": "#ffd36b" if mx > 2.0 else "#8fd8ff", "t": 0.0, "big": false})
							play("swipe", 0.9 + minf(b.pm, 8.0) * 0.1, -10.0)
							break
					if b.pcd > 0.0:
						break
		if shp.net:
			var a2 = pts[0]
			var b2 = pts[pts.size() - 1]
			var ab2 = b2 - a2
			var u2 = clampf((b.p - a2).dot(ab2) / ab2.length_squared(), 0.0, 1.0)
			var q2 = a2 + ab2 * u2
			if b.p.y - r < q2.y + 6.0 and u2 > 0.0 and u2 < 1.0:
				b.p.y = q2.y + 6.0 + r
				b.v.y = absf(b.v.y) * 0.6
		if b.p.y < 150.0:
			b.p.y = 150.0; b.v.y = absf(b.v.y) * 0.5
		if b.p.y > 1150.0 or b.p.x < -50.0 or b.p.x > 770.0:
			b.p = shp.spawn; b.v = Vector2.ZERO
		if gift != null:
			hit_box(b, gift, 120.0, 70.0, false)
		if boss != null and boss.hp > 0:
			hit_box(b, boss, boss.w, boss.h, true)
		b.sq = maxf(0.0, b.sq - dt * 7.0)
	for b in dead:
		balls.erase(b)
	if dead.size() >= 2:
		var lv: int = dead[0].lv + 1
		var p: Vector2 = dead[0].mg.to
		balls.append({"p": p, "v": Vector2(rng.randf_range(-100, 100), -KICK * 0.75 * (0.0 if is_plinko() else 1.0)), "lv": lv, "r": rad(lv), "tr": [], "cd": 0.0, "sq": 1.0, "mg": null, "rot": 0.0, "gold": false, "q": queued_world(), "lift": -1.0})
		var c = C(obj_col(lv), 1.8)
		ring(p, c, 60.0 + lv * 10.0)
		ring(p, Color(2, 2, 2), 34.0 + lv * 5.0, 0.25)
		burst(p, c, 18 + lv * 4, 320.0, 4.0, 0.55)
		snd_merge(lv)
		if lv >= 4:
			hitstop = 0.05
			shake = maxf(shake, lv * 1.2)
		var sk_key = "%s:%d" % [equip, lv]
		if not seen.has(sk_key):
			seen[sk_key] = true
			popup = {"t": 0.0, "kind": "candy", "lv": lv}
			state = "newcandy"
			play("drop", 1.0, -4.0)
			save_game()
		else:
			floats.append({"p": p - Vector2(0, 30), "txt": obj_name(lv).to_upper(), "col": "#ffffff", "t": 0.0, "big": true})

func pad_at(s: float) -> int:
	for i in range(pads.size()):
		if s >= pads[i].s0 and s <= pads[i].s1:
			return i
	return -1

func hit_box(b: Dictionary, bx: Dictionary, w: float, h: float, is_b: bool) -> void:
	var c: Vector2 = bx.pos
	var q = Vector2(clampf(b.p.x, c.x - w / 2, c.x + w / 2), clampf(b.p.y, c.y - h / 2, c.y + h / 2))
	var d: float = b.p.distance_to(q)
	if d >= b.r or d < 0.001:
		return
	var n: Vector2 = (b.p - q) / d
	b.p = q + n * b.r
	var vn: float = b.v.dot(n)
	if vn < 0.0:
		b.v -= n * vn * 1.9
	if b.cd > 0.0:
		return
	b.cd = 0.06
	if is_b and bx.get("shield", false):
		bx.wob = 0.5
		play("pop2", 0.6, -12.0)
		if not sim and rng.randf() < 0.3:
			floats.append({"p": b.p + Vector2(0, -20), "txt": "BLOCK!", "col": "#8fd8ff", "t": 0.0, "big": false})
		return
	var dmg: int = b.lv * (10 if b.gold else 1)
	bx.hp = maxi(0, bx.hp - dmg)
	bx.wob = 1.0
	play("bosshit" if is_b and rng.randf() < 0.12 else "hit", rng.randf_range(0.95, 1.1) * (0.8 if is_b else 1.0), -10.0)
	burst(b.p, C("#ffffff", 1.5) if not is_b else C("#ff4d6d", 1.6), 6, 200.0, 3.0, 0.3)
	if bx.hp <= 0:
		if is_b:
			hitstop = 0.22
			slowmo = 1.0
			flash = 1.0
			shake = 22.0
			for col in ["#ff4d6d", "#ffd36b", "#ff5fa2", "#7df0c8", "#ffffff"]:
				burst(c, C(col, 2.0), 40, 640.0, 6.0, 1.2)
			ring(c, Color(2.5, 2.5, 2.5), 300.0, 0.6)
			ring(c, C("#ff5fa2", 1.8), 200.0, 0.45)
			banner = {"t": 0.0, "txt": "K.O.!", "col": "#ff4d6d", "big": true}
			play("ko", 1.0, -1.0)
			buzz(80)
			confetti()
		else:
			var rw = maxf(rate() * 25.0, 15.0 * m())
			money += rw; earned += rw
			floats.append({"p": c - Vector2(0, 40), "txt": "+$" + fmt(rw), "col": "#ffffff", "t": 0.0, "big": true})
			for col in ["#ff5fa2", "#ffd36b", "#ffffff"]:
				burst(c, C(col, 1.8), 25, 460.0, 5.0, 0.9)
			ring(c, C("#ffd36b", 1.6), 140.0, 0.45)
			play("cash", 1.0, -4.0)
			buzz(40)
			gift = null
			gift_timer = rng.randf_range(10.0, 15.0)

func earn(b: Dictionary, pi: int, at: Vector2) -> void:
	var v = val(b.lv) * (10.0 if b.gold else 1.0) * b.get("pm", 1.0)
	b.pm = 1.0
	money += v; earned += v
	hist.append([t, v])
	if not sim:
		floats.append({"p": at + Vector2(rng.randf_range(-10, 10), -16), "txt": "+$" + fmt(v), "col": "#ffd36b" if b.gold else "#ffffff", "t": 0.0, "big": false})
		if floats.size() > 40:
			floats.pop_front()
	if combo_t > 0.0:
		combo += 1
	else:
		combo = 1
	combo_t = 0.5
	if combo in [15, 30, 50, 80]:
		banner = {"t": 0.0, "txt": "x%d COMBO!" % combo, "col": "#ffd36b", "big": false}
	var now = Time.get_ticks_msec() / 1000.0
	if now - last_pop > 0.028:
		last_pop = now
		var idx: int = (b.lv - 1) * 2 + pi % 3 + int(mini(combo, 24) / 4)
		snd_bounce(idx)

# ================================================================ balancing (--sim)
func run_sim() -> void:
	# Plays every level with the bot several times at 30 fps (no rendering) and prints durations.
	var out = []
	for i in range(LEVELS.size()):
		var times = []
		var e60 = []
		for s in range(6):
			rng.seed = 1000 + s * 17 + i
			start_level(i)
			var frames = 0
			var maxf_ = 30 * 420
			var probe = {}
			while frames < maxf_ and state in ["play", "newcandy"]:
				if state == "newcandy":
					state = "play"; popup = null
				tick(1.0 / 30.0)
				frames += 1
				for mark in [30, 45, 60, 90, 120, 150]:
					if lt >= mark and not probe.has(mark):
						probe[mark] = boss.max - boss.hp if boss != null else earned
				if ending >= 0.0:
					break
			times.append(lt)
			e60.append(probe)
		out.append({"level": i + 1, "times": times, "probe": e60})
		print("SIM L%d %s" % [i + 1, str(times)])
		for pr in e60:
			print("   probe ", pr)
	get_tree().quit()

func run_tune() -> void:
	# For each level: play with the bot up to the wanted duration with an unreachable goal,
	# and print the median $ earned (or boss damage) at that time = suggested target / boss hp.
	var want = [24, 34, 45, 45, 65, 45, 65, 100, 30, 90, 60, 50, 70, 65, 85, 60, 75, 105, 38, 100, 50, 55, 60, 60, 85, 50, 65, 105, 38, 100, 50, 55, 60, 60, 85, 55, 65, 105, 38, 100, 50, 55, 60, 60, 85, 55, 65, 105, 38, 100, 55, 60, 60, 65, 100, 60, 70, 105, 38, 130]
	for i in range(LEVELS.size()):
		if only_level >= 0 and i != only_level:
			continue
		var vals = []
		for s in range(7):
			rng.seed = 500 + s * 31 + i
			start_level(i)
			L = L.duplicate()
			L.target = 1e18
			L.erase("limit")
			if boss != null:
				boss.hp = 100000000
				boss.max = 100000000
			while lt < want[i]:
				if state == "newcandy":
					state = "play"; popup = null
				tick(1.0 / 30.0)
			vals.append(boss.max - boss.hp if boss != null else earned)
		vals.sort()
		print("TUNE L%d want=%ds median=%s all=%s" % [i + 1, want[i], str(vals[3]), str(vals)])
	get_tree().quit()

# ================================================================ fx
func burst(p: Vector2, col: Color, n: int, sp: float, size: float, life: float) -> void:
	if sim:
		return
	for i in range(n):
		if parts.size() > 800:
			return
		var a = rng.randf() * TAU
		var s = sp * rng.randf_range(0.3, 1.0)
		parts.append({"p": p, "v": Vector2(cos(a), sin(a)) * s - Vector2(0, 60), "life": life * rng.randf_range(0.6, 1.2), "max": life, "col": col, "size": size * rng.randf_range(0.6, 1.3), "ring": false})

func ring(p: Vector2, col: Color, r: float, life = 0.4) -> void:
	if not sim:
		parts.append({"p": p, "r": r, "life": life, "max": life, "col": col, "ring": true})

func confetti() -> void:
	if sim:
		return
	var cols = ["#ffd36b", "#7df0c8", "#ff8fc6", "#8fd8ff", "#ffffff", "#9b7bff"]
	for i in range(120):
		parts.append({"p": Vector2(rng.randf() * 720.0, -20 - rng.randf() * 200), "v": Vector2(rng.randf_range(-60, 60), rng.randf_range(80, 220)), "life": 2.6, "max": 2.6, "col": C(cols[i % 6]), "size": 9.0, "ring": false, "conf": true, "rot": rng.randf() * TAU, "vr": rng.randf_range(-8, 8)})

func fx(dt: float) -> void:
	var keep = []
	for p in parts:
		p.life -= dt
		if p.life <= 0.0:
			continue
		if not p.ring:
			if p.has("conf"):
				p.v.y = minf(p.v.y + 120 * dt, 260)
				p.rot += p.vr * dt
			else:
				p.v.y += 700.0 * dt
				p.v *= 0.985
			p.p += p.v * dt
		keep.append(p)
	parts = keep
	var kf = []
	for f in floats:
		f.t += dt
		if f.t < (1.0 if f.big else 0.75):
			kf.append(f)
	floats = kf
	for pd in pads:
		pd.f = maxf(0.0, pd.f - dt * 6.0)
	for po in portals:
		po.f = maxf(0.0, po.f - dt * 4.0)
		if L.get("movp", false):
			po.a = po.ba + Vector2(sin(t * 0.9) * 50.0, cos(t * 0.7) * 30.0)
			po.b = po.bb + Vector2(-sin(t * 0.8) * 50.0, sin(t * 0.6) * 30.0)
	if gift != null:
		gift.wob = maxf(0.0, gift.wob - dt * 6.0)
	if boss != null:
		boss.wob = maxf(0.0, boss.wob - dt * 6.0)
	if not sim:
		for b in balls:
			b.tr.append(b.p)
			if b.tr.size() > 9:
				b.tr.pop_front()
	if banner != null:
		banner.t += dt
		if banner.t > 1.6:
			banner = null
	shake = maxf(0.0, shake - dt * 45.0)

# ================================================================ drawing
func _draw() -> void:
	if want_screen == "icon":
		draw_icon_art(icon_v)
		return
	draw_bg()
	if state == "map":
		draw_map()
		return
	if state == "chest":
		draw_map()
		draw_chest_popup()
		return
	if state == "daily":
		draw_daily()
		return
	if state == "book":
		draw_book()
		return
	if state == "skins":
		draw_skins()
		return
	if state == "settings":
		if set_from == "map":
			draw_map()
		draw_settings()
		return
	var off = Vector2(rng.randf_range(-1, 1), rng.randf_range(-1, 1)) * shake
	base_off = off
	draw_set_transform(off)
	if L.get("space_bg", false) or is_space():
		draw_space_bg()
	if not queued_world() and not is_space():
		draw_spout()
	draw_tube()
	if is_plinko():
		draw_plinko()
	elif is_flipper():
		draw_flipper()
	elif is_space():
		draw_space()
	else:
		draw_pads()
		draw_portals()
	if gift != null:
		draw_bonbon(gift.pos, (0.4 + 0.6 * minf(1.0, gift.born / 0.3)) * (1.0 + gift.wob * 0.12), gift.wob, str(gift.hp))
	if boss != null and (boss.hp > 0 or ending > 1.9):
		draw_boss()
	draw_balls()
	draw_parts()
	base_off = Vector2.ZERO
	draw_set_transform(Vector2.ZERO)
	draw_hud()
	draw_cards()
	draw_tutorial()
	if banner != null:
		draw_banner()
	if flash > 0.0:
		draw_rect(Rect2(0, 0, 720, 1280), Color(1, 1, 1, flash * 0.7))
	if state == "newcandy":
		draw_newcandy()
	elif state == "drop":
		draw_drop()
	elif state == "end":
		draw_end()
	elif state == "fail":
		draw_fail()

func draw_bg() -> void:
	if bgtex == null:
		var gr = Gradient.new()
		gr.set_color(0, C("#ffd3ea"))
		gr.set_color(1, C("#c7b6ff"))
		bgtex = GradientTexture2D.new()
		bgtex.gradient = gr
		bgtex.fill_from = Vector2(0.5, 0.0)
		bgtex.fill_to = Vector2(0.5, 1.0)
		bgtex.width = 64
		bgtex.height = 256
	draw_texture_rect(bgtex, Rect2(0, 0, 720, 1280), false)
	for c in [Vector2(90, 230), Vector2(640, 330), Vector2(120, 980), Vector2(610, 900)]:
		var cc = c + Vector2(sin(t * 0.2 + c.x) * 14.0, 0)
		for k in [Vector2(-40, 10), Vector2(0, -12), Vector2(42, 8), Vector2(10, 18)]:
			draw_circle(cc + k, 44, C("#ffffff", 1.0, 0.35))
	var r2 = RandomNumberGenerator.new()
	r2.seed = 7
	var cols = ["#ff5fa2", "#7df0c8", "#ffd36b", "#9b7bff", "#8fd8ff"]
	for i in range(70):
		var p = Vector2(r2.randf() * 720, r2.randf() * 1280)
		var an = r2.randf() * PI
		var d = Vector2(cos(an), sin(an)) * 7
		draw_line(p - d, p + d, C(cols[i % 5], 1.0, 0.45), 5.0, true)

func shifted(pts: PackedVector2Array, o: Vector2) -> PackedVector2Array:
	var out = PackedVector2Array()
	for p in pts:
		out.append(p + o)
	return out

func cap_line(pts: PackedVector2Array, col: Color, w: float) -> void:
	draw_polyline(pts, col, w, true)
	draw_circle(pts[0], w / 2.0, col)
	draw_circle(pts[pts.size() - 1], w / 2.0, col)

func draw_spout() -> void:
	var y: float = shp.top - 120.0
	var poly = PackedVector2Array([Vector2(326, y - 74), Vector2(394, y - 74), Vector2(382, y + 30), Vector2(338, y + 30)])
	var outl = PackedVector2Array([Vector2(320, y - 80), Vector2(400, y - 80), Vector2(388, y + 36), Vector2(332, y + 36)])
	draw_colored_polygon(outl, INK())
	draw_colored_polygon(poly, C("#ffb3d6"))
	for k in range(4):
		var yy = y - 60 + k * 26
		draw_line(Vector2(330 + k * 2, yy), Vector2(390 - k * 2, yy + 12), C("#ffffff", 1.0, 0.6), 7.0, true)
	draw_circle(Vector2(360, y + 34), 20, INK())
	draw_circle(Vector2(360, y + 34), 14, C("#7a3a80"))

func draw_tube() -> void:
	var pts: PackedVector2Array = shp.pts
	var base = C(shp.col)
	var dark = C(shp.col, 0.45)
	var light = C(shp.col).lightened(0.35)
	var o = Vector2(-0.16, -0.3) * TR
	cap_line(pts, INK(), (TR + 6) * 2.0)
	cap_line(pts, dark, TR * 2.0)
	cap_line(shifted(pts, o * 0.6), base, TR * 1.55)
	var nr: PackedVector2Array = shp.nrm
	var acc = 0.0
	for i in range(1, pts.size()):
		acc += pts[i].distance_to(pts[i - 1])
		if acc >= 30.0:
			acc = 0.0
			var tg = (pts[i] - pts[i - 1]).normalized()
			draw_line(pts[i] - nr[i] * TR * 0.88 - tg * 9.0, pts[i] + nr[i] * TR * 0.88 + tg * 9.0, Color(1, 1, 1, 0.42), 10.0, true)
	cap_line(shifted(pts, o * 1.5), Color(light.r, light.g, light.b, 0.5), TR * 0.6)
	cap_line(shifted(pts, o * 2.1), Color(1, 1, 1, 0.3), TR * 0.18)
	if shp.net:
		draw_net(pts[pts.size() - 1], pts[0])

func draw_net(a: Vector2, b: Vector2) -> void:
	var n = 22
	var band = PackedVector2Array()
	for i in range(n + 1):
		var u = float(i) / n
		band.append(a.lerp(b, u) + Vector2(0, sin(u * PI) * 16.0))
	draw_polyline(band, C(shp.padc, 0.8, 0.35), 36.0, true)
	for i in range(n):
		var u = (i + 0.5) / n
		for row in range(2):
			var p = a.lerp(b, u) + Vector2(0, sin(u * PI) * 16.0 + (row - 0.5) * 14.0 + (6.0 if (i % 2) == 1 else 0.0))
			var hexa = PackedVector2Array()
			for k in range(7):
				var an = k * TAU / 6.0
				hexa.append(p + Vector2(cos(an), sin(an)) * 7.0)
			draw_polyline(hexa, C(shp.padc, 1.2, 0.8), 1.6, true)
	draw_polyline(band, C(shp.padc, 1.3, 0.8), 2.0, true)

func draw_pads() -> void:
	for pd in pads:
		var line = PackedVector2Array()
		var s: float = pd.s0
		while s <= pd.s1:
			var a = at_s(s)
			line.append(a[0] + a[1] * TR * 0.62)
			s += 6.0
		if line.size() < 2:
			continue
		var f: float = pd.f
		cap_line(line, INK(), 26.0)
		cap_line(line, C(shp.padc, 1.0 + f * 1.4), 19.0)
		cap_line(shifted(line, Vector2(-1, -4)), Color(1, 1, 1, 0.45 + f * 0.5), 5.0)

# ---------------------------------------------------------------- the 10 candies
func candy_col(lv: int) -> String:
	return ["#8fd8ff", "#ff4d6d", "#ffb3d6", "#ff7ab8", "#d99a5b", "#ff8fc6", "#ffcf6b", "#9b7bff", "#7a4a2a", "#ffd36b"][clampi(lv - 1, 0, 9)]

func draw_candy(lv: int, p: Vector2, r: float, sq = 0.0, rot = 0.0, gold = false, skin = "") -> void:
	var sk = equip if skin == "" else skin
	var sd = skin_by_id(sk)
	if sd.has("base") and sd.id == sk:
		draw_candy(lv, p, r, sq, rot, gold, sd.base)
		var sc2 = C(sd.col, 1.8, 0.85)
		draw_arc(p, r + 5, t * 2.0, t * 2.0 + 4.2, 24, sc2, 3.0, true)
		for k in range(3):
			var an = t * 2.4 + k * TAU / 3.0
			draw_star(p + Vector2(cos(an), sin(an)) * (r + 8), 4.0 + 1.5 * sin(t * 6.0 + k), C("#fff6c8", 1.8))
		return
	if sk == "candy":
		draw_candy_base(lv, p, r, sq, rot, gold)
	else:
		draw_obj(sk, lv, p, r, sq, rot, gold)

func draw_candy_base(lv: int, p: Vector2, r: float, sq = 0.0, rot = 0.0, gold = false) -> void:
	draw_circle(p + Vector2(0, r * 0.25), r + 3, Color(0.2, 0.05, 0.25, 0.25))
	draw_set_transform(p + base_off, rot, Vector2(1.0 + sq * 0.16, 1.0 - sq * 0.16))
	var ink = INK()
	match lv:
		1: # dragee: glossy oval
			ell(Vector2.ZERO, r * 1.12 + 3, r * 0.82 + 3, ink)
			ell(Vector2.ZERO, r * 1.12, r * 0.82, C("#8fd8ff"))
			ell(Vector2(0, r * 0.2), r * 0.95, r * 0.5, C("#5bb8f0"))
			ell(Vector2(-r * 0.35, -r * 0.35), r * 0.38, r * 0.18, Color(1, 1, 1, 0.85))
		2: # hard candy: red with white swirl
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, C("#ff4d6d"))
			for k in range(3):
				draw_arc(Vector2.ZERO, r * (0.32 + k * 0.22), k * 1.4, k * 1.4 + 3.6, 16, Color(1, 1, 1, 0.85), 3.5, true)
			draw_circle(Vector2(-r * 0.4, -r * 0.42), r * 0.2, Color(1, 1, 1, 0.8))
		3: # marshmallow: soft pink-white puff
			rrect(Rect2(-r - 3, -r * 0.85 - 3, r * 2 + 6, r * 1.7 + 6), ink, int(r * 0.7))
			rrect(Rect2(-r, -r * 0.85, r * 2, r * 1.7), C("#fff0f6"), int(r * 0.6))
			rrect(Rect2(-r, r * 0.05, r * 2, r * 0.8), C("#ffb3d6"), int(r * 0.4), 0, Color.BLACK, true, [0, 0, 1, 1])
			ell(Vector2(-r * 0.35, -r * 0.45), r * 0.35, r * 0.15, Color(1, 1, 1, 0.9))
		4: # bubble gum: big pink bubble
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, C("#ff7ab8"))
			draw_circle(Vector2(r * 0.15, r * 0.15), r * 0.8, C("#ff9fcc"))
			draw_circle(Vector2(-r * 0.35, -r * 0.38), r * 0.3, Color(1, 1, 1, 0.9))
			draw_circle(Vector2(r * 0.35, -r * 0.5), r * 0.1, Color(1, 1, 1, 0.8))
		5: # cookie
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, C("#d99a5b"))
			draw_circle(Vector2(-r * 0.1, -r * 0.1), r * 0.85, C("#e8b273"))
			for q in [Vector2(-0.4, -0.3), Vector2(0.35, -0.4), Vector2(0.1, 0.25), Vector2(-0.35, 0.4), Vector2(0.5, 0.3)]:
				draw_circle(q * r, r * 0.14, C("#5a2d14"))
		6: # donut
			draw_arc(Vector2.ZERO, r * 0.66, 0, TAU, 40, ink, r * 0.78 + 6, true)
			draw_arc(Vector2.ZERO, r * 0.66, 0, TAU, 40, C("#e8b273"), r * 0.78, true)
			draw_arc(Vector2(0, -r * 0.06), r * 0.64, 0, TAU, 40, C("#ff8fc6"), r * 0.58, true)
			var spc = ["#ffffff", "#7df0c8", "#ffd36b", "#8fd8ff"]
			for k in range(10):
				var an = k * TAU / 10.0 + 0.3
				var q = Vector2(cos(an), sin(an)) * r * (0.6 + (k % 2) * 0.12)
				draw_line(q - Vector2(cos(an + 1.2), sin(an + 1.2)) * 3, q + Vector2(cos(an + 1.2), sin(an + 1.2)) * 3, C(spc[k % 4]), 3.0, true)
		7: # cupcake
			var cup = PackedVector2Array([Vector2(-r * 0.75, 0), Vector2(r * 0.75, 0), Vector2(r * 0.55, r * 0.95), Vector2(-r * 0.55, r * 0.95)])
			var cup_o = PackedVector2Array([Vector2(-r * 0.75 - 4, -2), Vector2(r * 0.75 + 4, -2), Vector2(r * 0.55 + 3, r * 0.95 + 3), Vector2(-r * 0.55 - 3, r * 0.95 + 3)])
			draw_colored_polygon(cup_o, ink)
			draw_colored_polygon(cup, C("#8fd8ff"))
			for k in range(4):
				var x = -r * 0.5 + k * r * 0.33
				draw_line(Vector2(x, r * 0.08), Vector2(x * 0.8, r * 0.88), C("#ffffff", 1.0, 0.6), 3.0)
			ell(Vector2(0, -r * 0.15), r * 0.95 + 3, r * 0.62 + 3, ink)
			ell(Vector2(0, -r * 0.15), r * 0.95, r * 0.62, C("#fff0f6"))
			ell(Vector2(0, -r * 0.45), r * 0.6 + 3, r * 0.42 + 3, ink)
			ell(Vector2(0, -r * 0.45), r * 0.6, r * 0.42, C("#ffc2e2"))
			draw_circle(Vector2(0, -r * 0.92), r * 0.22 + 2, ink)
			draw_circle(Vector2(0, -r * 0.92), r * 0.22, C("#ff4d6d"))
		8: # lollipop
			draw_line(Vector2(0, r * 0.7), Vector2(0, r * 1.5), ink, 8.0)
			draw_line(Vector2(0, r * 0.7), Vector2(0, r * 1.5), C("#ffffff"), 4.0)
			draw_circle(Vector2.ZERO, r + 3, ink)
			var sw = ["#9b7bff", "#ff5fa2", "#7df0c8", "#ffd36b"]
			for k in range(4):
				draw_circle(Vector2.ZERO, r * (1.0 - k * 0.22), C(sw[k]))
			for k in range(3):
				draw_arc(Vector2.ZERO, r * (0.3 + k * 0.22), k * 2.0, k * 2.0 + 4.0, 18, Color(1, 1, 1, 0.7), 3.0, true)
		9: # cake (top view): chocolate with cream and strawberry
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, C("#7a4a2a"))
			draw_circle(Vector2.ZERO, r * 0.78, C("#9a6038"))
			for k in range(8):
				var an = k * TAU / 8.0
				draw_circle(Vector2(cos(an), sin(an)) * r * 0.78, r * 0.17, C("#fff0f6"))
			draw_circle(Vector2(0, 0), r * 0.3 + 2, ink)
			draw_circle(Vector2(0, 0), r * 0.3, C("#ff4d6d"))
			draw_circle(Vector2(-r * 0.08, -r * 0.1), r * 0.07, Color(1, 1, 1, 0.8))
		_: # golden candy: a wrapped bonbon in gold foil
			var w = r * 0.78
			var h = r * 0.6
			for sg in [-1, 1]:
				var base = Vector2(sg * w * 0.85, 0)
				var fan = PackedVector2Array([base + Vector2(0, -h * 0.28), base + Vector2(sg * r * 0.55, -h * 0.95), base + Vector2(sg * r * 0.42, -h * 0.3), base + Vector2(sg * r * 0.62, 0), base + Vector2(sg * r * 0.42, h * 0.3), base + Vector2(sg * r * 0.55, h * 0.95), base + Vector2(0, h * 0.28)])
				var fano = PackedVector2Array()
				for q in fan:
					fano.append(q + (q - base).normalized() * 3.0)
				draw_colored_polygon(fano, ink)
				draw_colored_polygon(fan, C("#ffcf4a", 1.25))
				draw_line(base + Vector2(sg * r * 0.08, -h * 0.15), base + Vector2(sg * r * 0.45, -h * 0.7), C("#fff6c8", 1.4, 0.8), 2.0, true)
				draw_circle(base, h * 0.32 + 2, ink)
				draw_circle(base, h * 0.32, C("#e0a020", 1.2))
			ell(Vector2.ZERO, w + 3, h + 3, ink)
			ell(Vector2.ZERO, w, h, C("#ffd36b", 1.35))
			ell(Vector2(0, h * 0.25), w * 0.9, h * 0.55, C("#f2b230", 1.25))
			for k in range(-1, 2):
				draw_line(Vector2(k * w * 0.45 - w * 0.12, -h * 0.85), Vector2(k * w * 0.45 + w * 0.12, h * 0.85), C("#fff6c8", 1.4, 0.55), 3.0, true)
			ell(Vector2(-w * 0.35, -h * 0.4), w * 0.28, h * 0.16, Color(1.7, 1.7, 1.7, 0.9))
	if gold:
		draw_arc(Vector2.ZERO, r + 6, 0, TAU, 32, C("#ffd36b", 2.2, 0.9), 4.0, true)
	draw_set_transform(base_off)

func ell(c: Vector2, rx: float, ry: float, col: Color) -> void:
	var pts = PackedVector2Array()
	for k in range(28):
		var an = k * TAU / 28.0
		pts.append(c + Vector2(cos(an) * rx, sin(an) * ry))
	draw_colored_polygon(pts, col)

func hidden_ball(b: Dictionary) -> bool:
	return (b.get("q", false) and b.mg == null) or b.get("lift", -1.0) >= 0.0

func draw_balls() -> void:
	for b in balls:
		if hidden_ball(b):
			continue
		var tr: Array = b.tr
		for i in range(1, tr.size()):
			var a = float(i) / tr.size()
			if trail_style != "" and not b.gold:
				trail_dot(tr[i], a, b.r * 1.1, i + int(t * 20.0), trail_style)
			else:
				draw_line(tr[i - 1], tr[i], C("#ffd36b" if b.gold else "#ffffff", 1.0, a * 0.5), maxf(1.5, b.r * 0.35 * a), true)
	for b in balls:
		if hidden_ball(b):
			continue
		draw_candy(b.lv, b.p, b.r, b.sq, b.rot, b.gold)

func draw_bonbon(c: Vector2, s: float, wob: float, label: String) -> void:
	var sway = sin(t * 2.2) * 0.12 + wob * 0.25 * sin(t * 40.0)
	for i in range(7):
		draw_circle(c, (46 + i * 9) * s, C("#ffffff", 1.3, 0.06))
	draw_set_transform(c + base_off, sway, Vector2(s, s))
	var w = 46.0
	var h = 34.0
	for sg in [-1, 1]:
		var tip = Vector2(sg * (w + 34), 0)
		var wing = PackedVector2Array([Vector2(sg * (w - 8), -10), tip + Vector2(0, -26), tip + Vector2(sg * -8, 0), tip + Vector2(0, 26), Vector2(sg * (w - 8), 10)])
		var wing_o = PackedVector2Array()
		for q in wing:
			wing_o.append(q + (q - Vector2(sg * (w - 8), 0)).normalized() * 4.0)
		draw_colored_polygon(wing_o, INK())
		draw_colored_polygon(wing, C("#ffd36b"))
		draw_line(Vector2(sg * (w + 6), -6), tip + Vector2(sg * -6, -16), C("#ffffff", 1.0, 0.55), 3.0, true)
		draw_line(Vector2(sg * (w + 6), 6), tip + Vector2(sg * -6, 16), C("#e0a23a"), 3.0, true)
		draw_circle(Vector2(sg * (w - 4), 0), 11, INK())
		draw_circle(Vector2(sg * (w - 4), 0), 8, C("#f2b230"))
	ell(Vector2.ZERO, w + 5, h + 5, INK())
	ell(Vector2.ZERO, w, h, C("#ff5fa2"))
	for k in range(-2, 3):
		var x0 = k * 18.0
		var yl = h * sqrt(maxf(0.0, 1.0 - pow(x0 / w, 2))) * 0.9
		draw_line(Vector2(x0 - 9, -yl), Vector2(x0 + 9, yl), C("#ffffff", 1.0, 0.55), 7.0, true)
	draw_circle(Vector2(-w * 0.45, -h * 0.4), 9, Color(1, 1, 1, 0.75))
	draw_set_transform(base_off)
	text_c(c + Vector2(0, 3), label, int(32 * s), Color(1, 1, 1), 8)

func draw_boss() -> void:
	var b: Dictionary = boss
	var tgt = Vector2(360, 900)
	var best = 1e9
	for q in balls:
		if hidden_ball(q):
			continue
		var d: float = q.p.distance_to(b.pos)
		if d < best:
			best = d; tgt = q.p
	var s2 = 1.0 + b.wob * 0.08
	draw_boss_body(b.kind, b.pos, s2, float(b.hp) / b.max, b.shield, b.rot, tgt, false, b.wob)
	# hp bar + name
	var top = b.pos.y - b.h / 2.0 - (40.0 if b.kind == "cupcake" else 20.0)
	var hb = Rect2(b.pos.x - 90, top - 34, 180, 26)
	rrect(hb.grow(4), INK(), 16)
	rrect(hb, C("#ffffff", 1.0, 0.6), 13)
	var k2 = float(b.hp) / b.max
	if k2 > 0.0:
		rrect(Rect2(hb.position, Vector2(hb.size.x * k2, hb.size.y)), C("#ff4d6d"), 13)
	text_c(hb.get_center() + Vector2(0, 1), str(b.hp), 22, Color(1, 1, 1), 6)

func boss_ai(dt: float) -> void:
	var b = boss
	var bx = 398.0 if is_plinko() else 360.0
	var by = 610.0 if is_plinko() else (520.0 if is_flipper() else (500.0 if is_space() else 600.0))
	var amp = 0.75 if is_plinko() else 1.0
	match b.kind:
		"gummy": # fast and bouncy
			b.pos.x = bx + sin(b.t * 0.9) * 120.0 * amp
			b.pos.y = by + absf(sin(b.t * 2.2)) * -40.0 + 20.0
		"cupcake": # slow, raises a whipped-cream shield 1.8 s out of every 6 s
			b.pos.x = bx + sin(b.t * 0.5) * 110.0 * amp
			b.pos.y = by
			var ph = fmod(b.t, 6.0)
			var was = b.shield
			b.shield = ph > 4.2
			if b.shield and not was:
				play("pad", 0.7, -8.0)
				if not sim:
					floats.append({"p": b.pos + Vector2(0, -110), "txt": "SHIELD!", "col": "#8fd8ff", "t": 0.0, "big": true})
		"choco": # heavy: barely moves
			b.pos.x = bx + sin(b.t * 0.3) * 60.0
			b.pos.y = by
		"donut": # rolls left and right, spinning
			b.pos.x = bx + sin(b.t * 0.8) * 140.0
			b.pos.y = by
			b.rot = (b.pos.x - bx) / 64.0
		"ginger": # stomps slowly, jumps every 4 s
			b.pos.x = bx + sin(b.t * 0.4) * 100.0
			var ph2 = fmod(b.t, 4.0)
			b.pos.y = by - (sin(ph2 / 0.6 * PI) * 70.0 if ph2 < 0.6 else 0.0)
		"mallow": # orbits the planet slowly
			b.pos = Vector2(360, 640) + Vector2(cos(b.t * 0.5), sin(b.t * 0.5) * 0.6 - 0.5) * 150.0
		"cloud": # drifts, puffs a shield of fluff 2 s every 7 s
			b.pos.x = bx + sin(b.t * 0.5) * 110.0
			b.pos.y = by + sin(b.t * 0.9) * 20.0
			var was2 = b.shield
			b.shield = fmod(b.t, 7.0) > 5.0
			if b.shield and not was2:
				play("pad", 0.6, -8.0)
		"gumball": # spits a gumball shower every 6 s (pure show) and wobbles
			b.pos.x = bx + sin(b.t * 0.6) * 100.0
			b.pos.y = by
			if fmod(b.t, 6.0) < dt * 1.5 and not sim:
				for k in range(12):
					burst(b.pos + Vector2(0, -40), C(["#ff4d6d", "#4fa3ff", "#ffd36b", "#3fcf5f"][k % 4], 1.6), 1, 380.0, 9.0, 0.8)
		"overlord": # final boss: moves, shields, then teleports when below half hp
			b.rot += dt * 2.0
			var slot2 = int(b.t / 6.0) % 3
			if float(b.hp) / b.max < 0.5 and slot2 != b.tp:
				b.tp = slot2
				burst(b.pos, C("#ffd36b", 1.6), 30, 320.0, 5.0, 0.5)
				b.pos = Vector2(360 + [0.0, -120.0, 120.0][slot2], 500 + [0.0, 60.0, 60.0][slot2])
				play("swipe", 1.5, -8.0)
			elif float(b.hp) / b.max >= 0.5:
				b.pos.x = bx + sin(b.t * 0.5) * 110.0
				b.pos.y = by
			var was3 = b.shield
			b.shield = fmod(b.t, 8.0) > 6.3
			if b.shield and not was3 and not sim:
				floats.append({"p": b.pos + Vector2(0, -120), "txt": "SHIELD!", "col": "#ffd36b", "t": 0.0, "big": true})
		"jelly": # three beans bobbing in a row
			b.pos.x = bx + sin(b.t * 0.7) * 90.0
			b.pos.y = by + sin(b.t * 2.0) * 15.0
			b.rot += dt
		"sundae": # floats; a scoop shield orbits around it
			b.pos.x = bx + sin(b.t * 0.45) * 90.0
			b.pos.y = by + sin(b.t * 1.1) * 25.0
			b.rot += dt * 1.6
		"lolli": # spins, teleports every 7 s
			b.rot += dt * 2.4
			var slot = int(b.t / 7.0) % 3
			if slot != b.tp:
				b.tp = slot
				burst(b.pos, C("#ffffff", 1.6), 26, 300.0, 5.0, 0.5)
				play("swipe", 1.5, -8.0)
				b.pos = Vector2(bx + [0.0, -110.0, 110.0][slot] * amp, by + [0.0, -40.0, 30.0][slot])
				burst(b.pos, C("#9b7bff", 1.6), 26, 300.0, 5.0, 0.5)

func boss_eyes(c: Vector2, sp: float, s: float, tgt: Vector2, locked: bool) -> void:
	for sg in [-1, 1]:
		var e = c + Vector2(sg * sp, 0) * s
		draw_circle(e, 20 * s, INK())
		draw_circle(e, 17 * s, Color(1, 1, 1))
		var dir: Vector2 = (tgt - e).normalized()
		draw_circle(e + dir * 6.0 * s, 8 * s, INK())
		draw_line(e + Vector2(-19, -26 + (7 if sg < 0 else -7)) * s, e + Vector2(19, -26 + (-7 if sg < 0 else 7)) * s, INK(), 6.0 * s, true)

func bcol(h: String, locked: bool) -> Color:
	return gray(C(h)) if locked else C(h)

func draw_boss_body(kind: String, c: Vector2, s: float, ratio: float, shield: bool, rot: float, tgt: Vector2, locked: bool, wob: float) -> void:
	var ink = INK()
	match kind:
		"cupcake":
			# wrapper
			var top_y = c.y + 6 * s
			var cup = PackedVector2Array([Vector2(c.x - 62 * s, top_y), Vector2(c.x + 62 * s, top_y), Vector2(c.x + 46 * s, top_y + 64 * s), Vector2(c.x - 46 * s, top_y + 64 * s)])
			var cupo = PackedVector2Array([Vector2(c.x - 68 * s, top_y - 4 * s), Vector2(c.x + 68 * s, top_y - 4 * s), Vector2(c.x + 50 * s, top_y + 69 * s), Vector2(c.x - 50 * s, top_y + 69 * s)])
			draw_colored_polygon(cupo, ink)
			draw_colored_polygon(cup, bcol("#3fbfd9", locked))
			for k in range(6):
				var x = c.x - 50 * s + k * 20 * s
				draw_line(Vector2(x, top_y + 4 * s), Vector2(c.x + (x - c.x) * 0.75, top_y + 60 * s), Color(1, 1, 1, 0.45), 4.0 * s)
			# frosting tiers
			for tier in [[0.0, 74.0, 34.0], [-30.0, 56.0, 28.0], [-56.0, 36.0, 22.0]]:
				ell(c + Vector2(0, tier[0] - 6) * s, (tier[1] + 5) * s, (tier[2] + 5) * s, ink)
				ell(c + Vector2(0, tier[0] - 6) * s, tier[1] * s, tier[2] * s, bcol("#ff9fd0", locked))
				ell(c + Vector2(-tier[1] * 0.35, tier[0] - 14) * s, tier[1] * 0.3 * s, tier[2] * 0.25 * s, Color(1, 1, 1, 0.6))
			# cherry + crown
			draw_circle(c + Vector2(0, -84) * s, 13 * s, ink)
			draw_circle(c + Vector2(0, -84) * s, 10 * s, bcol("#ff4d6d", locked))
			boss_crown(c + Vector2(0, -104) * s, s * 0.8, locked)
			boss_eyes(c + Vector2(0, -6) * s, 30.0, s * 0.85, tgt, locked)
			draw_arc(c + Vector2(0, 42) * s, 14 * s, PI * 1.15, PI * 1.85, 10, ink, 5.0 * s, true)
			if shield:
				draw_circle(c, 112 * s, C("#8fd8ff", 1.3, 0.25))
				draw_arc(c, 112 * s, 0, TAU, 48, C("#ffffff", 1.6, 0.8), 5.0, true)
				draw_arc(c, 98 * s, -2.2, -1.4, 12, C("#ffffff", 1.6, 0.8), 6.0, true)
		"choco":
			var w = 180.0 * s
			var h = 112.0 * s
			var r = Rect2(c - Vector2(w, h) / 2.0, Vector2(w, h))
			rrect(Rect2(r.position + Vector2(0, 10), r.size), C(INKH, 1.0, 0.3), int(20 * s))
			rrect(r.grow(6 * s), ink, int(22 * s))
			rrect(r, bcol("#6b3a1e", locked), int(18 * s))
			for gx in range(3):
				for gy in range(2):
					var cell = Rect2(r.position + Vector2(10 + gx * 56, 10 + gy * 48) * s, Vector2(48, 40) * s)
					rrect(cell, bcol("#8a4f2a", locked), int(8 * s))
					rrect(Rect2(cell.position + Vector2(4, 3) * s, Vector2(40, 8) * s), bcol("#a8693e", locked), int(4 * s))
			# silver foil on the bottom
			rrect(Rect2(r.position + Vector2(-4, h * 0.72), Vector2(w + 8, h * 0.32)), bcol("#d9dbe6", locked), int(10 * s))
			for k in range(6):
				draw_line(r.position + Vector2(10 + k * 30, h * 0.75) * Vector2(s / s, 1) + Vector2(0, 0), r.position + Vector2(20 + k * 30, h) , Color(1, 1, 1, 0.6), 3.0)
			# cracks as hp drops
			if ratio < 0.67:
				draw_polyline(PackedVector2Array([c + Vector2(-60, -50) * s, c + Vector2(-40, -20) * s, c + Vector2(-55, 5) * s, c + Vector2(-30, 25) * s]), ink, 4.0 * s, true)
			if ratio < 0.34:
				draw_polyline(PackedVector2Array([c + Vector2(70, -48) * s, c + Vector2(45, -18) * s, c + Vector2(62, 8) * s, c + Vector2(38, 30) * s]), ink, 4.0 * s, true)
				draw_polyline(PackedVector2Array([c + Vector2(0, -56) * s, c + Vector2(8, -30) * s, c + Vector2(-6, -12) * s]), ink, 4.0 * s, true)
			boss_eyes(c + Vector2(0, -6) * s, 36.0, s, tgt, locked)
			draw_line(c + Vector2(-16, 26) * s, c + Vector2(16, 26) * s, ink, 6.0 * s, true)
		"mallow":
			draw_circle(c, 66 * s + 4, ink)
			draw_circle(c, 66 * s, bcol("#fff0f6", locked))
			draw_circle(c + Vector2(8, 8) * s, 56 * s, bcol("#ffd3ea", locked))
			for q in [Vector2(-30, -30), Vector2(25, 30), Vector2(30, -25)]:
				draw_circle(c + q * s, 9 * s, bcol("#f0c8dc", locked))
			draw_arc(c, 92 * s, -0.3, PI + 0.3, 24, ink, 12 * s, true)
			draw_arc(c, 92 * s, -0.3, PI + 0.3, 24, bcol("#7df0c8", locked), 7 * s, true)
			boss_eyes(c + Vector2(0, -6) * s, 24.0, s * 0.8, tgt, locked)
			draw_arc(c + Vector2(0, 34) * s, 12 * s, PI * 1.15, PI * 1.85, 10, ink, 5.0 * s, true)
		"cloud":
			for q in [Vector2(-60, 10, ), Vector2(-25, -22), Vector2(20, -28), Vector2(60, 5), Vector2(0, 18)]:
				draw_circle(c + q * s, 46 * s + 4, ink)
			for q in [Vector2(-60, 10), Vector2(-25, -22), Vector2(20, -28), Vector2(60, 5), Vector2(0, 18)]:
				draw_circle(c + q * s, 46 * s, bcol("#ffb3d6", locked))
			for q in [Vector2(-40, -10), Vector2(30, -20)]:
				draw_circle(c + q * s, 22 * s, bcol("#ffe3f0", locked))
			boss_eyes(c + Vector2(0, 0) * s, 26.0, s * 0.8, tgt, locked)
			draw_arc(c + Vector2(0, 36) * s, 12 * s, PI * 1.15, PI * 1.85, 10, ink, 5.0 * s, true)
			if shield:
				draw_circle(c, 120 * s, C("#ffffff", 1.2, 0.3))
				draw_arc(c, 120 * s, 0, TAU, 48, C("#ffffff", 1.6, 0.8), 5.0, true)
		"gumball":
			var base = PackedVector2Array([c + Vector2(-50, 40) * s, c + Vector2(50, 40) * s, c + Vector2(60, 90) * s, c + Vector2(-60, 90) * s])
			draw_colored_polygon(PackedVector2Array([base[0] + Vector2(-4, -4), base[1] + Vector2(4, -4), base[2] + Vector2(4, 4), base[3] + Vector2(-4, 4)]), ink)
			draw_colored_polygon(base, bcol("#ff4d6d", locked))
			rrect(Rect2(c + Vector2(-10, 55) * s, Vector2(20, 20) * s), bcol("#ffd36b", locked), int(4 * s))
			draw_circle(c + Vector2(0, -20) * s, 64 * s + 4, ink)
			draw_circle(c + Vector2(0, -20) * s, 64 * s, C("#d9f2ff", 1.0, 0.85) if not locked else C("#e6e6ee"))
			var gcols = ["#ff4d6d", "#4fa3ff", "#ffd36b", "#3fcf5f", "#9b7bff", "#ff9a2e"]
			for k in range(14):
				var gq = c + Vector2(cos(k * 2.4) * (12 + (k % 4) * 11), -20 + sin(k * 2.4) * (12 + (k % 4) * 11)) * s
				draw_circle(gq, 9 * s, bcol(gcols[k % 6], locked))
			draw_circle(c + Vector2(0, -90) * s, 12 * s, ink)
			draw_circle(c + Vector2(0, -90) * s, 9 * s, bcol("#ff4d6d", locked))
			boss_eyes(c + Vector2(0, -20) * s, 26.0, s * 0.75, tgt, locked)
		"overlord":
			# cape
			draw_colored_polygon(PackedVector2Array([c + Vector2(-70, -20) * s, c + Vector2(70, -20) * s, c + Vector2(95, 90) * s, c + Vector2(-95, 90) * s]), ink)
			draw_colored_polygon(PackedVector2Array([c + Vector2(-64, -16) * s, c + Vector2(64, -16) * s, c + Vector2(88, 84) * s, c + Vector2(-88, 84) * s]), bcol("#9b2a5a", locked))
			# body = big wrapped candy king
			ell(c, 70 * s + 4, 62 * s + 4, ink)
			ell(c, 70 * s, 62 * s, bcol("#ff5fa2", locked))
			for k in range(-2, 3):
				draw_line(c + Vector2(k * 24 - 10, -54) * s, c + Vector2(k * 24 + 10, 54) * s, Color(1, 1, 1, 0.45), 9 * s, true)
			for sg in [-1, 1]:
				draw_colored_polygon(PackedVector2Array([c + Vector2(sg * 64, -14) * s, c + Vector2(sg * 110, -44) * s, c + Vector2(sg * 110, 44) * s, c + Vector2(sg * 64, 14) * s]), bcol("#ffd36b", locked))
			boss_eyes(c + Vector2(0, -8) * s, 26.0, s * 0.85, tgt, locked)
			var mouth2 = PackedVector2Array([c + Vector2(-22, 26) * s, c + Vector2(22, 26) * s, c + Vector2(14, 38) * s, c + Vector2(-14, 38) * s])
			draw_colored_polygon(mouth2, ink)
			boss_crown(c + Vector2(0, -86) * s, s * 1.2, locked)
			if shield:
				draw_circle(c, 130 * s, C("#ffd36b", 1.2, 0.22))
				draw_arc(c, 130 * s, 0, TAU, 48, C("#ffd36b", 1.8, 0.9), 6.0, true)
		"ginger":
			var bodyc = bcol("#c97a3a", locked)
			var icing = bcol("#ffffff", locked)
			# legs, arms, body, head
			for sg in [-1, 1]:
				draw_line(c + Vector2(sg * 22, 40) * s, c + Vector2(sg * 34, 82) * s, ink, 40 * s)
				draw_line(c + Vector2(sg * 22, 40) * s, c + Vector2(sg * 34, 82) * s, bodyc, 32 * s)
				draw_line(c + Vector2(sg * 30, 0) * s, c + Vector2(sg * 70, -20) * s, ink, 36 * s)
				draw_line(c + Vector2(sg * 30, 0) * s, c + Vector2(sg * 70, -20) * s, bodyc, 28 * s)
				draw_arc(c + Vector2(sg * 64, -18) * s, 8 * s, 0, PI, 8, icing, 3 * s)
			ell(c + Vector2(0, 14) * s, 46 * s + 4, 52 * s + 4, ink)
			ell(c + Vector2(0, 14) * s, 46 * s, 52 * s, bodyc)
			draw_circle(c + Vector2(0, -50) * s, 42 * s + 4, ink)
			draw_circle(c + Vector2(0, -50) * s, 42 * s, bodyc)
			for k in range(3):
				draw_circle(c + Vector2(0, 0 + k * 22) * s, 7 * s, bcol(["#ff5fa2", "#7df0c8", "#ffd36b"][k], locked))
			draw_arc(c + Vector2(0, -30) * s, 14 * s, PI * 1.15, PI * 1.85, 10, icing, 4 * s, true)
			boss_eyes(c + Vector2(0, -56) * s, 16.0, s * 0.6, tgt, locked)
		"jelly":
			var cols3 = ["#ff4d6d", "#7df0c8", "#ffd36b"]
			for k in range(3):
				var q = c + Vector2((k - 1) * 66, sin(rot * 2.0 + k * 2.0) * 10) * s
				ell(q, 34 * s + 4, 46 * s + 4, ink)
				ell(q, 34 * s, 46 * s, bcol(cols3[k], locked))
				ell(q + Vector2(-10, -18) * s, 9 * s, 14 * s, Color(1, 1, 1, 0.55))
				boss_eyes(q + Vector2(0, -2) * s, 12.0, s * 0.5, tgt, locked)
			boss_crown(c + Vector2(0, -62) * s, s * 0.6, locked)
		"donut":
			draw_set_transform(c + base_off, rot)
			draw_arc(Vector2.ZERO, 44 * s, 0, TAU, 48, ink, 52 * s + 8, true)
			draw_arc(Vector2.ZERO, 44 * s, 0, TAU, 48, bcol("#e8b273", locked), 52 * s, true)
			draw_arc(Vector2(0, -4 * s), 44 * s, 0, TAU, 48, bcol("#ff8fc6", locked), 40 * s, true)
			var spc = ["#ffffff", "#7df0c8", "#ffd36b", "#8fd8ff", "#9b7bff"]
			for k in range(16):
				var an = k * TAU / 16.0 + 0.2
				var q = Vector2(cos(an), sin(an)) * (40.0 + (k % 3) * 6.0) * s
				draw_line(q - Vector2(cos(an + 1.2), sin(an + 1.2)) * 5 * s, q + Vector2(cos(an + 1.2), sin(an + 1.2)) * 5 * s, bcol(spc[k % 5], locked), 4.0 * s, true)
			draw_set_transform(base_off)
			boss_eyes(c + Vector2(0, -44) * s, 22.0, s * 0.7, tgt, locked)
			boss_crown(c + Vector2(0, -96) * s, s * 0.75, locked)
			draw_arc(c + Vector2(0, 50) * s, 12 * s, PI * 1.15, PI * 1.85, 10, ink, 5.0 * s, true)
		"sundae":
			# glass cup + 3 scoops + whipped cream + cherry, scoop shield orbiting
			var cup = PackedVector2Array([c + Vector2(-58, 10) * s, c + Vector2(58, 10) * s, c + Vector2(30, 60) * s, c + Vector2(12, 62) * s, c + Vector2(12, 80) * s, c + Vector2(34, 88) * s, c + Vector2(-34, 88) * s, c + Vector2(-12, 80) * s, c + Vector2(-12, 62) * s, c + Vector2(-30, 60) * s])
			var cupo = PackedVector2Array()
			for q in cup:
				cupo.append(c + (q - c) * 1.06)
			draw_colored_polygon(cupo, ink)
			draw_colored_polygon(cup, bcol("#d9f2ff", locked))
			for sc2 in [[-34.0, -8.0, "#ff9fd0"], [34.0, -8.0, "#7df0c8"], [0.0, -38.0, "#fff1d6"]]:
				draw_circle(c + Vector2(sc2[0], sc2[1]) * s, 40 * s, ink)
				draw_circle(c + Vector2(sc2[0], sc2[1]) * s, 36 * s, bcol(sc2[2], locked))
				draw_circle(c + Vector2(sc2[0] - 12, sc2[1] - 14) * s, 9 * s, Color(1, 1, 1, 0.6))
			draw_circle(c + Vector2(0, -82) * s, 13 * s, ink)
			draw_circle(c + Vector2(0, -82) * s, 10 * s, bcol("#ff4d6d", locked))
			boss_eyes(c + Vector2(0, -36) * s, 18.0, s * 0.62, tgt, locked)
			# wizard hat
			var hat = PackedVector2Array([c + Vector2(-30, -92) * s, c + Vector2(30, -92) * s, c + Vector2(6, -150) * s])
			draw_colored_polygon(PackedVector2Array([hat[0] + Vector2(-4, 3), hat[1] + Vector2(4, 3), hat[2] + Vector2(0, -5)]), ink)
			draw_colored_polygon(hat, bcol("#9b7bff", locked))
			draw_circle(c + Vector2(-2, -118) * s, 5 * s, bcol("#ffd36b", locked))
			if not locked:
				for k in range(3):
					var an = rot + k * TAU / 3.0
					var q = c + Vector2(cos(an), sin(an)) * 95.0 * s
					draw_circle(q, 18 * s, ink)
					draw_circle(q, 15 * s, C(["#ff9fd0", "#7df0c8", "#ffd36b"][k]))
		"lolli":
			draw_line(c + Vector2(0, 40) * s, c + Vector2(0, 120) * s, ink, 16 * s)
			draw_line(c + Vector2(0, 40) * s, c + Vector2(0, 120) * s, bcol("#fff1d6", locked), 9 * s)
			draw_circle(c, 76 * s, ink)
			var sw = ["#9b7bff", "#ff5fa2", "#7df0c8", "#ffd36b", "#8fd8ff"]
			draw_circle(c, 70 * s, bcol("#ffffff", locked))
			for k in range(5):
				var a0 = rot + k * TAU / 5.0
				var pts = PackedVector2Array([c])
				for j in range(13):
					var aa = a0 + j * (TAU / 5.0) / 12.0
					var rr2 = 70.0 * s
					pts.append(c + Vector2(cos(aa + (1.0 - rr2 / (70.0 * s)) * 2.0), sin(aa)) * rr2)
				draw_colored_polygon(pts, bcol(sw[k], locked))
			for k in range(3):
				draw_arc(c, (18 + k * 17) * s, rot * 1.5 + k, rot * 1.5 + k + 3.5, 16, Color(1, 1, 1, 0.55), 5.0 * s, true)
			draw_circle(c, 40 * s, ink)
			draw_circle(c, 36 * s, bcol("#fff0f6", locked))
			boss_eyes(c + Vector2(0, -2) * s, 15.0, s * 0.62, tgt, locked)
			boss_crown(c + Vector2(0, -84) * s, s * 0.7, locked)
		_:
			# Grumpy Gummy: red jelly block
			var w = 156.0 * s
			var h = 108.0 * s
			var r = Rect2(c - Vector2(w, h) / 2.0, Vector2(w, h))
			rrect(Rect2(r.position + Vector2(0, 10), r.size), C(INKH, 1.0, 0.3), int(30 * s))
			rrect(r.grow(6 * s), ink, int(32 * s))
			rrect(r, bcol("#ff4d6d", locked), int(28 * s))
			rrect(Rect2(r.position + Vector2(10, 8) * s, Vector2(w - 20 * s, h * 0.34)), C("#ff9aae", 1.0, 0.7) if not locked else Color(1, 1, 1, 0.3), int(18 * s))
			for k in range(5):
				draw_circle(Vector2(r.position.x + 22 * s + k * (w - 44 * s) / 4.0, r.end.y - 10 * s), 7 * s, bcol("#ffd36b", locked))
			boss_eyes(c + Vector2(0, -8) * s, 34.0, s, tgt, locked)
			var mouth = PackedVector2Array([c + Vector2(-20, 24) * s, c + Vector2(20, 24) * s, c + Vector2(13, 36) * s, c + Vector2(-13, 36) * s])
			draw_colored_polygon(mouth, ink)
			for k in range(3):
				draw_colored_polygon(PackedVector2Array([c + Vector2(-13 + k * 10, 24) * s, c + Vector2(-6 + k * 10, 24) * s, c + Vector2(-9.5 + k * 10, 31) * s]), Color(1, 1, 1))
	if wob > 0.0 and kind != "lolli":
		draw_circle(c, 70 * s, Color(1, 1, 1, wob * 0.25))

func boss_crown(p: Vector2, s: float, locked: bool) -> void:
	var cr = PackedVector2Array([Vector2(-30, 22), Vector2(-30, -2), Vector2(-15, 12), Vector2(0, -8), Vector2(15, 12), Vector2(30, -2), Vector2(30, 22)])
	var o = PackedVector2Array()
	var pts = PackedVector2Array()
	for q in cr:
		pts.append(p + q * s)
		o.append(p + q * s + (q - Vector2(0, 10)).normalized() * 4.0)
	draw_colored_polygon(o, INK())
	draw_colored_polygon(pts, bcol("#ffd36b", locked))
	for q in [Vector2(-30, -2), Vector2(0, -8), Vector2(30, -2)]:
		draw_circle(p + q * s, 5 * s, bcol("#ff5fa2", locked))

func draw_parts() -> void:
	for p in parts:
		var a: float = clampf(p.life / p.max, 0.0, 1.0)
		var col: Color = p.col
		if p.ring:
			var rr: float = 8.0 + (p.r - 8.0) * (1.0 - a * a)
			draw_arc(p.p, rr, 0, TAU, 48, Color(col.r, col.g, col.b, a), 6.0 * a + 1.0, true)
		elif p.has("conf"):
			draw_set_transform(p.p + base_off, p.rot)
			draw_rect(Rect2(-6, -3, 12, 6), Color(col.r, col.g, col.b, minf(1.0, a * 2.0)))
			draw_set_transform(base_off)
		else:
			draw_circle(p.p, p.size * (0.4 + 0.6 * a), Color(col.r, col.g, col.b, a))
	for f in floats:
		var dur = 1.0 if f.big else 0.75
		var k: float = f.t / dur
		var y: float = f.p.y - f.t * (60.0 if f.big else 52.0)
		var sz = 38 if f.big else 26
		if f.big and f.t < 0.15:
			sz = int(sz * (0.6 + f.t / 0.15 * 0.5))
		text_c(Vector2(f.p.x, y), f.txt, sz, C(f.col, 1.0, 1.0 - k * k), 7, C(INKH, 1.0, 1.0 - k * k))

func draw_hud() -> void:
	text_l(Vector2(40, 54), lvl_label(), 30, Color(1, 1, 1), 8)
	var pill = Rect2(36, 82, 270, 48)
	rrect(pill, C("#ffffff", 1.0, 0.45), 24)
	var prog: float
	var label: String
	if boss != null:
		prog = 1.0 - float(boss.hp) / boss.max
		label = "BOSS"
	else:
		prog = clampf(earned / maxf(1.0, target()), 0.0, 1.0)
		label = "%s / %s" % [fmt(earned), fmt(target())]
	if prog > 0.02:
		rrect(Rect2(pill.position + Vector2(4, 4), Vector2((pill.size.x - 8) * prog, pill.size.y - 8)), C("#ff4d6d" if boss != null else "#3fcf9f"), 20)
	rrect(pill, Color(0, 0, 0, 0), 24, 4, INK(), false)
	text_c(pill.get_center() + Vector2(0, 1), label, 24, Color(1, 1, 1), 6)
	# timer + stars
	var tl = L.get("limit", 0.0) if not overtime else 0.0
	var tstr = ftime(tl - lt) if tl > 0.0 else ftime(lt)
	var tcol = C("#ff4d6d") if (tl > 0.0 and tl - lt < 15.0) else Color(1, 1, 1)
	text_l(Vector2(328, 106), tstr, 28 if tl == 0.0 else int(30 + (6 if tl - lt < 15.0 and fmod(t, 0.5) < 0.25 else 0)), tcol, 7)
	for k in range(3):
		var on = true
		if k == 2:
			on = lt <= L.stars[0]
		elif k == 1:
			on = lt <= L.stars[1]
		draw_star(Vector2(130 + k * 34, 158), 13.0, C("#ffd36b") if on else C("#d6c8f0"))
	# map + skins buttons (Cozy UI round button)
	img("round", MAPBTN.grow(6))
	img("round", SKINBTN.grow(6))
	img("round", SETBTN.grow(6))
	draw_gear(SETBTN.get_center() + Vector2(0, -4), 22.0)
	draw_candy(lv_icon(), SKINBTN.get_center() + Vector2(0, -4), 20.0)
	var mc = MAPBTN.get_center() + Vector2(0, -4)
	var path = PackedVector2Array([mc + Vector2(-22, 18), mc + Vector2(-8, 4), mc + Vector2(6, 12), mc + Vector2(20, -16)])
	draw_polyline(path, C("#ff5fa2"), 6.0, true)
	for q in [mc + Vector2(-22, 18), mc + Vector2(6, 12), mc + Vector2(20, -16)]:
		draw_circle(q, 7, INK())
		draw_circle(q, 5, C("#ffd36b"))
	# money pill
	var mp = Rect2(430, 40, 256, 58)
	rrect(mp, C(INKH, 1.0, 0.75), 29)
	draw_set_transform(Vector2(451, 69) + base_off, -0.35)
	rrect(Rect2(-31, -19, 62, 38), INK(), 8)
	rrect(Rect2(-28, -16, 56, 32), C("#3fd94a"), 6)
	draw_circle(Vector2.ZERO, 9, C("#1f8a2a"))
	text_c(Vector2(0, 1), "$", 16, C("#d9ffd9"), 0)
	draw_set_transform(base_off)
	text_l(Vector2(676, 69), fmt(money), 34, Color(1, 1, 1), 7, true)
	text_l(Vector2(684, 120), "$%s / sec" % fmt(rate()), 20, Color(1, 1, 1), 5, true)
	# coins
	draw_coin(Vector2(560, 160), 15.0)
	text_l(Vector2(584, 160), str(coins), 24, Color(1, 1, 1), 6)

func draw_cards() -> void:
	var nopair = merge_pair().size() < 2
	var info = [
		["BOOST" if is_plinko() else ("BUMPER" if is_flipper() else ("ADD MOON" if is_space() else "ADD PAD")), "#b8f5e1", "#5fd6b0", cost_boost() if is_plinko() else cost_pad(), can_pad(), (boosts >= 8) if is_plinko() else ((fbumps.size() >= FB_SLOTS.size()) if is_flipper() else ((moons.size() >= 6) if is_space() else free_slots().size() == 0))],
		["ADD BALL", "#ffd08a", "#ff9a5a", cost_ball(), can_ball(), balls.size() >= MAXBALLS],
		["MERGE", "#d9b8ff", "#9b7bff", cost_merge(), can_merge(), nopair],
	]
	for i in range(3):
		var r: Rect2 = CARDS[i]
		r = r.grow(-card_press[i] * 7.0)
		var on: bool = info[i][4]
		var top = C(info[i][1])
		var bot = C(info[i][2])
		if i == 2 and nopair:
			top = gray(top); bot = gray(bot)
		rrect(Rect2(r.position + Vector2(0, 9), r.size), C(INKH, 1.0, 0.35), 18)
		rrect(r, INK(), 18)
		var inner = r.grow(-6)
		rrect(inner, bot, 13)
		rrect(Rect2(inner.position, Vector2(inner.size.x, inner.size.y * 0.62)), top, 13, 0, Color.BLACK, true, [1, 1, 0, 0])
		var ic = inner.position + Vector2(inner.size.x / 2.0, inner.size.y * 0.47)
		for k in range(6):
			draw_circle(ic, 62 - k * 9, Color(1, 1, 1, 0.07))
		draw_icon(i, ic, i == 2 and nopair)
		text_c(inner.position + Vector2(inner.size.x / 2.0, 22), info[i][0], 24, Color(1, 1, 1), 7)
		var strip = Rect2(inner.position + Vector2(0, inner.size.y - 52), Vector2(inner.size.x, 52))
		rrect(strip, C("#ff5fa2") if on else C("#b3a7c4"), 13, 0, Color.BLACK, true, [0, 0, 1, 1])
		draw_line(strip.position, strip.position + Vector2(strip.size.x, 0), INK(), 5.0)
		var price: String = "MAX" if info[i][5] and i != 2 else "$ " + fmt(info[i][3])
		text_c(strip.get_center() + Vector2(0, 2), price, 30, Color(1, 1, 1), 8)

func draw_icon(i: int, c: Vector2, off: bool) -> void:
	if i == 0:
		var r = Rect2(c + Vector2(-56, -6), Vector2(112, 30))
		rrect(r.grow(4), INK(), 15)
		rrect(r, C("#7df0c8"), 12)
		rrect(Rect2(r.position + Vector2(10, 4), Vector2(92, 7)), Color(1, 1, 1, 0.8), 4)
		draw_rect(Rect2(c + Vector2(28, -40), Vector2(8, 28)), C("#ffffff"))
		draw_rect(Rect2(c + Vector2(18, -30), Vector2(28, 8)), C("#ffffff"))
	elif i == 1:
		draw_candy(1, c, 36.0)
		draw_rect(Rect2(c + Vector2(34, -50), Vector2(9, 32)), C("#ffffff"))
		draw_rect(Rect2(c + Vector2(22, -38), Vector2(33, 9)), C("#ffffff"))
	else:
		if off:
			for k in [-1, 1]:
				var p = c + Vector2(k * 30, k * 18)
				draw_circle(p, 25, INK())
				draw_circle(p, 22, C("#c9c2d6"))
		else:
			draw_candy(2, c + Vector2(-30, -18), 22.0)
			draw_candy(2, c + Vector2(30, 18), 22.0)
		var arrow = C("#ffffff") if not off else C("#e6e0ee")
		draw_colored_polygon(PackedVector2Array([c + Vector2(-8, -12), c + Vector2(6, -4), c + Vector2(-6, 4)]), arrow)
		draw_colored_polygon(PackedVector2Array([c + Vector2(8, 12), c + Vector2(-6, 4), c + Vector2(6, -4)]), arrow)

func draw_star(c: Vector2, r: float, col: Color) -> void:
	var pts = PackedVector2Array()
	var big = PackedVector2Array()
	for k in range(10):
		var an = -PI / 2 + k * PI / 5
		pts.append(c + Vector2(cos(an), sin(an)) * (r if k % 2 == 0 else r * 0.45))
		big.append(c + Vector2(cos(an), sin(an)) * ((r + 4) if k % 2 == 0 else (r + 4) * 0.5))
	draw_colored_polygon(big, INK())
	draw_colored_polygon(pts, col)

# ---------------------------------------------------------------- tutorial hand
func draw_tutorial() -> void:
	if state != "play" or ending >= 0.0:
		return
	var tut = L.get("tut", "")
	var target_pos = null
	var msg = ""
	if tut == "ball" and lt > 0.5 and nb < 3 and can_ball():
		target_pos = CARDS[1].get_center(); msg = "Tap to add a candy!"
	elif tut == "merge" and can_merge() and nm < 2:
		target_pos = CARDS[2].get_center(); msg = "2 same candies? MERGE!"
	elif tut == "pad" and can_pad() and np < 1:
		target_pos = CARDS[0].get_center(); msg = "More pads = more $"
	elif tut == "candy" and gift != null and gift.hp == gift.max:
		target_pos = gift.pos + Vector2(0, 70); msg = "Smash the candy!"
	elif tut == "aim" and not tut_done.has("aim") and lt > 1.0:
		target_pos = Vector2(200, 560); msg = "Tap to aim the drop!"
	elif tut == "orbit" and lt < 7.0:
		msg = "Candies orbit the planet!"
	elif tut == "moon" and lt < 6.0:
		msg = "Moons pay x2!"
	elif tut == "two" and lt < 6.0:
		msg = "Two planets, double gravity!"
	elif tut == "hole" and lt < 6.0:
		msg = "Avoid the black hole!"
	elif tut == "comet" and lt < 6.0:
		msg = "Hit the comet for a jackpot!"
	elif tut == "movplanet" and lt < 6.0:
		msg = "The planet is moving!"
	elif tut == "remix" and lt < 6.0:
		msg = "Low gravity remix!"
	elif tut == "portal" and lt < 7.0:
		msg = "Portals double your candy!"
	elif tut == "movp" and lt < 6.0:
		msg = "The portals are moving!"
	elif tut == "goldp" and lt < 6.0:
		msg = "Gold portal = x4!"
	elif tut == "trap" and lt < 6.0:
		msg = "Bottom portal sends you back up!"
	elif tut == "flip" and not tut_done.has("flip") and lt > 1.0:
		target_pos = Vector2(220, 860); msg = "Tap left / right to flip!"
	elif tut == "targets" and lt < 6.0:
		msg = "Drop all targets = x2 bonus!"
	elif tut == "movefb" and lt < 6.0:
		msg = "The bumpers move now!"
	elif tut == "super" and lt < 6.0:
		msg = "Gold bumper pays x3!"
	elif tut == "multi" and lt < 6.0:
		msg = "MULTIBALL!"
	elif tut == "edges" and lt < 6.0:
		msg = "Edges pay x10!"
	elif tut == "moving" and lt < 6.0:
		msg = "Watch out: the pegs move!"
	elif tut == "sour" and lt < 6.0:
		msg = "Avoid the SOUR buckets!"
	elif tut == "bumper" and lt < 6.0:
		msg = "Bumpers double your candy!"
	elif tut == "jackpot" and lt < 6.0:
		msg = "Aim for the moving x20 JACKPOT!"
	elif tut == "stars" and lt < 6.0:
		msg = "Finish fast for 3 stars!"
	if msg != "":
		var by = 960.0 if target_pos == null or target_pos.y > 900 else target_pos.y + 120
		var w = font.get_string_size(msg, HORIZONTAL_ALIGNMENT_LEFT, -1, 30).x + 44
		var rr = Rect2(360 - w / 2, by - 30 if target_pos == null or target_pos.y > 900 else by, w, 58)
		rrect(rr.grow(4), INK(), 30)
		rrect(rr, C("#ffffff"), 26)
		text_c(rr.get_center() + Vector2(0, 1), msg, 30, C("#ff5fa2"), 0)
	if target_pos != null:
		var bob = sin(t * 7.0) * 10.0
		draw_hand(target_pos + Vector2(26, 34 + bob))

func draw_hand(p: Vector2) -> void:
	# simple cartoon pointing hand (finger up-left)
	draw_set_transform(p + base_off, -0.45)
	rrect(Rect2(-24, -6, 48, 54), INK(), 18)
	rrect(Rect2(-20, -2, 40, 46), C("#ffffff"), 15)
	rrect(Rect2(-11, -52, 22, 56), INK(), 11)
	rrect(Rect2(-7, -48, 14, 50), C("#ffffff"), 7)
	for k in range(3):
		draw_line(Vector2(-12 + k * 10, 6), Vector2(-12 + k * 10, 20), C("#d6c8f0"), 3.0)
	draw_set_transform(base_off)

func draw_banner() -> void:
	var k: float = banner.t
	var sc = 0.5 + minf(1.0, k / 0.18) * 0.6 if k < 0.18 else 1.1 - minf(0.1, (k - 0.18) * 0.4)
	var a = 1.0 if k < 1.25 else maxf(0.0, 1.0 - (k - 1.25) / 0.35)
	var sz = int((84 if banner.big else 52) * sc)
	text_c(Vector2(360, 470), banner.txt, sz, C(banner.col, 1.0, a), 14, C(INKH, 1.0, a))

# ---------------------------------------------------------------- overlays
func panel(r: Rect2, col = "#fff0f6") -> void:
	nine("card", r.grow(12), 46, 70, 46, 46)

func big_button(r: Rect2, label: String, col: String) -> void:
	if col == "#b3a7c4":
		nine("pill", r.grow(6), 70, 60, 70, 70)
	else:
		nine("pill_w", r.grow(6), 70, 60, 70, 70)
	text_c(r.get_center() + Vector2(0, -2), label, 40, Color(1, 1, 1), 9)

func draw_end() -> void:
	var a = minf(1.0, screen_t / 0.25)
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.55 * a))
	var sc = 0.4 + 0.6 * minf(1.0, screen_t / 0.3)
	var r = Rect2(Vector2(360, 640) - Vector2(290, 360) * sc, Vector2(580, 720) * sc)
	panel(r)
	if sc < 0.98:
		return
	var rib = Rect2(130, 270, 460, 96)
	rrect(rib.grow(5), INK(), 30)
	rrect(rib, C("#ff5fa2"), 26)
	text_c(rib.get_center() + Vector2(0, 2), lvl_label(), 52, Color(1, 1, 1), 10)
	# stars pop one by one
	for k in range(3):
		var appear = 0.5 + k * 0.4
		var got = k < endinfo.stars
		var ss = 0.0 if screen_t < appear else minf(1.0, (screen_t - appear) / 0.18)
		var sz = (52.0 if k == 1 else 42.0) * (0.6 + 0.4 * ss + (0.25 * sin(minf(1.0, (screen_t - appear) / 0.3) * PI) if ss > 0 else 0.0))
		var pos = Vector2(240 + k * 120, 470 - (30 if k == 1 else 0))
		draw_star(pos, 50.0 if k == 1 else 40.0, C("#e6dcf5"))
		if got and ss > 0.0:
			draw_star(pos, sz, C("#ffd36b", 1.3))
		if got and absf(screen_t - appear) < 0.03 and not autoplay:
			pass
	text_c(Vector2(360, 590), "Time  " + ftime(endinfo.time), 34, C("#9b7bff"), 0)
	draw_coin(Vector2(300, 668), 24.0)
	text_l(Vector2(336, 668), "+%d" % endinfo.coins, 46, Color(1, 1, 1), 8)
	big_button(Rect2(190, 830, 340, 92), "NEXT", "#3fcf9f")
	text_c(Vector2(360, 982), "Map", 30, C("#9b7bff"), 0)

func draw_fail() -> void:
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.55))
	var r = Rect2(70, 300, 580, 680)
	panel(r)
	text_c(Vector2(360, 400), "OUT OF TIME!", 60, C("#ff4d6d"), 10)
	var p = clampf(earned / maxf(1.0, target()), 0.0, 1.0)
	text_c(Vector2(360, 520), "So close...", 40, C("#9b7bff"), 0)
	var bar = Rect2(140, 580, 440, 44)
	rrect(bar.grow(4), INK(), 24)
	rrect(bar, C("#ffffff"), 20)
	rrect(Rect2(bar.position, Vector2(bar.size.x * p, bar.size.y)), C("#3fcf9f"), 20)
	text_c(bar.get_center() + Vector2(0, 1), "%d%%" % int(p * 100), 30, Color(1, 1, 1), 7)
	big_button(Rect2(190, 830, 340, 92), "RETRY", "#ff5fa2")
	if boost_time > 0:
		big_button(Rect2(190, 700, 340, 84), "+15 s  (x%d)" % boost_time, "#3fcf9f")

func draw_newcandy() -> void:
	var k: float = popup.t
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.5 * minf(1.0, k / 0.2)))
	var sc = minf(1.0, k / 0.25)
	for i in range(12):
		var an = t * 0.6 + i * TAU / 12.0
		draw_line(Vector2(360, 600), Vector2(360, 600) + Vector2(cos(an), sin(an)) * 420.0 * sc, C("#ffffff", 1.0, 0.12), 34.0)
	text_c(Vector2(360, 380), "NEW!", int(70 * (0.5 + 0.5 * sc)), C("#ffd36b"), 12)
	var lv: int = popup.lv
	draw_candy(lv, Vector2(360, 610), 110.0 * (0.3 + 0.7 * sc) * (1.0 + 0.05 * sin(t * 4.0)))
	text_c(Vector2(360, 820), obj_name(lv), 56, Color(1, 1, 1), 10)
	text_c(Vector2(360, 885), "x%s per bounce" % fmt(pow(3.0, lv - 1)), 34, C("#7df0c8"), 7)
	if k > 0.6:
		text_c(Vector2(360, 1000), "Tap to continue", 28, C("#ffffff", 1.0, 0.6 + 0.4 * sin(t * 4.0)), 6)

func draw_drop() -> void:
	var k: float = popup.t
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.6 * minf(1.0, k / 0.2)))
	var sk: Dictionary = popup.skin
	var sc = minf(1.0, k / 0.3)
	for i in range(14):
		var an = t * 0.8 + i * TAU / 14.0
		draw_line(Vector2(360, 600), Vector2(360, 600) + Vector2(cos(an), sin(an)) * 480.0 * sc, C(sk.col, 1.2, 0.18), 30.0)
	text_c(Vector2(360, 360), "BOSS DEFEATED!", int(62 * (0.5 + 0.5 * sc)), C("#ffd36b"), 12)
	for j in range(5):
		draw_candy(1 + j * 2, Vector2(360 + (j - 2) * 120, 640 + absf(j - 2) * 30), (38.0 + (2 - absf(j - 2)) * 14.0) * sc, 0.0, 0.0, false, sk.id)
	text_c(Vector2(360, 800), "NEW SKIN: " + sk.name, 50, Color(1, 1, 1), 10)
	text_c(Vector2(360, 860), "New candies + new sounds!", 30, C("#7df0c8"), 6)
	if k > 0.6:
		text_c(Vector2(360, 1000), "Tap to continue", 28, C("#ffffff", 1.0, 0.6 + 0.4 * sin(t * 4.0)), 6)

# ---------------------------------------------------------------- map (Candy Crush path)
func map_nodes() -> Array:
	var nodes = []
	var n = clampi(LEVELS.size() - (map_world - 1) * 10, 0, 20 if map_world == 5 else 10)
	for i in range(n):
		nodes.append(Vector2(360 + sin(i * 0.95 + 0.4) * 190.0, 1050.0 - i * 118.0))
	return nodes

func map_max_scroll() -> float:
	var nodes = map_nodes()
	return maxf(0.0, 470.0 - (nodes[nodes.size() - 1].y - 150.0))

func focus_map() -> void:
	var nodes = map_nodes()
	var base = (map_world - 1) * 10
	var cur = clampi(unlocked - 1 - base, 0, nodes.size() - 1)
	map_scroll = clampf(700.0 - nodes[cur].y, 0.0, map_max_scroll())

func draw_map() -> void:
	var base = (map_world - 1) * 10
	var nodes = map_nodes()
	var w2 = map_world == 2
	var road = ["#ff7ab8", "#3fcf9f", "#4a6cf0", "#ff9a2e", "#9b7bff"][clampi(map_world - 1, 0, 4)]
	var road_l = ["#ffb3d6", "#a8f5dc", "#9fb6ff", "#ffd08a", "#d0c0ff"][clampi(map_world - 1, 0, 4)]
	var ext = nodes.duplicate()
	ext.insert(0, Vector2(300, 1290))
	ext.append(Vector2(360, nodes[nodes.size() - 1].y - 170.0))
	var path = catmull(ext, 6.0)
	base_off = Vector2(0, map_scroll)
	draw_set_transform(base_off)
	# decorations behind the road (repeated up the map)
	for off in [0.0, -900.0, -1800.0]:
		if nodes[nodes.size() - 1].y - 300.0 < 1000.0 + off:
			base_off = Vector2(0, map_scroll + off)
			draw_set_transform(base_off)
			map_decor(w2)
	base_off = Vector2(0, map_scroll)
	draw_set_transform(base_off)
	# the road: soft shadow, thick outline, candy road with diagonal stripes and a shiny edge
	cap_line(shifted(path, Vector2(0, 10)), C(INKH, 1.0, 0.25), 74.0)
	cap_line(path, INK(), 70.0)
	cap_line(path, C(road), 58.0)
	var acc = 0.0
	for i in range(1, path.size()):
		acc += path[i].distance_to(path[i - 1])
		if fmod(acc, 34.0) < 14.0:
			var tg = (path[i] - path[i - 1]).normalized()
			var nn = Vector2(-tg.y, tg.x)
			draw_line(path[i] - nn * 26.0 - tg * 8.0, path[i] + nn * 26.0 + tg * 8.0, C(road_l), 9.0, true)
	cap_line(shifted(path, Vector2(-3, -8)), Color(1, 1, 1, 0.28), 10.0)
	# the gate to the next world
	var gate = Rect2(220, nodes[nodes.size() - 1].y - 200.0, 280, 64)
	var next_open = unlocked > base + 10 and base + 10 < LEVELS.size()
	nine("pill_w" if next_open else "pill", gate.grow(10), 70, 60, 70, 70)
	text_c(gate.get_center() + Vector2(0, -2), "FINAL WORLD" if map_world == 5 else (("WORLD %d  >" % (map_world + 1)) if next_open else ("WORLD %d  LOCKED" % (map_world + 1))), 26, Color(1, 1, 1) if next_open else C("#9b7bff"), 6 if next_open else 0)
	var cur = clampi(unlocked - 1 - base, 0, nodes.size() - 1)
	for i in range(nodes.size()):
		var p: Vector2 = nodes[i]
		var idx = base + i
		var open = idx < unlocked
		if LEVELS[idx].has("boss"):
			draw_boss_icon(p, open, i == cur, LEVELS[idx].get("bkind", "gummy"))
		else:
			draw_level_node(p, i + 1, open, i == cur, i < cur)
		var st = best_stars.get(idx, 0)
		if st > 0:
			var yoff = 76.0 if LEVELS[idx].has("boss") else 44.0
			for s2 in range(3):
				draw_star(p + Vector2((s2 - 1) * 28, yoff + (6 if s2 == 1 else 0)), 12.0, C("#ffd36b") if s2 < st else C("#e6dcf5"))
	# player marker: the equipped candy hopping on the current level
	var hop = absf(sin(t * 3.2))
	var cp: Vector2 = nodes[cur] + Vector2(0, -78 - hop * 18.0)
	ell(nodes[cur] + Vector2(0, -50), 20.0 - hop * 6.0, 6.0, C(INKH, 1.0, 0.25))
	draw_candy(2, cp, 26.0, (1.0 - hop) * 0.6)
	base_off = Vector2.ZERO
	draw_set_transform(Vector2.ZERO)
	# fixed bands (header + bottom bar) so the scrolling path slides under them
	draw_texture_rect_region(bgtex, Rect2(0, 0, 720, 316), Rect2(0, 0, 64, 256.0 * 316.0 / 1280.0))
	draw_line(Vector2(0, 316), Vector2(720, 316), C(INKH, 1.0, 0.15), 6.0)
	draw_texture_rect_region(bgtex, Rect2(0, 1120, 720, 160), Rect2(0, 256.0 * 1120.0 / 1280.0, 64, 256.0 * 160.0 / 1280.0))
	draw_line(Vector2(0, 1120), Vector2(720, 1120), C(INKH, 1.0, 0.15), 6.0)
	if map_world > 1:
		var back = Rect2(520, 1124, 170, 50)
		nine("pill_w", back.grow(6), 70, 60, 70, 70)
		text_c(back.get_center() + Vector2(0, -2), "< WORLD %d" % (map_world - 1), 22, Color(1, 1, 1), 6)
	# header
	var bn = Rect2(110, 40, 500, 92)
	nine("card", bn.grow(10), 46, 60, 46, 46)
	text_c(bn.get_center() + Vector2(0, -16), "WORLD %d" % map_world, 24, Color(1, 1, 1), 6)
	text_c(bn.get_center() + Vector2(0, 22), WORLD_NAMES[clampi(map_world - 1, 0, 4)], 38, C("#ff5fa2"), 0)
	draw_coin(Vector2(58, 1140), 16.0)
	text_l(Vector2(82, 1140), str(coins), 26, Color(1, 1, 1), 6)
	draw_star_bar(map_world)
	big_button(Rect2(160, 1170, 360, 86), "PLAY  " + lvl_name(clampi(unlocked - 1, 0, LEVELS.size() - 1)), "#3fcf9f")
	img("round", Rect2(600, 1180, 90, 90))
	img("round", Rect2(30, 1180, 90, 90))
	draw_gear(Vector2(75, 1220), 24.0)
	draw_candy(lv_icon(), Vector2(645, 1220), 24.0)

func draw_level_node(p: Vector2, n: int, open: bool, cur: bool, done: bool) -> void:
	# glossy candy button with a thick bottom edge (pressed-button look)
	var r = 40.0
	var top = "#ffd36b" if cur else ("#ff5fa2" if done else "#e6dcf5")
	var side = "#e0a020" if cur else ("#c23a7a" if done else "#b3a7c4")
	if cur:
		for k in range(4):
			draw_circle(p, r + 16 + k * 8 + sin(t * 4.0) * 4.0, C("#ffffff", 1.3, 0.09))
	draw_circle(p + Vector2(0, 12), r + 6, C(INKH, 1.0, 0.3))
	draw_circle(p + Vector2(0, 8), r + 5, INK())
	draw_circle(p, r + 5, INK())
	draw_circle(p + Vector2(0, 8), r, C(side))
	draw_circle(p, r, C(top))
	draw_circle(p + Vector2(0, -4), r * 0.82, C(top).lightened(0.12))
	ell(p + Vector2(-r * 0.32, -r * 0.42), r * 0.34, r * 0.16, Color(1, 1, 1, 0.75))
	if open:
		text_c(p + Vector2(0, 1), str(n), 36, Color(1, 1, 1), 8)
	else:
		# small lock
		rrect(Rect2(p + Vector2(-13, -2), Vector2(26, 20)), C("#9b8cb4"), 5)
		draw_arc(p + Vector2(0, -4), 9, PI, TAU, 12, C("#9b8cb4"), 5.0, true)
		draw_circle(p + Vector2(0, 7), 3.5, C("#e6dcf5"))

func draw_boss_icon(p: Vector2, open: bool, cur: bool, kind = "gummy") -> void:
	if open:
		for k in range(4):
			draw_circle(p, 62 + k * 9 + sin(t * 3.0) * 4.0, C("#ff4d6d", 1.4, 0.07))
	var bob = sin(t * 3.0) * 3.0 if open else 0.0
	var sc = {"gummy": 0.5, "cupcake": 0.5, "choco": 0.48, "lolli": 0.52, "donut": 0.55, "sundae": 0.5, "ginger": 0.45, "jelly": 0.42, "mallow": 0.5, "cloud": 0.42, "gumball": 0.42, "overlord": 0.45}[kind]
	draw_boss_body(kind, p + Vector2(0, -8 + bob), sc, 1.0, false, t * 1.5 if kind == "lolli" else 0.0, p + Vector2(0, 80), not open, 0.0)
	var rb = Rect2(p + Vector2(-46, 30), Vector2(92, 28))
	draw_colored_polygon(PackedVector2Array([rb.position + Vector2(-14, 4), rb.position + Vector2(4, 4), rb.position + Vector2(4, 26), rb.position + Vector2(-14, 26), rb.position + Vector2(-6, 15)]), INK())
	draw_colored_polygon(PackedVector2Array([rb.end + Vector2(14, -24), rb.end + Vector2(-4, -24), rb.end + Vector2(-4, -2), rb.end + Vector2(14, -2), rb.end + Vector2(6, -13)]), INK())
	rrect(rb.grow(4), INK(), 8)
	rrect(rb, C("#9b7bff") if open else C("#b3a7c4"), 6)
	text_c(rb.get_center() + Vector2(0, 1), "BOSS", 22, Color(1, 1, 1), 5)

func map_decor(w2: bool) -> void:
	if not w2:
		# lollipops and gumdrops
		for d in [Vector2(105, 1010), Vector2(625, 770), Vector2(90, 530), Vector2(645, 330)]:
			draw_line(d, d + Vector2(0, 80), INK(), 12.0)
			draw_line(d, d + Vector2(0, 80), C("#fff1d6"), 6.0)
			draw_circle(d, 40, INK())
			draw_circle(d, 35, C("#ff7ab8"))
			draw_arc(d, 22, 0, TAU * 0.8, 24, C("#ffffff", 1.0, 0.7), 7.0, true)
			draw_arc(d, 10, 0, TAU * 0.7, 16, C("#ffffff", 1.0, 0.7), 6.0, true)
		for g in [[Vector2(600, 1060), "#7df0c8"], [Vector2(150, 780), "#ffd36b"], [Vector2(560, 560), "#9b7bff"], [Vector2(170, 330), "#8fd8ff"]]:
			gumdrop(g[0], g[1])
	else:
		# mint pegs and a little plinko board in the background
		for d in [Vector2(100, 980), Vector2(630, 760), Vector2(95, 520), Vector2(640, 320)]:
			for k in range(3):
				for j in range(3 - k):
					var q = d + Vector2((j - (2 - k) / 2.0) * 26.0, k * 22.0)
					draw_circle(q, 9, INK())
					draw_circle(q, 6.5, C("#7df0c8"))
		for g in [[Vector2(600, 1060), "#ff8fc6"], [Vector2(150, 780), "#ffd36b"], [Vector2(560, 560), "#3fcf9f"], [Vector2(170, 330), "#8fd8ff"]]:
			gumdrop(g[0], g[1])

func gumdrop(p: Vector2, col: String) -> void:
	var pts = PackedVector2Array()
	for k in range(21):
		var an = PI + k * PI / 20.0
		pts.append(p + Vector2(cos(an) * 30.0, sin(an) * 34.0))
	pts.append(p + Vector2(30, 6))
	pts.append(p + Vector2(-30, 6))
	var o = PackedVector2Array()
	for q in pts:
		o.append(p + (q - p) * 1.0 + (q - p).normalized() * 4.0)
	draw_colored_polygon(o, INK())
	draw_colored_polygon(pts, C(col))
	for k in range(6):
		draw_circle(p + Vector2(-16 + k * 7, -12 + (k % 2) * 10), 2.2, Color(1, 1, 1, 0.8))
	ell(p + Vector2(-10, -20), 7, 4, Color(1, 1, 1, 0.7))


# ================================================================ UI pack (Cozy UI by dobo_ui, recolored) + skins
func img_tex(name: String):
	if tex.has(name):
		return tex[name]
	var im = Image.load_from_file(ProjectSettings.globalize_path("res://ui/%s.png" % name))
	var tt = ImageTexture.create_from_image(im) if im != null else null
	tex[name] = tt
	return tt

func img(name: String, r: Rect2, mod = Color(1, 1, 1)) -> void:
	var tt = img_tex(name)
	if tt != null:
		draw_texture_rect(tt, r, false, mod)

func nine(name: String, r: Rect2, ml: int, mt: int, mr: int, mb: int) -> void:
	var tt = img_tex(name)
	if tt == null:
		rrect(r, C("#fff0f6"), 30, 6, INK())
		return
	var sbt = StyleBoxTexture.new()
	sbt.texture = tt
	sbt.texture_margin_left = ml
	sbt.texture_margin_top = mt
	sbt.texture_margin_right = mr
	sbt.texture_margin_bottom = mb
	draw_style_box(sbt, r)

func skin_by_id(id: String) -> Dictionary:
	for sk in SKINS:
		if sk.id == id:
			return sk
	return SKINS[0]

func obj_name(lv: int) -> String:
	var sk = skin_by_id(equip)
	if sk.has("base"):
		return "Star " + skin_by_id(sk.base).objs[clampi(lv - 1, 0, 9)]
	return sk.objs[clampi(lv - 1, 0, 9)]

func skin_objs(sk: Dictionary) -> Array:
	return skin_by_id(sk.base).objs if sk.has("base") else sk.objs

func lv_icon() -> int:
	return 2

func obj_col(lv: int) -> String:
	match equip:
		"fruits":
			return ["#4a6cf0", "#e0283c", "#ff4d6d", "#ffe14d", "#ff9a2e", "#ff4d4d", "#ffb08a", "#ffd23a", "#9be15d", "#3fcf5f"][clampi(lv - 1, 0, 9)]
		"space":
			return ["#cfe8ff", "#a49a90", "#e6e6f0", "#e0603a", "#3a8ff0", "#4a6cf0", "#e8c890", "#e0a060", "#ffd23a", "#9b4dff"][clampi(lv - 1, 0, 9)]
		"gems":
			return ["#e8f4ff", "#b06cff", "#ffc83d", "#2fd47a", "#3a7bff", "#ff3a5a", "#9ff0ff", "#ff9fd0", "#3a3a52", "#ffffff"][clampi(lv - 1, 0, 9)]
		"retro":
			return ["#4a6cf0", "#7a3aa0", "#e0283c", "#ff9a2e", "#e0283c", "#ffb08a", "#ffb21e", "#ffd23a", "#ffe14d", "#ffd36b"][clampi(lv - 1, 0, 9)]
		"music":
			return ["#ff5fa2", "#9b7bff", "#ff9a2e", "#3fcf9f", "#ffd23a", "#e0603a", "#ffb21e", "#ffffff", "#ffe6a0", "#ffd36b"][clampi(lv - 1, 0, 9)]
	return candy_col(lv)

# ---------------------------------------------------------------- per-skin sounds
func snd_bounce(idx: int) -> void:
	if my_song_on and my_song_ok:
		# the song only plays while candies keep bouncing: each bounce buys a little more of it
		song_until = Time.get_ticks_msec() / 1000.0 + 0.3
		return
	match equip:
		"fruits":
			play("fruit_pop%d" % (1 + rng.randi() % 3), semis(idx) * 0.7, -8.0)
		"space":
			play("space_pop%d" % (1 + rng.randi() % 3), semis(idx) * 0.6, -14.0)
		"gems":
			play("gem_pop%d" % (1 + rng.randi() % 3), semis(idx) * 0.5, -12.0)
		"retro":
			play("retro_pop", semis(idx) * 0.6, -16.0)
		"music":
			# every bounce plays the next note of an original little tune
			play("marimba", pow(2.0, MELODY[mel_i % MELODY.size()] / 12.0), -8.0)
			mel_i += 1
		_:
			play("pop%d" % (1 + rng.randi() % 3), semis(idx) * 0.8, -10.0)

func snd_merge(lv: int) -> void:
	match equip:
		"fruits":
			play("fruit_merge", semis(lv) * 0.8, -4.0)
		"space":
			play("space_merge", semis(lv) * 0.7, -6.0)
		"gems":
			play("gem_merge", semis(lv) * 0.6, -5.0)
		"music":
			play("chord", semis(lv) * 0.8, -4.0)
		"retro":
			play("retro_merge", semis(lv) * 0.7, -10.0)
		_:
			play("match%d" % clampi(lv - 1, 1, 9), 1.0, -3.0)

func snd_spawn() -> void:
	match equip:
		"space":
			play("space_spawn", 1.0 + rng.randf() * 0.15, -12.0)
		"gems":
			play("gem_pop1", 1.4, -14.0)
		"retro":
			play("retro_spawn", 1.0, -16.0)
		_:
			play("spawn", 1.0 + rng.randf() * 0.15, -10.0)

# ---------------------------------------------------------------- objects of the other skins (procedural, our own drawings)
func draw_obj(sk: String, lv: int, p: Vector2, r: float, sq: float, rot: float, gold: bool) -> void:
	var keep = equip
	equip = sk
	var col = obj_col(lv)
	equip = keep
	var ink = INK()
	draw_circle(p + Vector2(0, r * 0.25), r + 3, Color(0.2, 0.05, 0.25, 0.25))
	draw_set_transform(p + base_off, rot if sk != "music" else 0.0, Vector2(1.0 + sq * 0.16, 1.0 - sq * 0.16))
	match sk:
		"fruits":
			fruit(lv, r, C(col))
		"space":
			planet(lv, r, C(col))
		"gems":
			gem(lv, r, C(col))
		"music":
			music(lv, r, C(col))
		"donuts":
			var icing = ["#fff1d6", "#ffe3a0", "#ff8fc6", "#6b3a1e", "#ff5fa2", "#8fd88f", "#d9944a", "#9b7bff", "#ffffff", "#ffd36b"][clampi(lv - 1, 0, 9)]
			draw_arc(Vector2.ZERO, r * 0.66, 0, TAU, 32, INK(), r * 0.8 + 6, true)
			draw_arc(Vector2.ZERO, r * 0.66, 0, TAU, 32, C("#e8b273"), r * 0.8, true)
			draw_arc(Vector2(0, -r * 0.06), r * 0.64, 0, TAU, 32, C(icing, 1.4 if lv == 10 else 1.0), r * 0.58, true)
			if lv in [3, 8]:
				for k in range(10):
					var an = k * TAU / 10.0
					draw_circle(Vector2(cos(an), sin(an)) * r * 0.64, r * 0.06, C(["#7df0c8", "#ffd36b", "#8fd8ff"][k % 3]))
		"cookies":
			var cc2 = ["#e8c08a", "#e8b273", "#d99a5b", "#2a1a14", "#c97a3a", "#ff9fd0", "#f2d6a0", "#b8642e", "#8fd8ff", "#ffd36b"][clampi(lv - 1, 0, 9)]
			draw_circle(Vector2.ZERO, r + 3, INK())
			draw_circle(Vector2.ZERO, r, C(cc2, 1.4 if lv == 10 else 1.0))
			if lv in [3, 7]:
				for q in [Vector2(-0.4, -0.3), Vector2(0.35, -0.4), Vector2(0.1, 0.25), Vector2(-0.35, 0.4)]:
					draw_circle(q * r, r * 0.13, C("#5a2d14"))
			if lv == 4:
				draw_circle(Vector2.ZERO, r * 0.7, C("#fff1d6"))
				draw_circle(Vector2.ZERO, r * 0.6, C("#2a1a14"))
			if lv == 6:
				draw_rect(Rect2(-r, -r * 0.15, r * 2, r * 0.3), C("#fff1d6"))
			gloss(r)
		"jellybeans":
			var jc = ["#ffb3d6", "#8bd63a", "#e0283c", "#ffe14d", "#9b4dff", "#ff9a2e", "#4a6cf0", "#ff7ab8", "#ffffff", "#ffd36b"][clampi(lv - 1, 0, 9)]
			ell(Vector2.ZERO, r * 0.8 + 3, r * 1.05 + 3, INK())
			ell(Vector2.ZERO, r * 0.8, r * 1.05, C(jc, 1.4 if lv == 10 else 1.0))
			if lv == 9:
				for k in range(4):
					ell(Vector2(0, -r * 0.6 + k * r * 0.4), r * 0.6, r * 0.12, C(["#ff5fa2", "#ffd36b", "#7df0c8", "#9b7bff"][k]))
			ell(Vector2(-r * 0.25, -r * 0.4), r * 0.18, r * 0.3, Color(1, 1, 1, 0.7))
		"icecream":
			var scol = ["#ffb3d6", "#fff1d6", "#ff9fd0", "#9fe6c0", "#8a5a3a", "#fff1d6", "#ff9fd0", "#ffd36b", "#fff1d6", "#ffd36b"][clampi(lv - 1, 0, 9)]
			if lv >= 6:
				var cone = PackedVector2Array([Vector2(-r * 0.6, 0), Vector2(r * 0.6, 0), Vector2(0, r * 1.3)])
				draw_colored_polygon(PackedVector2Array([Vector2(-r * 0.7, -3), Vector2(r * 0.7, -3), Vector2(0, r * 1.42)]), INK())
				draw_colored_polygon(cone, C("#e8b273"))
			draw_circle(Vector2(0, -r * 0.1), r * 0.85 + 3, INK())
			draw_circle(Vector2(0, -r * 0.1), r * 0.85, C(scol, 1.4 if lv == 10 else 1.0))
			if lv >= 7:
				draw_circle(Vector2(0, -r * 0.75), r * 0.5 + 3, INK())
				draw_circle(Vector2(0, -r * 0.75), r * 0.5, C("#ff9fd0"))
			gloss(r)
		"planets":
			planet(clampi(lv, 1, 10), r, C(["#cfe8ff", "#7df0c8", "#ff5fa2", "#d9944a", "#ff7ab8", "#8fd8ff", "#e8c890", "#ff4d6d", "#ffd36b", "#ffb21e"][clampi(lv - 1, 0, 9)]))
		"clouds":
			var cc3 = C(["#ffffff", "#ffb3d6", "#9fd8ff", "#e0c8ff", "#c8d0e0", "#ffe3a0", "#a0a8c0", "#fff0f6", "#d9c8ff", "#ffd36b"][clampi(lv - 1, 0, 9)], 1.3 if lv == 10 else 1.0)
			for q in [Vector2(-0.45, 0.15), Vector2(0, -0.2), Vector2(0.45, 0.15), Vector2(0, 0.25)]:
				draw_circle(q * r, r * 0.62 + 3, INK())
			for q in [Vector2(-0.45, 0.15), Vector2(0, -0.2), Vector2(0.45, 0.15), Vector2(0, 0.25)]:
				draw_circle(q * r, r * 0.62, cc3)
			if lv == 6:
				for k in range(4):
					draw_arc(Vector2(0, r * 0.4), r * (0.9 - k * 0.15), PI, TAU, 12, C(["#ff5fa2", "#ffd36b", "#7df0c8", "#8fd8ff"][k]), 3.0, true)
			if lv in [5, 7]:
				for k in range(3):
					draw_line(Vector2(-r * 0.4 + k * r * 0.4, r * 0.7), Vector2(-r * 0.5 + k * r * 0.4, r * 1.0), C("#8fd8ff"), 3.0)
			ell(Vector2(-r * 0.2, -r * 0.4), r * 0.25, r * 0.12, Color(1, 1, 1, 0.8))
		"gumballs":
			var gc = C(["#ffb3d6", "#ff4d6d", "#4fa3ff", "#3fcf5f", "#ffd23a", "#9b4dff", "#ff9a2e", "#2a1650", "#ff5fa2", "#ffd36b"][clampi(lv - 1, 0, 9)], 1.3 if lv == 10 else 1.0)
			draw_circle(Vector2.ZERO, r + 3, INK())
			draw_circle(Vector2.ZERO, r, gc)
			if lv == 7:
				draw_line(Vector2(-r, 0), Vector2(r, 0), Color(1, 1, 1, 0.8), r * 0.3)
			if lv == 8:
				for k in range(6):
					draw_circle(Vector2(cos(k * 2.1), sin(k * 2.1)) * r * 0.5, 2.0, Color(1.4, 1.4, 1.6))
			gloss(r)
		"crown":
			if lv <= 3:
				var cn = C(["#d9944a", "#d9dbe6", "#ffd36b"][lv - 1])
				draw_circle(Vector2.ZERO, r + 3, INK())
				draw_circle(Vector2.ZERO, r, cn)
				draw_arc(Vector2.ZERO, r * 0.7, 0, TAU, 24, cn.darkened(0.2), 3.0, true)
				text_c(Vector2(0, 2), "$", int(r), Color(1, 1, 1), 0)
			elif lv <= 5:
				draw_arc(Vector2(0, r * 0.15), r * 0.7, 0, TAU, 28, INK(), r * 0.38 + 6, true)
				draw_arc(Vector2(0, r * 0.15), r * 0.7, 0, TAU, 28, C("#ffd36b"), r * 0.38, true)
				draw_circle(Vector2(0, -r * 0.6), r * 0.35 + 3, INK())
				draw_circle(Vector2(0, -r * 0.6), r * 0.35, C("#ff3a5a" if lv == 4 else "#3a7bff"))
			elif lv <= 8:
				gem([0, 0, 0, 0, 0, 6, 0, 8][lv - 1], r, C(["", "", "", "", "", "#ff3a5a", "#9b4dff", "#3fcf9f"][lv - 1]))
			else:
				boss_crown(Vector2(0, 0), r / 32.0, false)
				if lv == 10:
					draw_arc(Vector2.ZERO, r + 4, 0, TAU, 24, C("#ffd36b", 2.0), 3.0, true)
		"retro":
			var tt = img_tex_path("res://pixel/%d.png" % lv)
			if tt != null:
				draw_texture_rect(tt, Rect2(-r * 1.25, -r * 1.25, r * 2.5, r * 2.5), false)
	if gold:
		draw_arc(Vector2.ZERO, r + 6, 0, TAU, 32, C("#ffd36b", 2.2, 0.9), 4.0, true)
	draw_set_transform(base_off)

func gloss(r: float) -> void:
	ell(Vector2(-r * 0.35, -r * 0.38), r * 0.3, r * 0.16, Color(1, 1, 1, 0.75))

func fruit(lv: int, r: float, col: Color) -> void:
	var ink = INK()
	var leaf = C("#3fcf5f")
	match lv:
		3: # strawberry
			var pts = PackedVector2Array()
			for k in range(28):
				var an = k * TAU / 28.0
				var rr2 = r * (1.0 - 0.25 * maxf(0.0, sin(an)))
				pts.append(Vector2(cos(an) * rr2 * (1.0 - 0.3 * maxf(0.0, sin(an))), sin(an) * r))
			var o = PackedVector2Array()
			for q in pts:
				o.append(q * 1.0 + q.normalized() * 3.0)
			draw_colored_polygon(o, ink)
			draw_colored_polygon(pts, col)
			for q in [Vector2(-0.4, -0.2), Vector2(0.3, -0.3), Vector2(0, 0.1), Vector2(-0.2, 0.45), Vector2(0.35, 0.25)]:
				ell(q * r, r * 0.06, r * 0.1, C("#fff3a0"))
			for k in range(-1, 2):
				draw_colored_polygon(PackedVector2Array([Vector2(k * r * 0.3, -r * 0.8), Vector2(k * r * 0.3 - r * 0.2, -r * 1.15), Vector2(k * r * 0.3 + r * 0.2, -r * 1.15)]), leaf)
		4: # lemon
			ell(Vector2.ZERO, r * 1.1 + 3, r * 0.82 + 3, ink)
			ell(Vector2.ZERO, r * 1.1, r * 0.82, col)
			draw_circle(Vector2(r * 1.05, 0), r * 0.18, col)
			draw_circle(Vector2(-r * 1.05, 0), r * 0.18, col)
			gloss(r)
		8: # pineapple
			for k in range(-1, 2):
				draw_colored_polygon(PackedVector2Array([Vector2(k * r * 0.25, -r * 0.7), Vector2(k * r * 0.45, -r * 1.45), Vector2(k * r * 0.25 + r * 0.18, -r * 0.7)]), leaf)
			ell(Vector2(0, r * 0.1), r * 0.82 + 3, r * 1.0 + 3, ink)
			ell(Vector2(0, r * 0.1), r * 0.82, r * 1.0, col)
			for k in range(-2, 3):
				draw_line(Vector2(k * r * 0.3 - r * 0.4, -r * 0.7), Vector2(k * r * 0.3 + r * 0.4, r * 0.9), C("#c8901a"), 2.0)
				draw_line(Vector2(k * r * 0.3 + r * 0.4, -r * 0.7), Vector2(k * r * 0.3 - r * 0.4, r * 0.9), C("#c8901a"), 2.0)
		10: # watermelon slice-ball
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, C("#2fa84a"))
			for k in range(6):
				var an = k * TAU / 6.0
				draw_arc(Vector2.ZERO, r * 0.8, an - 0.15, an + 0.15, 6, C("#1a6e2e"), r * 0.4, true)
			gloss(r)
		_:
			draw_circle(Vector2.ZERO, r + 3, ink)
			draw_circle(Vector2.ZERO, r, col)
			draw_circle(Vector2(r * 0.12, r * 0.15), r * 0.82, col.darkened(0.12))
			if lv == 5:
				for k in range(9):
					var an = k * 0.7
					draw_circle(Vector2(cos(an), sin(an)) * r * 0.55, r * 0.05, col.darkened(0.25))
			if lv == 7:
				draw_arc(Vector2(r * 0.2, 0), r * 0.75, PI * 0.6, PI * 1.4, 10, col.darkened(0.3), 3.0, true)
			if lv == 9:
				for k in range(5):
					draw_arc(Vector2.ZERO, r * 0.9, k * 1.26, k * 1.26 + 0.2, 4, C("#5fa83a"), 3.0, true)
			gloss(r)
			if lv in [2, 6, 7]:
				draw_line(Vector2(0, -r * 0.9), Vector2(r * 0.25, -r * 1.4), C("#6b3a1a"), 4.0, true)
				ell(Vector2(r * 0.45, -r * 1.25), r * 0.28, r * 0.13, leaf)
			if lv == 1:
				for k in range(5):
					var an = -PI / 2 + k * TAU / 5.0
					draw_line(Vector2(0, -r * 0.55), Vector2(0, -r * 0.55) + Vector2(cos(an), sin(an)) * r * 0.22, C("#2a3a8a"), 2.5, true)

func planet(lv: int, r: float, col: Color) -> void:
	var ink = INK()
	if lv == 9:
		for k in range(12):
			var an = k * TAU / 12.0 + t * 0.4
			draw_colored_polygon(PackedVector2Array([Vector2(cos(an - 0.12), sin(an - 0.12)) * r * 0.9, Vector2(cos(an), sin(an)) * r * 1.35, Vector2(cos(an + 0.12), sin(an + 0.12)) * r * 0.9]), C("#ff9a2e", 1.4))
	if lv == 10:
		draw_arc(Vector2.ZERO, r * 1.1, 0, TAU, 40, C("#c06bff", 1.8, 0.8), r * 0.35, true)
	if lv == 7:
		draw_arc(Vector2.ZERO, r * 1.45, PI, TAU, 24, ink, 7.0, true)
	draw_circle(Vector2.ZERO, r + 3, ink)
	draw_circle(Vector2.ZERO, r, C("#0b0614") if lv == 10 else col)
	match lv:
		1:
			for k in range(6):
				var an = k * TAU / 6.0 + t
				draw_circle(Vector2(cos(an), sin(an)) * r * 0.5, r * 0.12, Color(1.5, 1.5, 1.8, 0.9))
		2, 3:
			for q in [Vector2(-0.3, -0.2), Vector2(0.35, 0.1), Vector2(-0.1, 0.45)]:
				draw_circle(q * r, r * 0.2, col.darkened(0.2))
		4:
			for q in [Vector2(-0.3, -0.25), Vector2(0.3, 0.3)]:
				ell(q * r, r * 0.3, r * 0.15, col.darkened(0.25))
		5:
			for q in [Vector2(-0.35, -0.2), Vector2(0.3, 0.25), Vector2(0.25, -0.45)]:
				ell(q * r, r * 0.32, r * 0.22, C("#3fcf5f"))
		6, 8:
			for k in range(-2, 3):
				draw_line(Vector2(-r * 0.95 + absf(k) * r * 0.15, k * r * 0.33), Vector2(r * 0.95 - absf(k) * r * 0.15, k * r * 0.33), col.darkened(0.2) if k % 2 == 0 else col.lightened(0.2), r * 0.16)
			if lv == 8:
				ell(Vector2(r * 0.35, r * 0.3), r * 0.25, r * 0.14, C("#c0402a"))
		9:
			draw_circle(Vector2.ZERO, r * 0.8, C("#ffe14d", 1.5))
	if lv == 7:
		draw_arc(Vector2.ZERO, r * 1.45, 0, PI, 24, ink, 7.0, true)
		draw_arc(Vector2.ZERO, r * 1.45, 0, PI, 24, C("#f0dca0"), 4.0, true)
	if lv != 10:
		gloss(r)

func gem(lv: int, r: float, col: Color) -> void:
	var ink = INK()
	var sides = [6, 8, 5, 8, 6, 10, 12, 4, 0, 8][clampi(lv - 1, 0, 9)]
	if sides == 0:
		draw_circle(Vector2.ZERO, r + 3, ink)
		draw_circle(Vector2.ZERO, r, col)
		gloss(r)
		return
	var pts = PackedVector2Array()
	var o = PackedVector2Array()
	for k in range(sides):
		var an = -PI / 2 + k * TAU / sides
		var sx = 1.0 if lv != 4 else 1.15
		pts.append(Vector2(cos(an) * r * sx, sin(an) * r))
		o.append(Vector2(cos(an) * (r * sx + 4), sin(an) * (r + 4)))
	draw_colored_polygon(o, ink)
	draw_colored_polygon(pts, col)
	var inner = PackedVector2Array()
	for q in pts:
		inner.append(q * 0.55)
	draw_colored_polygon(inner, col.lightened(0.25))
	for k in range(sides):
		draw_line(pts[k], inner[k], col.darkened(0.25), 2.0, true)
	if lv == 7:
		draw_colored_polygon(inner, Color(1.3, 0.8, 1.4, 0.5))
	if lv == 10:
		for k in range(4):
			var an = t * 2.0 + k * PI / 2
			draw_line(Vector2.ZERO, Vector2(cos(an), sin(an)) * r * 1.4, Color(1.8, 1.8, 1.8, 0.6), 3.0, true)
	ell(Vector2(-r * 0.25, -r * 0.35), r * 0.22, r * 0.1, Color(1, 1, 1, 0.85))

func music(lv: int, r: float, col: Color) -> void:
	var ink = INK()
	draw_circle(Vector2.ZERO, r + 3, ink)
	draw_circle(Vector2.ZERO, r, col if lv < 10 else C("#ffd36b", 1.3))
	if lv == 10 or lv == 8:
		for k in range(3):
			draw_arc(Vector2.ZERO, r * (0.45 + k * 0.17), 0, TAU, 28, col.darkened(0.2), 1.5, true)
		draw_circle(Vector2.ZERO, r * 0.22, ink)
	var w = Color(1, 1, 1) if lv not in [8, 9, 10] else ink
	# note glyph(s)
	var notes = 1 if lv in [1, 3, 5] else 2
	for k in range(notes):
		var x = -r * 0.25 + k * r * 0.45 - (r * 0.1 if notes == 1 else r * 0.2)
		ell(Vector2(x, r * 0.3), r * 0.2, r * 0.15, w)
		draw_line(Vector2(x + r * 0.17, r * 0.3), Vector2(x + r * 0.17, -r * 0.45), w, 3.0)
	if notes == 2:
		draw_line(Vector2(-r * 0.28, -r * 0.45), Vector2(r * 0.17 + r * 0.25 - r * 0.2, -r * 0.45), w, 5.0)
	else:
		draw_line(Vector2(r * 0.07, -r * 0.45), Vector2(r * 0.35, -r * 0.2), w, 3.0)
	gloss(r)

# ---------------------------------------------------------------- skins tab
func open_skins(from: String) -> void:
	skins_from = from
	state = "skins"
	screen_t = 0.0
	for i in range(SKINS.size()):
		if SKINS[i].id == equip:
			sel_skin = i
			skin_page = i / 6
	play("swipe", 1.1, -6.0)

func skin_card_rect(i: int) -> Rect2:
	i = i % 6
	var col = i % 3
	var row = i / 3
	return Rect2(42 + col * 218, 170 + row * 254, 200, 236)

func skins_input(pos: Vector2) -> void:
	if Rect2(20, 44, 150, 72).has_point(pos):
		state = "book"; book_page = 0
		play("swipe", 1.2, -6.0)
		return
	if Rect2(620, 40, 80, 80).has_point(pos):
		state = skins_from
		play("swipe", 0.9, -6.0)
		return
	var pages = int(ceil(SKINS.size() / 6.0))
	if Rect2(36, 664, 110, 40).has_point(pos):
		skin_page = (skin_page - 1 + pages) % pages
		play("swipe", 1.2, -8.0)
		return
	if Rect2(574, 664, 110, 40).has_point(pos):
		skin_page = (skin_page + 1) % pages
		play("swipe", 1.2, -8.0)
		return
	for i in range(skin_page * 6, mini(SKINS.size(), skin_page * 6 + 6)):
		if skin_card_rect(i).has_point(pos):
			sel_skin = i
			play("pop2", 1.2, -8.0)
			return
	var sk = SKINS[sel_skin]
	if Rect2(190, 1150, 340, 90).has_point(pos):
		if skins.has(sk.id):
			equip = sk.id
			play("match3", 1.0, -6.0)
			save_game()
		elif sk.how == "shop" and coins >= sk.price:
			coins -= sk.price
			skins[sk.id] = true
			equip = sk.id
			play("cash", 1.0, -4.0)
			save_game()

func draw_skins() -> void:
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.35))
	text_c(Vector2(360, 82), "SKINS", 64, Color(1, 1, 1), 12)
	img("close", Rect2(620, 40, 80, 80))
	draw_coin(Vector2(316, 136), 16.0)
	text_l(Vector2(340, 136), str(coins), 26, Color(1, 1, 1), 6)
	nine("pill_w", Rect2(20, 44, 150, 72), 70, 60, 70, 70)
	text_c(Vector2(95, 76), "BOOK", 30, Color(1, 1, 1), 7)
	var pages = int(ceil(SKINS.size() / 6.0))
	text_c(Vector2(360, 684), "%d / %d" % [skin_page + 1, pages], 24, Color(1, 1, 1), 6)
	text_c(Vector2(90, 684), "<  PREV", 24, Color(1, 1, 1), 6)
	text_c(Vector2(630, 684), "NEXT  >", 24, Color(1, 1, 1), 6)
	for i in range(skin_page * 6, mini(SKINS.size(), skin_page * 6 + 6)):
		var sk = SKINS[i]
		var r = skin_card_rect(i)
		var owned = skins.has(sk.id)
		nine("card" if i == sel_skin else "card_w", r, 46, 64, 46, 46)
		text_c(Vector2(r.get_center().x, r.position.y + 30), sk.name, 28, Color(1, 1, 1), 7)
		draw_candy(10 if owned else 1, r.get_center() + Vector2(0, 8), 46.0 if owned else 40.0, 0.0, 0.0, false, sk.id)
		var st = ""
		var scol = C("#9b7bff")
		if sk.id == equip:
			st = "EQUIPPED"; scol = C("#3fcf9f")
		elif owned:
			st = "OWNED"
		elif sk.how == "boss":
			st = "BOSS " + lvl_name(sk.boss - 1); scol = C("#ff4d6d")
		elif sk.how == "stars":
			st = "%d STARS W%d" % [miles(sk.world)[miles(sk.world).size() - 1], sk.world]; scol = C("#e0a020")
		else:
			st = "%d coins" % sk.price; scol = C("#e0a020")
		text_c(Vector2(r.get_center().x, r.end.y - 34), st, 24, scol, 0)
	# selected skin: the whole merge chain, unknown items as silhouettes
	var sk2 = SKINS[sel_skin]
	nine("panel_b", Rect2(36, 700, 648, 420), 50, 50, 50, 50)
	text_c(Vector2(360, 742), sk2.name + "  ·  merge chain", 30, INK(), 0)
	for lv in range(1, 11):
		var col = (lv - 1) % 5
		var row = (lv - 1) / 5
		var sr = Rect2(66 + col * 120, 790 + row * 150, 108, 116)
		img("slot_sel" if lv == 10 else "slot", sr)
		var known = seen.has("%s:%d" % [sk2.id, lv]) or (sk2.id == "candy" and lv == 1) or lv == 1
		var c = sr.get_center() + Vector2(0, -8)
		if known:
			draw_candy(lv, c, 30.0, 0.0, 0.0, false, sk2.id)
		else:
			draw_circle(c, 30, C("#d8cce6"))
			text_c(c + Vector2(0, 2), "?", 40, C("#ffffff"), 6)
		text_c(Vector2(c.x, sr.end.y - 16), str(lv), 20, INK(), 0)
	var owned2 = skins.has(sk2.id)
	if sk2.id == equip:
		big_button(Rect2(190, 1150, 340, 90), "EQUIPPED", "#3fcf9f")
	elif owned2:
		big_button(Rect2(190, 1150, 340, 90), "EQUIP", "#3fcf9f")
	elif sk2.how == "shop":
		big_button(Rect2(190, 1150, 340, 90), "BUY  %d" % sk2.price, "#ff5fa2" if coins >= sk2.price else "#b3a7c4")
	elif sk2.how == "stars":
		big_button(Rect2(190, 1150, 340, 90), "ALL STARS W%d" % sk2.world, "#ff5fa2")
	else:
		big_button(Rect2(190, 1150, 340, 90), "BEAT BOSS " + lvl_name(sk2.boss - 1), "#ff5fa2")


func img_tex_path(path: String):
	if tex.has(path):
		return tex[path]
	var im = Image.load_from_file(ProjectSettings.globalize_path(path))
	var tt = ImageTexture.create_from_image(im) if im != null else null
	tex[path] = tt
	return tt

# ---------------------------------------------------------------- music + settings
func update_music() -> void:
	if sim or demo or show_map_only:
		return
	var want = "game2" if li % 2 == 1 else "game"
	if state in ["map"] or (state == "settings" and set_from == "map"):
		want = "map"
	elif state == "skins":
		want = "shop"
	elif boss != null and state == "play":
		want = "boss"
	if music_player == null:
		music_player = AudioStreamPlayer.new()
		add_child(music_player)
	if want != cur_track:
		cur_track = want
		var st = AudioStreamOggVorbis.load_from_file(ProjectSettings.globalize_path("res://music/%s.ogg" % want))
		if st != null:
			st.loop = true
			music_player.stream = st
			music_player.volume_db = -10.0
			music_player.play()
	music_player.stream_paused = (not mus_on) or (my_song_on and my_song_ok)
	drive_song()

func draw_gear(c: Vector2, r: float) -> void:
	var pts = PackedVector2Array()
	for k in range(32):
		var an = k * TAU / 32.0
		var rr2 = r if (k / 2) % 2 == 0 else r * 0.74
		pts.append(c + Vector2(cos(an), sin(an)) * rr2)
	var o = PackedVector2Array()
	for q in pts:
		o.append(c + (q - c) * 1.0 + (q - c).normalized() * 4.0)
	draw_colored_polygon(o, INK())
	draw_colored_polygon(pts, C("#9b7bff"))
	draw_circle(c, r * 0.36 + 3, INK())
	draw_circle(c, r * 0.36, C("#fff0f6"))

func set_rows() -> Array:
	return [["MUSIC", mus_on], ["SOUNDS", sfx_on], ["VIBRATION", vib_on], ["MY SONG", my_song_on]]

func settings_input(pos: Vector2) -> void:
	if Rect2(560, 330, 80, 80).has_point(pos):
		state = set_from
		save_game()
		return
	if Rect2(150, 1022, 420, 80).has_point(pos):
		pick_song()
		return
	for i in range(4):
		if Rect2(110, 470 + i * 130, 500, 110).has_point(pos):
			if i == 0:
				mus_on = not mus_on
			elif i == 1:
				sfx_on = not sfx_on
			elif i == 2:
				vib_on = not vib_on
				buzz(40)
			else:
				if not my_song_ok:
					pick_song()
				else:
					my_song_on = not my_song_on
			play("pop2", 1.3, -6.0)
			save_game()

func draw_settings() -> void:
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.55))
	nine("card", Rect2(70, 330, 580, 820), 46, 70, 46, 46)
	text_c(Vector2(360, 372), "SETTINGS", 44, Color(1, 1, 1), 9)
	img("close", Rect2(560, 330, 80, 80))
	var rows = set_rows()
	for i in range(4):
		var y = 470 + i * 130
		nine("bar_white", Rect2(110, y, 500, 104), 40, 40, 40, 40)
		text_l(Vector2(150, y + 50), rows[i][0], 40, C("#ff5fa2"), 0)
		img("check" if rows[i][1] else "uncheck", Rect2(500, y + 6, 88, 92))
	text_c(Vector2(360, 990), "Every bounce plays the next bit of your song", 22, C("#9b7bff"), 0)
	big_button(Rect2(150, 1022, 420, 80), "CHOOSE A SONG" if not my_song_ok else "CHANGE SONG", "#ff5fa2")
	text_c(Vector2(360, 1118), "Sugar Bounce  v0.1", 18, C("#9b7bff"), 0)


# ---------------------------------------------------------------- "my song": the player's own music, advanced by bounces
func pick_song() -> void:
	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		DisplayServer.file_dialog_show("Choose a song", "", "", false, DisplayServer.FILE_DIALOG_MODE_OPEN_FILE, PackedStringArray(["*.mp3, *.ogg ; Songs"]), _on_song_picked)
	else:
		banner = {"t": 0.0, "txt": "No file picker here", "col": "#ff4d6d", "big": false}

func _on_song_picked(status: bool, paths: PackedStringArray, _filter: int) -> void:
	if status and paths.size() > 0:
		import_song(paths[0])
		my_song_on = my_song_ok
		save_game()

func import_song(path: String) -> void:
	var ext = path.get_extension().to_lower()
	if ext not in ["mp3", "ogg"]:
		return
	for old in ["user://my_song.mp3", "user://my_song.ogg"]:
		if FileAccess.file_exists(old):
			DirAccess.remove_absolute(old)
	var src = FileAccess.open(path, FileAccess.READ)
	if src == null:
		return
	var dst = FileAccess.open("user://my_song." + ext, FileAccess.WRITE)
	dst.store_buffer(src.get_buffer(src.get_length()))
	dst.close()
	load_my_song()

func load_my_song() -> void:
	var st = null
	if FileAccess.file_exists("user://my_song.mp3"):
		var f = FileAccess.open("user://my_song.mp3", FileAccess.READ)
		st = AudioStreamMP3.new()
		st.data = f.get_buffer(f.get_length())
	elif FileAccess.file_exists("user://my_song.ogg"):
		st = AudioStreamOggVorbis.load_from_file(ProjectSettings.globalize_path("user://my_song.ogg"))
	if st == null:
		my_song_ok = false
		return
	st.loop = true
	if song_player == null:
		song_player = AudioStreamPlayer.new()
		add_child(song_player)
	song_player.stream = st
	song_player.volume_db = -4.0
	song_player.play()
	song_player.stream_paused = true
	my_song_ok = true

func drive_song() -> void:
	if song_player == null or not my_song_ok:
		return
	var on = my_song_on and state == "play" and Time.get_ticks_msec() / 1000.0 < song_until
	song_player.stream_paused = not on


# ================================================================ WORLD 2 : SUGAR PLINKO
func step_plinko(dt: float) -> void:
	var pts: PackedVector2Array = shp.pts
	spout_x = move_toward(spout_x, spout_tx, 900.0 * dt)
	for pg in pegs:
		if pg.mv:
			pg.p.x = pg.bx + sin(t * 1.6 + pg.row) * 30.0
	if L.get("jackpot", false):
		jack_t -= dt
		if jack_t <= 0.0:
			jack_t = 6.0
			for bk in buckets:
				bk.m = bk.base
			jack_i = rng.randi() % buckets.size()
			buckets[jack_i].m = 20.0
			buckets[jack_i].f = 1.0
			if not sim:
				play("swipe", 1.4, -12.0)
	# drop the next queued candy
	drop_t -= dt
	if drop_t <= 0.0 and ending < 0:
		for b in balls:
			if b.q and b.mg == null:
				b.q = false
				b.p = Vector2(spout_x + rng.randf_range(-6, 6), 262.0)
				b.v = Vector2(rng.randf_range(-40, 40), 120.0)
				b.tr.clear()
				drop_t = 0.32
				break
		if drop_t <= 0.0:
			drop_t = 0.1
	var dead = []
	for b in balls:
		b.rot += b.v.x * dt * 0.01
		if b.mg != null:
			b.mg.t += dt
			var k = minf(1.0, b.mg.t / 0.3)
			b.p = b.mg.from.lerp(b.mg.to, k * k)
			if k >= 1.0:
				dead.append(b)
			continue
		if b.q:
			continue
		if b.lift >= 0.0:
			b.lift += dt
			if b.lift >= 0.85:
				b.lift = -1.0
				b.q = true
			continue
		b.cd -= dt
		b.v.y += G * 0.75 * grav() * dt
		b.p += b.v * dt
		var r: float = b.r
		# walls (the board tube)
		for i in range(pts.size() - 1):
			var a = pts[i]
			if absf(a.x - b.p.x) > 70.0 or absf(a.y - b.p.y) > 70.0:
				continue
			var ab = pts[i + 1] - a
			var u = clampf((b.p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
			var q = a + ab * u
			var d = b.p.distance_to(q)
			if d < TR + r and d > 0.001:
				var n: Vector2 = (b.p - q) / d
				b.p = q + n * (TR + r)
				var vn: float = b.v.dot(n)
				if vn < 0.0:
					b.v -= n * vn * 1.5
		# sugar pegs
		for pg in pegs:
			var dd = b.p.distance_to(pg.p)
			var mm = r + 10.0
			if dd < mm and dd > 0.001:
				var n2: Vector2 = (b.p - pg.p) / dd
				b.p = pg.p + n2 * mm
				var vn2: float = b.v.dot(n2)
				if vn2 < 0.0:
					b.v -= n2 * vn2 * 1.55
					b.v.x += rng.randf_range(-60, 60)
					b.sq = 1.0
					pg.f = 1.0
					if b.cd <= 0.0:
						b.cd = 0.04
						var small = val(b.lv) * 0.25 * (3.0 if pg.gold else 1.0)
						money += small; earned += small
						hist.append([t, small])
						if not sim:
							floats.append({"p": pg.p + Vector2(0, -18), "txt": "+$" + fmt(small), "col": "#ffd36b" if pg.gold else "#ffffff", "t": 0.0, "big": false})
						snd_bounce(12 - pg.row * 2 + rng.randi() % 2)
		# bumpers: big candy bumpers that kick hard and charge the candy (x2 in the bucket)
		for bm in bumpers:
			var db = b.p.distance_to(bm.p)
			var mb = r + 28.0
			if db < mb and db > 0.001:
				var nb3: Vector2 = (b.p - bm.p) / db
				b.p = bm.p + nb3 * mb
				b.v = nb3 * 760.0 + Vector2(0, -120)
				bm.f = 1.0
				b.charged = true
				b.sq = 1.0
				if b.cd <= 0.0:
					b.cd = 0.05
					play("pad", 1.4, -12.0)
		if boss != null and boss.hp > 0:
			hit_box(b, boss, boss.w, boss.h, true)
		# landing in a bucket
		if b.p.y > BUCKET_Y:
			var bi = clampi(int((b.p.x - 166.0) / ((630.0 - 166.0) / buckets.size())), 0, buckets.size() - 1)
			var bk = buckets[bi]
			var v = val(b.lv) * bk.m * boost_mult() * (10.0 if b.gold else 1.0) * (2.0 if b.get("charged", false) else 1.0)
			b.charged = false
			money += v; earned += v
			hist.append([t, v])
			bk.f = 1.0
			if not sim:
				floats.append({"p": Vector2((bk.x0 + bk.x1) / 2.0, BUCKET_Y - 30), "txt": "+$" + fmt(v), "col": "#5cff4a" if bk.m >= 8 else "#ffffff", "t": 0.0, "big": bk.m >= 8})
				burst(Vector2((bk.x0 + bk.x1) / 2.0, BUCKET_Y + 20), C("#ffd36b" if bk.m >= 8 else "#ffffff", 1.6), 14 if bk.m >= 8 else 6, 260.0, 3.5, 0.5)
			if bk.m <= 0.0:
				if not sim:
					floats[floats.size() - 1].txt = "SOUR!"
					floats[floats.size() - 1].col = "#ff4d6d"
				play("fail", 1.3, -14.0)
			elif bk.m >= 8:
				play("cash", 1.2, -10.0)
				shake = maxf(shake, 3.0)
			else:
				play("pop4", 0.8 + bk.m * 0.08, -9.0)
			b.lift = 0.0
			b.liftfrom = b.p
		b.sq = maxf(0.0, b.sq - dt * 7.0)
	for b in dead:
		balls.erase(b)
	if dead.size() >= 2:
		var lv: int = dead[0].lv + 1
		var p: Vector2 = dead[0].mg.to
		balls.append({"p": p, "v": Vector2.ZERO, "lv": lv, "r": rad(lv), "tr": [], "cd": 0.0, "sq": 1.0, "mg": null, "rot": 0.0, "gold": false, "q": true, "lift": -1.0})
		var c = C(obj_col(lv), 1.8)
		ring(p, c, 60.0 + lv * 10.0)
		burst(p, c, 18 + lv * 4, 320.0, 4.0, 0.55)
		snd_merge(lv)
		var sk_key = "%s:%d" % [equip, lv]
		if not seen.has(sk_key):
			seen[sk_key] = true
			popup = {"t": 0.0, "kind": "candy", "lv": lv}
			state = "newcandy"
			play("drop", 1.0, -4.0)
			save_game()
	for pg in pegs:
		pg.f = maxf(0.0, pg.f - dt * 5.0)
	for bm in bumpers:
		bm.f = maxf(0.0, bm.f - dt * 4.0)
	for bk in buckets:
		bk.f = maxf(0.0, bk.f - dt * 3.0)

func lift_pos(b: Dictionary) -> Vector2:
	# candies ride a little elevator on the right side back up to the dispenser
	var k = clampf(b.lift / 0.85, 0.0, 1.0)
	var a: Vector2 = b.get("liftfrom", Vector2(560, 960))
	var p1 = Vector2(690, 980)
	var p2 = Vector2(690, 230)
	var p3 = Vector2(spout_x, 230)
	if k < 0.2:
		return a.lerp(p1, k / 0.2)
	if k < 0.8:
		return p1.lerp(p2, (k - 0.2) / 0.6)
	return p2.lerp(p3, (k - 0.8) / 0.2)

func draw_plinko() -> void:
	# elevator rail
	draw_line(Vector2(690, 980), Vector2(690, 230), INK(), 22.0)
	draw_line(Vector2(690, 980), Vector2(690, 230), C("#fff1d6"), 14.0)
	for k in range(14):
		var y = 980.0 - fmod(t * 160.0 + k * 54.0, 750.0)
		draw_line(Vector2(683, y), Vector2(697, y), C("#ffb3d6"), 4.0)
	# pegs
	for pg in pegs:
		var f: float = pg.f
		var col = C("#ffd36b", 1.0 + f) if pg.gold else C("#7df0c8", 1.0 + f * 1.2)
		draw_circle(pg.p, 13.0 + f * 3.0, INK())
		draw_circle(pg.p, 10.0 + f * 3.0, col)
		draw_circle(pg.p + Vector2(-3, -3), 3.5, Color(1, 1, 1, 0.8))
	# buckets
	for i in range(buckets.size()):
		var bk = buckets[i]
		var x0: float = bk.x0
		var x1: float = bk.x1
		var hot = bk.m >= 8.0
		var base = C("#ff5fa2") if hot else (C("#9b7bff") if bk.m >= 3.0 else C("#8fd8ff"))
		if bk.m <= 0.0:
			base = C("#8bd63a")
		if bk.m >= 20.0:
			base = C("#ffd36b", 1.0 + 0.4 * sin(t * 10.0))
		rrect(Rect2(x0 + 4, BUCKET_Y + 6, x1 - x0 - 8, 56), base.lightened(bk.f * 0.6), 10)
		var lbl = "SOUR" if bk.m <= 0.0 else "x" + (fmt(bk.m * boost_mult()) if bk.m * boost_mult() >= 10 else ("%.1f" % (bk.m * boost_mult())).trim_suffix(".0"))
		text_c(Vector2((x0 + x1) / 2.0, BUCKET_Y + 34), lbl, 20 if bk.m <= 0.0 else 24, Color(1, 1, 1), 6)
		if i > 0:
			draw_line(Vector2(x0, BUCKET_Y - 4), Vector2(x0, BUCKET_Y + 62), INK(), 10.0)
			draw_line(Vector2(x0, BUCKET_Y - 4), Vector2(x0, BUCKET_Y + 62), C("#fff1d6"), 5.0)
	for bm in bumpers:
		var f: float = bm.f
		draw_circle(bm.p, 32.0 + f * 5.0, INK())
		draw_circle(bm.p, 28.0 + f * 5.0, C("#ff5fa2", 1.0 + f))
		draw_circle(bm.p, 18.0, C("#ffd36b"))
		draw_circle(bm.p + Vector2(-8, -9), 6.0, Color(1, 1, 1, 0.8))
		text_c(bm.p + Vector2(0, 2), "x2", 18, Color(1, 1, 1), 5)
	# dispenser that follows your aim + queued candies
	var sx = spout_x
	draw_colored_polygon(PackedVector2Array([Vector2(sx - 44, 196), Vector2(sx + 44, 196), Vector2(sx + 24, 252), Vector2(sx - 24, 252)]), INK())
	draw_colored_polygon(PackedVector2Array([Vector2(sx - 38, 200), Vector2(sx + 38, 200), Vector2(sx + 20, 246), Vector2(sx - 20, 246)]), C("#ffb3d6"))
	draw_line(Vector2(sx - 30, 210), Vector2(sx + 28, 236), C("#ffffff", 1.0, 0.6), 6.0)
	if state == "play" and ending < 0:
		for k in range(8):
			draw_circle(Vector2(sx, 280 + k * 22), 3.0, C("#ffffff", 1.0, 0.5 - k * 0.05))
	var qn = 0
	for b in balls:
		if b.q and b.mg == null:
			qn += 1
	if qn > 0:
		text_c(Vector2(sx, 176), "x%d" % qn, 22, Color(1, 1, 1), 6)
	for b in balls:
		if b.lift >= 0.0:
			draw_candy(b.lv, lift_pos(b), b.r * 0.8, 0.0, b.rot, b.gold)


# ================================================================ WORLD 3 : FLIPPER FAIR
func add_fbump(k: int, quiet = false) -> void:
	if k >= FB_SLOTS.size():
		return
	var p: Vector2 = FB_SLOTS[k]
	fbumps.append({"p": p, "bx": p.x, "f": 0.0, "super": false, "r": 36.0})
	if not quiet:
		burst(p, C("#ff9a2e", 1.6), 20, 300.0, 4.0, 0.5)
		ring(p, C("#ffd36b", 1.5), 80.0)

func flip_tip(i: int, a: float) -> Vector2:
	var d = Vector2(cos(a), sin(a)) if i == 0 else Vector2(-cos(a), sin(a))
	return FL_PIV[i] + d * FL_LEN

func step_flipper(dt: float) -> void:
	var pts: PackedVector2Array = shp.pts
	# flippers
	for i in range(2):
		var f = flips[i]
		if autoplay:
			# bot: short taps when a candy is about to reach the flipper
			f.t -= dt
			if f.t > 0.18:
				f.hold = true
			else:
				f.hold = false
				if f.t <= 0.0:
					for b in balls:
						if not hidden_ball(b) and b.mg == null and b.p.y > 850.0 and absf(b.p.x - (FL_PIV[i].x + (45.0 if i == 0 else -45.0))) < 70.0:
							f.t = 0.45 + rng.randf() * 0.1
							break
		f.pa = f.a
		var goal = FL_UP if f.hold else FL_DOWN
		f.a = move_toward(f.a, goal, (22.0 if f.hold else 9.0) * dt)
	for fb in fbumps:
		fb.f = maxf(0.0, fb.f - dt * 5.0)
		if L.get("movefb", false):
			fb.p.x = fb.bx + sin(t * 1.3 + fb.bx) * 40.0
	for tg in ftargets:
		tg.f = maxf(0.0, tg.f - dt * 4.0)
	tbonus = maxf(0.0, tbonus - dt)
	# launch queued / drained candies from the top
	drop_t -= dt
	if drop_t <= 0.0 and ending < 0:
		for b in balls:
			if b.q and b.mg == null and b.get("wait", 0.0) <= 0.0:
				b.q = false
				b.p = Vector2(360 + rng.randf_range(-30, 30), 270.0)
				b.v = Vector2(rng.randf_range(-260, 260), 80.0)
				b.tr.clear()
				drop_t = 0.4
				break
		if drop_t <= 0.0:
			drop_t = 0.1
	var dead = []
	for b in balls:
		b.rot += b.v.x * dt * 0.01
		if b.mg != null:
			b.mg.t += dt
			var k = minf(1.0, b.mg.t / 0.3)
			b.p = b.mg.from.lerp(b.mg.to, k * k)
			if k >= 1.0:
				dead.append(b)
			continue
		if b.q:
			if b.get("wait", 0.0) > 0.0:
				b.wait -= dt
			continue
		b.cd -= dt
		b.v.y += G * 0.8 * grav() * dt
		b.p += b.v * dt
		var r: float = b.r
		# table walls
		for i in range(pts.size() - 1):
			var a = pts[i]
			if absf(a.x - b.p.x) > 70.0 or absf(a.y - b.p.y) > 70.0:
				continue
			var ab = pts[i + 1] - a
			var u = clampf((b.p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
			var q = a + ab * u
			var d = b.p.distance_to(q)
			if d < TR + r and d > 0.001:
				var n: Vector2 = (b.p - q) / d
				b.p = q + n * (TR + r)
				var vn: float = b.v.dot(n)
				if vn < 0.0:
					b.v -= n * vn * 1.55
		# flippers (moving capsules)
		for i in range(2):
			var f = flips[i]
			var piv: Vector2 = FL_PIV[i]
			var tip = flip_tip(i, f.a)
			var ab2 = tip - piv
			var u2 = clampf((b.p - piv).dot(ab2) / ab2.length_squared(), 0.0, 1.0)
			var q2 = piv + ab2 * u2
			var d2 = b.p.distance_to(q2)
			if d2 < r + 13.0 and d2 > 0.001:
				var n2: Vector2 = (b.p - q2) / d2
				b.p = q2 + n2 * (r + 13.0)
				var qprev = piv + (flip_tip(i, f.pa) - piv) * u2
				var vf = (q2 - qprev) / maxf(dt, 0.0001)
				var rel = b.v - vf
				var vn2 = rel.dot(n2)
				if vn2 < 0.0:
					b.v -= n2 * vn2 * 1.45
					b.v += vf * 0.85 * clampf(u2 + 0.3, 0.0, 1.0)
					if vf.length() > 200.0 and b.cd <= 0.0:
						b.cd = 0.05
						b.sq = 1.0
						play("pad", 1.6, -12.0)
		# slingshots (the rails above each flipper kick the candy back up)
		for i in range(2):
			var sx = -1.0 if i == 0 else 1.0
			var a3: Vector2 = FL_PIV[i] + Vector2(sx * 70, -120)
			var b3: Vector2 = FL_PIV[i] + Vector2(sx * 14, -18)
			var ab3 = b3 - a3
			var u3 = clampf((b.p - a3).dot(ab3) / ab3.length_squared(), 0.0, 1.0)
			var q3 = a3 + ab3 * u3
			var d3 = b.p.distance_to(q3)
			if d3 < r + 8.0 and d3 > 0.001:
				var n5: Vector2 = (b.p - q3) / d3
				b.p = q3 + n5 * (r + 8.0)
				if b.v.dot(n5) < 0.0:
					b.v = n5 * 620.0 + Vector2(0, -260)
					b.sq = 1.0
					if b.cd <= 0.0:
						b.cd = 0.05
						flip_earn(val(b.lv) * 0.5, q3 + Vector2(0, -24), false)
						play("pad", 1.3, -12.0)
		# bumpers
		for fb in fbumps:
			var db = b.p.distance_to(fb.p)
			var mb = r + fb.r
			if db < mb and db > 0.001:
				var n3: Vector2 = (b.p - fb.p) / db
				b.p = fb.p + n3 * mb
				b.v = n3 * 820.0
				fb.f = 1.0
				b.sq = 1.0
				if b.cd <= 0.0:
					b.cd = 0.04
					var v = val(b.lv) * (3.0 if fb.super else 1.0) * (2.0 if tbonus > 0.0 else 1.0) * (10.0 if b.gold else 1.0)
					flip_earn(v, fb.p + Vector2(0, -36), fb.super)
					snd_bounce(int(fb.p.y / 60.0) % 12)
		# drop targets
		for tg in ftargets:
			if tg.down:
				continue
			var tq = Vector2(clampf(b.p.x, tg.p.x - 20, tg.p.x + 20), clampf(b.p.y, tg.p.y - 10, tg.p.y + 10))
			var dt2 = b.p.distance_to(tq)
			if dt2 < r and dt2 > 0.001:
				var n4: Vector2 = (b.p - tq) / dt2
				b.p = tq + n4 * r
				b.v -= n4 * b.v.dot(n4) * 1.6
				tg.down = true
				tg.f = 1.0
				flip_earn(val(b.lv) * 3.0, tg.p + Vector2(0, -24), false)
				play("match2", 1.3, -8.0)
				var all_down = true
				for t2 in ftargets:
					if not t2.down:
						all_down = false
				if all_down:
					tbonus = 10.0
					banner = {"t": 0.0, "txt": "BONUS x2!", "col": "#ffd36b", "big": false}
					play("clear", 1.3, -6.0)
					for t2 in ftargets:
						t2.down = false
		if boss != null and boss.hp > 0:
			hit_box(b, boss, boss.w, boss.h, true)
		# drain: the candy is lost for 1.5 s
		if b.p.y > 1040.0 or b.p.x < 60.0 or b.p.x > 660.0:
			b.q = true
			b.wait = 1.5
			if not sim:
				floats.append({"p": Vector2(360, 1000), "txt": "DRAIN!", "col": "#ff4d6d", "t": 0.0, "big": false})
			play("fail", 1.6, -16.0)
		b.sq = maxf(0.0, b.sq - dt * 7.0)
	for b in dead:
		balls.erase(b)
	if dead.size() >= 2:
		var lv: int = dead[0].lv + 1
		var p: Vector2 = dead[0].mg.to
		balls.append({"p": p, "v": Vector2(rng.randf_range(-200, 200), 60), "lv": lv, "r": rad(lv), "tr": [], "cd": 0.0, "sq": 1.0, "mg": null, "rot": 0.0, "gold": false, "q": false, "lift": -1.0})
		var c = C(obj_col(lv), 1.8)
		ring(p, c, 60.0 + lv * 10.0)
		burst(p, c, 18 + lv * 4, 320.0, 4.0, 0.55)
		snd_merge(lv)
		var sk_key = "%s:%d" % [equip, lv]
		if not seen.has(sk_key):
			seen[sk_key] = true
			popup = {"t": 0.0, "kind": "candy", "lv": lv}
			state = "newcandy"
			play("drop", 1.0, -4.0)
			save_game()

func flip_earn(v: float, at: Vector2, hot: bool) -> void:
	money += v; earned += v
	hist.append([t, v])
	if not sim:
		floats.append({"p": at, "txt": "+$" + fmt(v), "col": "#ffd36b" if hot or tbonus > 0.0 else "#ffffff", "t": 0.0, "big": hot})
		if floats.size() > 40:
			floats.pop_front()

func draw_flipper() -> void:
	# lane guides above the flippers
	for i in range(2):
		var piv: Vector2 = FL_PIV[i]
		var sx = -1.0 if i == 0 else 1.0
		draw_line(piv + Vector2(sx * 14, -18), piv + Vector2(sx * 70, -120), INK(), 22.0, true)
		draw_line(piv + Vector2(sx * 14, -18), piv + Vector2(sx * 70, -120), C("#ff9a2e"), 12.0, true)
		draw_line(piv + Vector2(sx * 14, -22), piv + Vector2(sx * 70, -124), Color(1, 1, 1, 0.5), 4.0, true)
	# drop targets
	for tg in ftargets:
		var rr = Rect2(tg.p - Vector2(20, 10), Vector2(40, 20))
		if tg.down:
			rrect(rr, C(INKH, 1.0, 0.25), 6)
		else:
			rrect(rr.grow(4), INK(), 9)
			rrect(rr, C("#ffd36b" if tbonus > 0.0 else "#ff5fa2", 1.0 + tg.f), 6)
			rrect(Rect2(rr.position + Vector2(4, 3), Vector2(32, 5)), Color(1, 1, 1, 0.6), 3)
	if tbonus > 0.0:
		text_c(Vector2(360, 300), "BONUS x2  %ds" % int(ceil(tbonus)), 22, C("#ffd36b"), 5)
	# bumpers
	for fb in fbumps:
		var f: float = fb.f
		var r: float = fb.r + f * 6.0
		draw_circle(fb.p + Vector2(0, 6), r + 4, C(INKH, 1.0, 0.25))
		draw_circle(fb.p, r + 4, INK())
		draw_circle(fb.p, r, C("#ffd36b" if fb.super else "#ff9a2e", 1.0 + f))
		draw_circle(fb.p, r * 0.62, C("#fff1d6"))
		draw_circle(fb.p, r * 0.36, C("#ff5fa2" if not fb.super else "#ff9a2e"))
		draw_circle(fb.p + Vector2(-r * 0.35, -r * 0.4), r * 0.18, Color(1, 1, 1, 0.8))
		if fb.super:
			text_c(fb.p + Vector2(0, 1), "x3", 18, Color(1, 1, 1), 5)
	# flippers
	for i in range(2):
		var f = flips[i]
		var piv: Vector2 = FL_PIV[i]
		var tip = flip_tip(i, f.a)
		draw_line(piv, tip, INK(), 32.0, true)
		draw_circle(piv, 16, INK())
		draw_circle(tip, 16, INK())
		draw_line(piv, tip, C("#ff5fa2"), 22.0, true)
		draw_circle(piv, 11, C("#ff5fa2"))
		draw_circle(tip, 11, C("#ff5fa2"))
		draw_line(piv + Vector2(0, -5), tip + Vector2(0, -5), Color(1, 1, 1, 0.45), 5.0, true)
		draw_circle(piv, 6, C("#ffd36b"))
	# launcher at the top
	var qn = 0
	for b in balls:
		if b.q and b.mg == null:
			qn += 1
	draw_circle(Vector2(360, 262), 22, INK())
	draw_circle(Vector2(360, 262), 17, C("#9b7bff"))
	if qn > 0:
		text_c(Vector2(360, 263), "x%d" % qn, 18, Color(1, 1, 1), 5)


# ================================================================ WORLD 4 : PORTAL POPS
func draw_portals() -> void:
	var pcols = [["#4fa3ff", "#ff9a2e"], ["#9b4dff", "#3fcf5f"]]
	for k in range(portals.size()):
		var po = portals[k]
		var gold = L.get("gold_portal", false) and k == 0
		for side in [0, 1]:
			var p: Vector2 = po.a if side == 0 else po.b
			var col = "#ffd36b" if gold else pcols[k % 2][side]
			draw_circle(p, 38.0, INK())
			draw_circle(p, 34.0, C(col, 1.0 + po.f))
			draw_circle(p, 26.0, C("#1a0b2e"))
			for j in range(3):
				var a0 = t * (3.0 if side == 0 else -3.0) + j * TAU / 3.0
				draw_arc(p, 8.0 + j * 6.0, a0, a0 + 2.2, 12, C(col, 1.6, 0.9), 3.0, true)
			if side == 0:
				text_c(p + Vector2(0, -50), "x4" if gold else "x2", 20, C(col), 5)


# ================================================================ WORLD 5 : COSMIC CANDY (zero gravity, planets)
func add_moon(quiet = false) -> void:
	if planets.size() == 0:
		return
	var k = moons.size()
	var pl = planets[k % planets.size()]
	moons.append({"pl": k % planets.size(), "rad": 120.0 + (k / planets.size()) * 45.0, "a": k * 2.1, "w": 0.6 + (k % 3) * 0.2, "p": Vector2.ZERO, "f": 0.0})
	if not quiet:
		ring(pl.p, C("#ffd36b", 1.5), 160.0)

func step_space(dt: float) -> void:
	var pts: PackedVector2Array = shp.pts
	for k in range(planets.size()):
		var pl = planets[k]
		pl.f = maxf(0.0, pl.f - dt * 5.0)
		if L.get("movplanet", false):
			pl.p = pl.b + Vector2(sin(t * 0.6) * 90.0, cos(t * 0.45) * 40.0)
	for mo in moons:
		mo.a += mo.w * dt
		mo.p = planets[mo.pl].p + Vector2(cos(mo.a), sin(mo.a)) * mo.rad
		mo.f = maxf(0.0, mo.f - dt * 5.0)
	if hole != null:
		hole.f += dt
	if L.get("comets", false):
		comet_t -= dt
		if comet == null and comet_t <= 0.0:
			var y0 = rng.randf_range(420, 860)
			comet = {"p": Vector2(40, y0), "v": Vector2(260, rng.randf_range(-60, 60))}
			play("swipe", 1.6, -10.0)
		if comet != null:
			comet.p += comet.v * dt
			if comet.p.x > 700:
				comet = null
				comet_t = rng.randf_range(7.0, 11.0)
	var dead = []
	for b in balls:
		b.rot += dt * 2.0
		if b.mg != null:
			b.mg.t += dt
			var k = minf(1.0, b.mg.t / 0.3)
			b.p = b.mg.from.lerp(b.mg.to, k * k)
			if k >= 1.0:
				dead.append(b)
			continue
		if b.get("wait", 0.0) > 0.0:
			b.wait -= dt
			if b.wait <= 0.0:
				b.p = Vector2(200, 430)
				b.v = Vector2(120.0, 0)
				b.tr.clear()
			continue
		b.cd -= dt
		var r: float = b.r
		# planet gravity (+ a little orbital drag so candies keep falling back onto the planet)
		var nearest = null
		var nd = 1e9
		for pl in planets:
			var d = pl.p - b.p
			var dist = maxf(d.length(), 60.0)
			b.v += d.normalized() * (5200000.0 / (dist * dist)) * dt
			if d.length() < nd:
				nd = d.length(); nearest = pl
		if nearest != null:
			var rn = (nearest.p - b.p).normalized()
			var vt = b.v - rn * b.v.dot(rn)
			b.v -= vt * minf(1.0, 0.9 * dt)
		if hole != null:
			var dh = hole.p - b.p
			var disth = maxf(dh.length(), 40.0)
			b.v += dh.normalized() * (3000000.0 / (disth * disth)) * dt
			if dh.length() < 26.0:
				b.wait = 1.5
				b.p = Vector2(-500, -500)
				if not sim:
					floats.append({"p": hole.p + Vector2(0, -40), "txt": "SUCKED IN!", "col": "#c06bff", "t": 0.0, "big": false})
				play("fail", 1.2, -14.0)
				continue
		var sp = b.v.length()
		if sp > 900.0:
			b.v *= 900.0 / sp
		b.p += b.v * dt
		# arena wall (no money, keeps energy)
		for i in range(pts.size() - 1):
			var a = pts[i]
			if absf(a.x - b.p.x) > 70.0 or absf(a.y - b.p.y) > 70.0:
				continue
			var ab = pts[i + 1] - a
			var u = clampf((b.p - a).dot(ab) / ab.length_squared(), 0.0, 1.0)
			var q = a + ab * u
			var dd = b.p.distance_to(q)
			if dd < TR + r and dd > 0.001:
				var n: Vector2 = (b.p - q) / dd
				b.p = q + n * (TR + r)
				var vn: float = b.v.dot(n)
				if vn < 0.0:
					b.v -= n * vn * 1.6
		# planets: bounce + money (like pads)
		for k in range(planets.size()):
			var pl = planets[k]
			var dp = b.p.distance_to(pl.p)
			var mp = pl.r + r
			if dp < mp and dp > 0.001:
				var n2: Vector2 = (b.p - pl.p) / dp
				b.p = pl.p + n2 * mp
				var tg = Vector2(-n2.y, n2.x)
				b.v = n2 * 540.0 + tg * rng.randf_range(-90, 90)
				b.sq = 1.0
				pl.f = 1.0
				if b.cd <= 0.0:
					b.cd = 0.05
					earn(b, k, pl.p + n2 * (pl.r + 10.0))
		# moons: x2
		for mo in moons:
			var dm = b.p.distance_to(mo.p)
			if dm < 24.0 + r and dm > 0.001:
				var n3: Vector2 = (b.p - mo.p) / dm
				b.p = mo.p + n3 * (24.0 + r)
				b.v = n3 * 560.0
				mo.f = 1.0
				if b.cd <= 0.0:
					b.cd = 0.05
					b.pm = 2.0
					earn(b, 3, mo.p + Vector2(0, -30))
		if comet != null and b.p.distance_to(comet.p) < 30.0 + r:
			var v = val(b.lv) * 30.0
			money += v; earned += v
			hist.append([t, v])
			if not sim:
				floats.append({"p": comet.p + Vector2(0, -30), "txt": "COMET! +$" + fmt(v), "col": "#ffd36b", "t": 0.0, "big": true})
				burst(comet.p, C("#ffd36b", 2.0), 30, 360.0, 5.0, 0.7)
			play("cash", 1.3, -8.0)
			comet = null
			comet_t = rng.randf_range(8.0, 12.0)
		if boss != null and boss.hp > 0:
			hit_box(b, boss, boss.w, boss.h, true)
		b.sq = maxf(0.0, b.sq - dt * 7.0)
	for b in dead:
		balls.erase(b)
	if dead.size() >= 2:
		var lv: int = dead[0].lv + 1
		var p: Vector2 = dead[0].mg.to
		balls.append({"p": p, "v": Vector2(120, 0), "lv": lv, "r": rad(lv), "tr": [], "cd": 0.0, "sq": 1.0, "mg": null, "rot": 0.0, "gold": false, "q": false, "lift": -1.0})
		var c = C(obj_col(lv), 1.8)
		ring(p, c, 60.0 + lv * 10.0)
		burst(p, c, 18 + lv * 4, 320.0, 4.0, 0.55)
		snd_merge(lv)
		var sk_key = "%s:%d" % [equip, lv]
		if not seen.has(sk_key):
			seen[sk_key] = true
			popup = {"t": 0.0, "kind": "candy", "lv": lv}
			state = "newcandy"
			play("drop", 1.0, -4.0)
			save_game()

func draw_space_bg() -> void:
	# deep-space disc behind the play area with twinkling stars
	draw_circle(Vector2(360, 640), 330.0, C("#2a1650", 1.0, 0.92))
	var r2 = RandomNumberGenerator.new()
	r2.seed = 11
	for i in range(60):
		var a = r2.randf() * TAU
		var d = sqrt(r2.randf()) * 310.0
		var p = Vector2(360, 640) + Vector2(cos(a), sin(a)) * d
		var tw = 0.5 + 0.5 * sin(t * 2.0 + i)
		draw_circle(p, 1.5 + (i % 3), Color(1.4, 1.4, 1.6, 0.3 + 0.6 * tw))

func draw_space() -> void:
	if hole != null:
		for k in range(6):
			draw_arc(hole.p, 26.0 + k * 8.0, hole.f * 3.0 + k, hole.f * 3.0 + k + 4.0, 16, C("#c06bff", 1.6, 0.6 - k * 0.08), 4.0, true)
		draw_circle(hole.p, 24.0, C("#0b0614"))
	for k in range(planets.size()):
		var pl = planets[k]
		var r: float = pl.r + pl.f * 6.0
		var cols = [["#ff5fa2", "#ffd36b"], ["#7df0c8", "#9b7bff"]][k % 2]
		draw_arc(pl.p, r * 1.55, PI * 1.05, TAU * 0.98, 32, INK(), 12.0, true)
		draw_circle(pl.p, r + 5, INK())
		draw_circle(pl.p, r, C(cols[0], 1.0 + pl.f))
		for j in range(-2, 3):
			var yy = j * r * 0.32
			var hw = sqrt(maxf(0.0, r * r - yy * yy))
			draw_line(pl.p + Vector2(-hw * 0.95, yy), pl.p + Vector2(hw * 0.95, yy), C(cols[1], 1.0, 0.45), r * 0.12, true)
		draw_circle(pl.p + Vector2(-r * 0.35, -r * 0.38), r * 0.2, Color(1, 1, 1, 0.6))
		draw_arc(pl.p, r * 1.55, 0.02, PI * 0.95, 32, INK(), 12.0, true)
		draw_arc(pl.p, r * 1.55, 0.02, PI * 0.95, 32, C("#fff1d6"), 6.0, true)
	for mo in moons:
		var f: float = mo.f
		draw_circle(mo.p, 27.0 + f * 4.0, INK())
		draw_circle(mo.p, 23.0 + f * 4.0, C("#d9dbe6", 1.0 + f))
		draw_circle(mo.p + Vector2(-6, -4), 6.0, C("#b3b6c4"))
		draw_circle(mo.p + Vector2(7, 6), 4.0, C("#b3b6c4"))
		text_c(mo.p + Vector2(0, -36), "x2", 16, C("#ffd36b"), 4)
	if comet != null:
		for k in range(10):
			draw_circle(comet.p - comet.v.normalized() * k * 12.0, 16.0 - k * 1.3, C("#ffd36b", 1.6, 0.8 - k * 0.07))
		draw_circle(comet.p, 18.0, INK())
		draw_circle(comet.p, 15.0, C("#fff1d6", 1.5))


# ================================================================ star chests (rewards per world)
func world_range(w: int) -> Array:
	var a = (w - 1) * 10
	var n = 20 if w == 5 else 10
	return [a, mini(a + n, LEVELS.size())]

func world_stars(w: int) -> int:
	var rg = world_range(w)
	var n = 0
	for i in range(rg[0], rg[1]):
		n += best_stars.get(i, 0)
	return n

func miles(w: int) -> Array:
	return MILE20 if w == 5 else MILE10

func chest_reward(w: int, k: int) -> Dictionary:
	var last = miles(w).size() - 1
	if k == last:
		return {"kind": "skin", "id": "star%d" % w, "txt": "STAR SKIN"}
	if w == 5:
		return [{"kind": "coins", "n": 150, "txt": "150 COINS"}, {"kind": "gold", "txt": "GOLDEN CANDY BOOSTER"}, {"kind": "trail", "id": TRAILS[w - 1], "txt": "COMET TRAIL"}, {"kind": "time", "txt": "+15 s BOOSTER"}, {"kind": "coins", "n": 1000, "txt": "1000 COINS"}][k]
	return [{"kind": "coins", "n": 100, "txt": "100 COINS"}, {"kind": "gold", "txt": "GOLDEN CANDY BOOSTER"}, {"kind": "trail", "id": TRAILS[w - 1], "txt": TRAILS[w - 1].to_upper() + " TRAIL"}, {"kind": "coins_time", "n": 500, "txt": "500 COINS + 15 s BOOSTER"}][k]

func claim_chest(w: int, k: int) -> void:
	var key = "%d:%d" % [w, k]
	if claimed.has(key) or world_stars(w) < miles(w)[k]:
		return
	claimed[key] = true
	var rw = chest_reward(w, k)
	match rw.kind:
		"coins":
			coins += rw.n
		"gold":
			boost_gold += 1
		"time":
			boost_time += 1
		"coins_time":
			coins += rw.n
			boost_time += 1
		"trail":
			trail_style = rw.id
		"skin":
			skins[rw.id] = true
			equip = rw.id
	popup = {"t": 0.0, "kind": "chest", "rw": rw, "w": w}
	state = "chest"
	play("cash", 1.0, -4.0)
	buzz(40)
	save_game()

func chest_pos(w: int, k: int) -> Vector2:
	var m = miles(w)
	return Vector2(150 + 420.0 * float(m[k]) / m[m.size() - 1], 262)

func draw_star_bar(w: int) -> void:
	var m = miles(w)
	var total = m[m.size() - 1]
	var have = world_stars(w)
	var bar = Rect2(150, 250, 420, 24)
	rrect(bar.grow(5), INK(), 16)
	rrect(bar, C("#ffffff", 1.0, 0.7), 12)
	var k0 = clampf(float(have) / total, 0.0, 1.0)
	if k0 > 0.0:
		rrect(Rect2(bar.position, Vector2(maxf(24.0, bar.size.x * k0), bar.size.y)), C("#ffd36b"), 12)
	draw_star(Vector2(112, 262), 20.0, C("#ffd36b"))
	text_c(Vector2(112, 296), "%d/%d" % [have, total], 20, Color(1, 1, 1), 5)
	for k in range(m.size()):
		var p = chest_pos(w, k)
		var got = claimed.has("%d:%d" % [w, k])
		var ready = have >= m[k] and not got
		draw_chest(p + Vector2(0, -4), got, ready, k == m.size() - 1)
		text_c(p + Vector2(0, 38), str(m[k]), 18, Color(1, 1, 1), 5)

func draw_chest(p: Vector2, open: bool, ready: bool, big: bool) -> void:
	var s = 1.25 if big else 1.0
	if ready:
		for k in range(3):
			draw_circle(p, (30 + k * 8 + sin(t * 5.0) * 3.0) * s, C("#ffd36b", 1.4, 0.12))
	var bob = sin(t * 6.0) * 3.0 if ready else 0.0
	var r = Rect2(p + Vector2(-20, -8 + bob) * s, Vector2(40, 26) * s)
	rrect(r.grow(4), INK(), 8)
	rrect(r, C("#ff5fa2") if not open else C("#d6c8f0"), 6)
	draw_rect(Rect2(r.position + Vector2(r.size.x / 2 - 4 * s, 0), Vector2(8 * s, r.size.y)), C("#ffd36b") if not open else C("#ece4f8"))
	if open:
		draw_colored_polygon(PackedVector2Array([r.position + Vector2(-2, 0), r.position + Vector2(r.size.x + 2, 0), r.position + Vector2(r.size.x - 4, -14 * s), r.position + Vector2(4, -14 * s)]), INK())
	else:
		var lid = Rect2(r.position + Vector2(-2, -12 * s), Vector2(r.size.x + 4, 14 * s))
		rrect(lid.grow(3), INK(), 8)
		rrect(lid, C("#ff7ab8"), 7)
		draw_circle(Vector2(r.get_center().x, r.position.y + 1), 4 * s, C("#ffd36b"))

func draw_chest_popup() -> void:
	var k: float = popup.t
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.6 * minf(1.0, k / 0.2)))
	var sc = minf(1.0, k / 0.3)
	for i in range(12):
		var an = t * 0.6 + i * TAU / 12.0
		draw_line(Vector2(360, 600), Vector2(360, 600) + Vector2(cos(an), sin(an)) * 420.0 * sc, C("#ffd36b", 1.2, 0.14), 32.0)
	text_c(Vector2(360, 380), "STAR CHEST!", int(64 * (0.5 + 0.5 * sc)), C("#ffd36b"), 12)
	var rw = popup.rw
	match rw.kind:
		"skin":
			for j in range(5):
				draw_candy(1 + j * 2, Vector2(360 + (j - 2) * 120, 620 + absf(j - 2) * 30), (34.0 + (2 - absf(j - 2)) * 14.0) * sc, 0.0, 0.0, false, rw.id)
		"trail":
			var c0 = Vector2(360, 610)
			for j in range(14):
				var q = c0 + Vector2(-180 + j * 18, sin(j * 0.6 + t * 4.0) * 30)
				trail_dot(q, 1.0 - j / 14.0, 18.0, j, rw.id)
			draw_candy(2, c0 + Vector2(80, sin(14 * 0.6 + t * 4.0) * 30), 34.0)
		"gold":
			draw_candy(10, Vector2(360, 610), 90.0 * sc, 0.0, 0.0, false, "candy")
		"time":
			draw_clock(Vector2(360, 610), 84.0 * sc)
			text_c(Vector2(360, 720), "+15 s", int(48 * sc), Color(1, 1, 1), 9)
		_:
			draw_coin(Vector2(330, 630), 70.0 * sc)
			draw_coin(Vector2(400, 600), 70.0 * sc)
	text_c(Vector2(360, 800), rw.txt, 46, Color(1, 1, 1), 10)
	if k > 0.6:
		text_c(Vector2(360, 1000), "Tap to continue", 28, C("#ffffff", 1.0, 0.6 + 0.4 * sin(t * 4.0)), 6)

# cosmetic trails
func trail_dot(q: Vector2, a: float, w: float, i: int, style: String) -> void:
	match style:
		"rainbow":
			var hue = fmod(i * 0.08 + t * 0.5, 1.0)
			draw_circle(q, w * 0.5 * a, Color.from_hsv(hue, 0.55, 1.0, a * 0.8))
		"stars":
			if i % 2 == 0:
				draw_star(q, w * 0.45 * a + 2.0, C("#ffd36b", 1.4, a))
		"hearts":
			if i % 2 == 0:
				var hs = w * 0.3 * a + 2.0
				draw_circle(q + Vector2(-hs * 0.5, 0), hs * 0.6, C("#ff5fa2", 1.0, a))
				draw_circle(q + Vector2(hs * 0.5, 0), hs * 0.6, C("#ff5fa2", 1.0, a))
				draw_colored_polygon(PackedVector2Array([q + Vector2(-hs * 1.05, hs * 0.2), q + Vector2(hs * 1.05, hs * 0.2), q + Vector2(0, hs * 1.3)]), C("#ff5fa2", 1.0, a))
		"bubbles":
			if i % 2 == 0:
				draw_arc(q, w * 0.35 * a + 2.0, 0, TAU, 12, C("#8fd8ff", 1.3, a), 2.0, true)
		"comet":
			draw_circle(q, w * 0.55 * a, C("#ff9a2e", 1.8, a * 0.7))
			draw_circle(q, w * 0.25 * a, C("#fff1d6", 1.8, a))


# ================================================================ daily gift (cozy: the streak never resets, it just waits)
const DAILY = [
	{"kind": "coins", "n": 50, "txt": "50"},
	{"kind": "coins", "n": 80, "txt": "80"},
	{"kind": "gold", "txt": "GOLD"},
	{"kind": "coins", "n": 120, "txt": "120"},
	{"kind": "time", "txt": "+15s"},
	{"kind": "coins", "n": 200, "txt": "200"},
	{"kind": "big", "n": 400, "txt": "400+"},
]

func claim_daily() -> void:
	var d = DAILY[gift_day % 7]
	match d.kind:
		"coins":
			coins += d.n
		"gold":
			boost_gold += 1
		"time":
			boost_time += 1
		"big":
			coins += d.n
			boost_gold += 1
	gift_day += 1
	gift_date = Time.get_date_string_from_system()
	play("cash", 1.0, -4.0)
	buzz(40)
	confetti()
	save_game()
	popup = null
	state = "play"

func draw_daily() -> void:
	var k: float = popup.t if popup != null else 1.0
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.45))
	var sc = minf(1.0, k / 0.3)
	nine("card", Rect2(50, 300, 620, 800).grow(10 * sc), 46, 70, 46, 46)
	text_c(Vector2(360, 344), "DAILY GIFT", 44, Color(1, 1, 1), 9)
	text_c(Vector2(360, 420), "Welcome back!", 34, C("#ff5fa2"), 0)
	var today = gift_day % 7
	for i in range(7):
		var col = i % 4
		var row = i / 4
		var w = 120.0
		var x0 = 360.0 - (2.0 if row == 0 else 1.5) * (w + 14.0) + col * (w + 14.0)
		var r = Rect2(x0, 470 + row * 210, w, 180)
		if i == 6:
			r = Rect2(x0, 470 + row * 210, w * 1.0, 180)
		var done = i < today
		var now = i == today
		if now:
			for j in range(3):
				rrect(r.grow(8 + j * 6 + sin(t * 5.0) * 2.0), C("#ffd36b", 1.3, 0.15), 22)
		img("slot_sel" if now else "slot", r)
		text_c(Vector2(r.get_center().x, r.position.y + 26), "DAY %d" % (i + 1), 20, C(INKH), 0)
		var d = DAILY[i]
		var c = r.get_center() + Vector2(0, 8)
		if d.kind in ["coins", "big"]:
			for j in range(3 if d.kind == "big" else 1):
				draw_coin(c + Vector2((j - (1 if d.kind == "big" else 0)) * 14, 6 - j * 10), 20.0)
		elif d.kind == "gold":
			draw_candy(10, c, 24.0, 0.0, 0.0, false, "candy")
		else:
			draw_clock(c, 22.0)
		text_c(Vector2(r.get_center().x, r.end.y - 26), d.txt, 22, Color(1, 1, 1), 5)
		if done:
			draw_rect(r, C("#ffffff", 1.0, 0.45))
			text_c(r.get_center(), "OK", 34, C("#3fcf9f"), 6)
	text_c(Vector2(360, 925), "Missed a day? No stress, your streak waits for you.", 22, C("#9b7bff"), 0)
	big_button(Rect2(190, 960, 340, 92), "CLAIM", "#ff5fa2")

# ================================================================ Candy Book: every object of every skin
func book_input(pos: Vector2) -> void:
	if Rect2(620, 40, 80, 80).has_point(pos):
		state = "skins"; play("swipe", 0.9, -6.0)
		return
	var pages = int(ceil(SKINS.size() / 5.0))
	if Rect2(36, 1150, 160, 70).has_point(pos):
		book_page = (book_page - 1 + pages) % pages; play("swipe", 1.2, -8.0)
	elif Rect2(524, 1150, 160, 70).has_point(pos):
		book_page = (book_page + 1) % pages; play("swipe", 1.2, -8.0)

func found(sk: Dictionary, lv: int) -> bool:
	if lv == 1 and skins.has(sk.id):
		return true
	return seen.has("%s:%d" % [sk.id, lv])

func draw_book() -> void:
	draw_rect(Rect2(0, 0, 720, 1280), C(INKH, 1.0, 0.35))
	text_c(Vector2(360, 82), "CANDY BOOK", 56, Color(1, 1, 1), 12)
	img("close", Rect2(620, 40, 80, 80))
	var total = 0
	var have = 0
	for sk in SKINS:
		for lv in range(1, 11):
			total += 1
			if found(sk, lv):
				have += 1
	var bar = Rect2(160, 140, 400, 30)
	rrect(bar.grow(5), INK(), 18)
	rrect(bar, C("#ffffff", 1.0, 0.7), 14)
	rrect(Rect2(bar.position, Vector2(maxf(30.0, bar.size.x * float(have) / total), bar.size.y)), C("#7df0c8"), 14)
	text_c(bar.get_center() + Vector2(0, 1), "%d / %d found" % [have, total], 22, Color(1, 1, 1), 6)
	var pages = int(ceil(SKINS.size() / 5.0))
	for row in range(5):
		var i = book_page * 5 + row
		if i >= SKINS.size():
			break
		var sk = SKINS[i]
		var y = 200 + row * 188
		nine("panel_b", Rect2(30, y, 660, 176), 50, 50, 50, 50)
		var n = 0
		for lv in range(1, 11):
			if found(sk, lv):
				n += 1
		draw_circle(Vector2(70, y + 36), 11, INK())
		draw_circle(Vector2(70, y + 36), 8, C(sk.col))
		text_l(Vector2(90, y + 34), sk.name, 28, C("#ff5fa2"), 0)
		text_l(Vector2(656, y + 34), "%d/10" % n, 24, C(INKH), 0, true)
		for lv in range(1, 11):
			var c = Vector2(84 + (lv - 1) * 61, y + 112)
			if found(sk, lv):
				draw_candy(lv, c, 22.0, 0.0, 0.0, false, sk.id)
			else:
				draw_circle(c, 22, C("#d8cce6"))
				text_c(c + Vector2(0, 2), "?", 26, Color(1, 1, 1), 4)
	big_button(Rect2(36, 1150, 160, 70), "<", "#ff5fa2")
	big_button(Rect2(524, 1150, 160, 70), ">", "#ff5fa2")
	text_c(Vector2(360, 1186), "%d / %d" % [book_page + 1, pages], 28, Color(1, 1, 1), 6)


# a proper coin: thick rim, inner ring, embossed star, shine
func draw_coin(p: Vector2, r: float) -> void:
	draw_circle(p + Vector2(0, r * 0.18), r + 2.5, INK())
	draw_circle(p + Vector2(0, r * 0.12), r, C("#c8820e"))
	draw_circle(p, r + 2.5, INK())
	draw_circle(p, r, C("#ffcf4a"))
	draw_circle(p, r * 0.74, C("#f2b230"))
	draw_arc(p, r * 0.74, 0, TAU, 28, C("#fff1a8"), maxf(1.5, r * 0.08), true)
	var pts = PackedVector2Array()
	for k in range(10):
		var an = -PI / 2 + k * PI / 5
		pts.append(p + Vector2(cos(an), sin(an)) * (r * 0.46 if k % 2 == 0 else r * 0.2))
	draw_colored_polygon(pts, C("#fff1a8"))
	ell(p + Vector2(-r * 0.38, -r * 0.42), r * 0.26, r * 0.12, Color(1, 1, 1, 0.75))


func draw_clock(p: Vector2, r: float) -> void:
	rrect(Rect2(p + Vector2(-r * 0.22, -r * 1.32), Vector2(r * 0.44, r * 0.34)), INK(), int(r * 0.12) + 1)
	rrect(Rect2(p + Vector2(-r * 0.15, -r * 1.26), Vector2(r * 0.3, r * 0.22)), C("#ff5fa2"), int(r * 0.1) + 1)
	draw_circle(p, r + 3, INK())
	draw_circle(p, r, C("#7df0c8"))
	draw_circle(p, r * 0.78, C("#ffffff"))
	draw_arc(p, r * 0.78, -PI / 2, -PI / 2 + TAU * 0.25, 16, C("#ffd36b"), r * 0.18, false)
	draw_line(p, p + Vector2(0, -r * 0.55), INK(), maxf(2.0, r * 0.1), true)
	draw_line(p, p + Vector2(r * 0.42, 0), INK(), maxf(2.0, r * 0.1), true)
	draw_circle(p, r * 0.1, INK())


# ================================================================ app icon (rendered in a 720x720 square: y 280..1000)
func face(p: Vector2, r: float) -> void:
	for sg in [-1, 1]:
		draw_circle(p + Vector2(sg * r * 0.34, -r * 0.08), r * 0.13, INK())
		draw_circle(p + Vector2(sg * r * 0.34 - r * 0.04, -r * 0.12), r * 0.045, Color(1, 1, 1))
		draw_circle(p + Vector2(sg * r * 0.52, r * 0.16), r * 0.1, C("#ff9fbf", 1.0, 0.8))
	draw_arc(p + Vector2(0, r * 0.12), r * 0.16, 0.2, PI - 0.2, 12, INK(), r * 0.07, true)

func radial_bg(sq: Rect2, c0: String, c1: String, key: String) -> void:
	if not tex.has(key):
		var gr = Gradient.new()
		gr.set_color(0, C(c0))
		gr.set_color(1, C(c1))
		var gt = GradientTexture2D.new()
		gt.gradient = gr
		gt.fill = GradientTexture2D.FILL_RADIAL
		gt.fill_from = Vector2(0.5, 0.45)
		gt.fill_to = Vector2(1.05, 1.05)
		gt.width = 256
		gt.height = 256
		tex[key] = gt
	draw_texture_rect(tex[key], sq, false)

# big glossy mascot: hard candy with a face; mood 0 = wow (open mouth), 1 = happy, 2 = cheeky wink
func draw_mascot(p: Vector2, r: float, mood: int, sq: float, base = "#ff3d6e") -> void:
	var sx = 1.0 + sq * 0.12
	var sy = 1.0 - sq * 0.12
	# shadow
	ell(p + Vector2(0, r * 1.02), r * 0.8, r * 0.16, C("#3a0a3a", 1.0, 0.35))
	draw_set_transform(p + base_off, 0.0, Vector2(sx, sy))
	var ink = INK()
	draw_circle(Vector2.ZERO, r + r * 0.07, ink)
	# body shading: dark edge -> base -> light center-top
	draw_circle(Vector2.ZERO, r, C(base, 0.62))
	draw_circle(Vector2(-r * 0.04, -r * 0.05), r * 0.93, C(base))
	draw_circle(Vector2(-r * 0.12, -r * 0.16), r * 0.72, C(base, 1.12))
	# candy swirl
	for k in range(3):
		var rr = r * (0.38 + k * 0.2)
		draw_arc(Vector2(r * 0.05, r * 0.05), rr, -1.9 + k * 0.6, 0.9 + k * 0.6, 24, Color(1, 1, 1, 0.55), r * 0.07, true)
	# rim light + big specular
	draw_arc(Vector2.ZERO, r * 0.9, 0.3, 1.6, 24, C("#ffb3c8", 1.2, 0.8), r * 0.06, true)
	ell(Vector2(-r * 0.42, -r * 0.5), r * 0.3, r * 0.17, Color(1, 1, 1, 0.92))
	draw_circle(Vector2(-r * 0.12, -r * 0.66), r * 0.06, Color(1, 1, 1, 0.9))
	# face
	for sg in [-1, 1]:
		var e = Vector2(sg * r * 0.33, -r * 0.02)
		var ey = r * (0.22 if mood == 0 else 0.19)
		if mood == 2 and sg == 1:
			draw_arc(e + Vector2(0, r * 0.04), r * 0.13, PI + 0.3, TAU - 0.3, 12, ink, r * 0.07, true)
		else:
			ell(e, r * 0.155, ey, ink)
			ell(e + Vector2(0, r * 0.02), r * 0.12, ey * 0.8, C("#2a1a4a"))
			draw_circle(e + Vector2(-r * 0.05, -ey * 0.4), r * 0.06, Color(1, 1, 1))
			draw_circle(e + Vector2(r * 0.05, ey * 0.25), r * 0.028, Color(1, 1, 1))
		# brows
		draw_line(e + Vector2(-r * 0.12, -r * 0.3 - (r * 0.04 if mood == 0 else 0.0)), e + Vector2(r * 0.12, -r * 0.33 - (r * 0.04 if mood == 0 else 0.0)), ink, r * 0.06, true)
		ell(Vector2(sg * r * 0.56, r * 0.24), r * 0.13, r * 0.08, C("#ff9fbf", 1.1, 0.85))
	if mood == 0:
		# open "wow" mouth with tongue
		ell(Vector2(0, r * 0.36), r * 0.2, r * 0.22, ink)
		ell(Vector2(0, r * 0.38), r * 0.16, r * 0.18, C("#5a0a2a"))
		ell(Vector2(0, r * 0.48), r * 0.11, r * 0.07, C("#ff7aa0"))
	else:
		var mouth = PackedVector2Array()
		for k in range(13):
			var a = lerpf(0.15, PI - 0.15, k / 12.0)
			mouth.append(Vector2(cos(a) * r * 0.24, r * 0.2 + sin(a) * r * 0.2))
		mouth.append(Vector2(r * 0.24, r * 0.2))
		draw_colored_polygon(mouth, ink)
		ell(Vector2(0, r * 0.34), r * 0.1, r * 0.05, C("#ff7aa0"))
	draw_set_transform(base_off)

func burst_rays(c: Vector2, n: int, len: float, col: Color, w: float, rot = 0.0) -> void:
	for k in range(n):
		var a0 = rot + k * TAU / n
		draw_colored_polygon(PackedVector2Array([c, c + Vector2(cos(a0 - w), sin(a0 - w)) * len, c + Vector2(cos(a0 + w), sin(a0 + w)) * len]), col)

func draw_icon_art(v: int) -> void:
	if v >= 3:
		draw_icon_art2(v)
		return
	var sq = Rect2(0, 280, 720, 720)
	var c = sq.get_center()
	if not tex.has("icon_bg"):
		var gr = Gradient.new()
		gr.set_color(0, C("#ffc2e2"))
		gr.set_color(1, C("#a98cff"))
		var gt = GradientTexture2D.new()
		gt.gradient = gr
		gt.fill = GradientTexture2D.FILL_RADIAL
		gt.fill_from = Vector2(0.5, 0.35)
		gt.fill_to = Vector2(1.1, 1.0)
		gt.width = 256
		gt.height = 256
		tex["icon_bg"] = gt
	draw_texture_rect(tex["icon_bg"], sq, false)
	# sprinkles
	var r2 = RandomNumberGenerator.new()
	r2.seed = 5
	var cols = ["#ff5fa2", "#7df0c8", "#ffd36b", "#9b7bff", "#8fd8ff"]
	for i in range(26):
		var p = sq.position + Vector2(r2.randf() * 720, r2.randf() * 720)
		var an = r2.randf() * PI
		var d = Vector2(cos(an), sin(an)) * 12
		draw_line(p - d, p + d, C(cols[i % 5], 1.0, 0.55), 9.0, true)
	if v == 1:
		# merge moment: two candies smash into a bigger one
		for k in range(14):
			var an = k * TAU / 14.0
			draw_line(c + Vector2(0, 30), c + Vector2(0, 30) + Vector2(cos(an), sin(an)) * 330.0, C("#ffffff", 1.0, 0.18), 30.0)
		draw_arc(c + Vector2(0, 30), 230, 0, TAU, 64, C("#ffffff", 1.0, 0.7), 14.0, true)
		draw_candy(2, c + Vector2(-200, 230), 80.0, 0.0, 0.3, false, "candy")
		draw_candy(2, c + Vector2(200, 230), 80.0, 0.0, -0.3, false, "candy")
		draw_candy(4, c + Vector2(0, -10), 170.0, 0.0, 0.0, false, "candy")
		face(c + Vector2(0, -10), 170.0)
		return
	# tube arc with a gummy pad at the bottom
	var arc = PackedVector2Array()
	var cc = c + Vector2(0, -40)
	for k in range(61):
		var a = lerpf(deg_to_rad(20.0), deg_to_rad(160.0), k / 60.0)
		arc.append(cc + Vector2(cos(a), sin(a)) * 300.0)
	var TRi = 56.0
	cap_line(arc, INK(), (TRi + 10) * 2.0)
	cap_line(arc, C("#ff5fa2", 0.45), TRi * 2.0)
	cap_line(shifted(arc, Vector2(-8, -14)), C("#ff5fa2"), TRi * 1.55)
	for k in range(2, arc.size() - 1, 3):
		var tg = (arc[k] - arc[k - 1]).normalized()
		var nn = Vector2(-tg.y, tg.x)
		draw_line(arc[k] - nn * TRi * 0.85 - tg * 14.0, arc[k] + nn * TRi * 0.85 + tg * 14.0, Color(1, 1, 1, 0.45), 18.0, true)
	cap_line(shifted(arc, Vector2(-14, -26)), Color(1, 1, 1, 0.35), 14.0)
	var pad = PackedVector2Array()
	for k in range(22, 39):
		var a = lerpf(deg_to_rad(20.0), deg_to_rad(160.0), k / 60.0)
		pad.append(cc + Vector2(cos(a), sin(a)) * (300.0 - TRi * 0.62))
	cap_line(pad, INK(), 48.0)
	cap_line(pad, C("#7df0c8", 1.2), 36.0)
	cap_line(shifted(pad, Vector2(0, -7)), Color(1, 1, 1, 0.6), 9.0)
	# motion lines + bouncing hero candy with a face
	var hero = c + Vector2(10, -60)
	for k in range(3):
		draw_line(hero + Vector2(-60 + k * 60, 170), hero + Vector2(-60 + k * 60, 230), C("#ffffff", 1.0, 0.75), 14.0, true)
	draw_candy(2, hero, 150.0, 0.35, 0.0, false, "candy")
	face(hero, 150.0)
	if v == 0:
		draw_candy(10, c + Vector2(-210, -190), 62.0, 0.0, -0.4, false, "candy")
		draw_candy(1, c + Vector2(225, -200), 52.0, 0.0, 0.3, false, "candy")
	for q in [Vector2(-250, -40), Vector2(250, -60), Vector2(170, -250)]:
		draw_star(c + q, 20.0, C("#fff6c8"))


func draw_icon_art2(v: int) -> void:
	var sq = Rect2(0, 280, 720, 720)
	var c = sq.get_center()
	if v == 3:
		# D: mascot close-up, "wow" face, mid-bounce, hot pink -> violet, rays + coins
		radial_bg(sq, "#ff8ac6", "#6a2cff", "bgD")
		burst_rays(c + Vector2(0, -30), 16, 620.0, C("#ffffff", 1.0, 0.12), 0.09)
		for q in [[Vector2(-250, -230), 46.0], [Vector2(265, -170), 40.0], [Vector2(240, 230), 34.0]]:
			draw_coin(c + q[0], q[1])
		draw_candy(10, c + Vector2(-255, 200), 62.0, 0.0, -0.5, false, "candy")
		draw_mascot(c + Vector2(0, -10), 235.0, 0, 0.18)
		for q in [Vector2(-300, -20), Vector2(300, 40), Vector2(-120, -300), Vector2(160, -305)]:
			draw_star(c + q, 22.0, C("#fff6c8", 1.3))
	elif v == 4:
		# E: mascot framed by the striped tube ring, happy, mint pad below
		radial_bg(sq, "#ffe08a", "#ff4f9a", "bgE")
		burst_rays(c, 18, 620.0, C("#ffffff", 1.0, 0.16), 0.08, 0.1)
		var ring = PackedVector2Array()
		for k in range(97):
			var a = k * TAU / 96.0
			ring.append(c + Vector2(cos(a), sin(a)) * 300.0)
		cap_line(ring, INK(), 104.0)
		cap_line(ring, C("#7b3cff", 0.7), 88.0)
		cap_line(shifted(ring, Vector2(-6, -10)), C("#9b6bff"), 66.0)
		for k in range(1, ring.size(), 3):
			var tg = (ring[k] - ring[k - 1]).normalized()
			var nn = Vector2(-tg.y, tg.x)
			draw_line(ring[k] - nn * 38.0 - tg * 12.0, ring[k] + nn * 38.0 + tg * 12.0, Color(1, 1, 1, 0.45), 15.0, true)
		draw_arc(c, 300, PI * 0.35, PI * 0.65, 20, INK(), 46.0)
		draw_arc(c, 300, PI * 0.36, PI * 0.64, 20, C("#7df0c8", 1.2), 32.0)
		draw_mascot(c + Vector2(0, -6), 200.0, 1, 0.1)
		for q in [Vector2(-170, -170), Vector2(185, -150)]:
			draw_star(c + q, 20.0, C("#fff6c8", 1.3))
	else:
		# F: cheeky wink, mascot bursting out of the frame (bigger than the icon), golden bonbon trail
		radial_bg(sq, "#7ff0d0", "#3a6cff", "bgF")
		burst_rays(c + Vector2(40, 40), 14, 620.0, C("#ffffff", 1.0, 0.14), 0.1, 0.2)
		for k in range(5):
			var q = c + Vector2(-260 + k * 40, 260 - k * 40)
			draw_circle(q, 34.0 - k * 4.0, C("#ffffff", 1.0, 0.25 + k * 0.1))
		draw_coin(c + Vector2(255, -250), 44.0)
		draw_coin(c + Vector2(285, -150), 30.0)
		draw_mascot(c + Vector2(25, 35), 262.0, 2, 0.0)
		draw_star(c + Vector2(-270, -250), 26.0, C("#fff6c8", 1.3))
		draw_star(c + Vector2(-210, -300), 16.0, C("#fff6c8", 1.3))

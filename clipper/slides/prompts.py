"""Prompts slideshows (en anglais : le contenu publié est en anglais)."""

FORMATS = {
    "ranking": "a ranked list (e.g. 'Top 7 strongest characters in X'), counting down to #1 on the last content slide",
    "facts": "surprising but TRUE facts / details fans missed (e.g. '6 details you missed in X')",
    "recommendations": "recommendations (e.g. 'If you loved X, watch these 5'), one anime per slide",
    "quiz": "a quiz/guessing game (e.g. 'Guess the character from one quote'); the answer goes on the end slide",
    "assign": "an assignment game ('Your birth month = your JJK character'): exactly ONE content slide per option, "
              "in order (all 12 months January→December, or all 12 zodiac signs…). On each slide: label = the option "
              "in capitals (e.g. 'JANUARY'), text = ONLY the character's name as fans know it (e.g. 'Satoru Gojo'), "
              "nothing else. Use 12 DIFFERENT, recognisable characters "
              "and keep the most popular ones spread out. No facts needed, confidence 100. End slide: "
              "'Comment your month 👇 who did you get?' or similar",
    "zodiac": "same game as 'assign' but with the 12 zodiac signs in order (ARIES→PISCES): label = the sign, "
              "text = ONLY the character's name (pick characters whose personality fits the sign)",
    "redflags": "'Red flags of dating each X character': one character per slide, label = the character's first name "
                "in capitals, text = one funny red flag rooted in their real personality/canon behaviour",
    "as_people": "'X characters as …' (your coworkers, your classmates, your friend group, gym bros…): one character "
                 "per slide, label = the role (e.g. 'THE INTERN'), text = character — why, short and funny",
    "opinions": "'Unpopular X opinions (don't hate me)': one spicy but defensible opinion per slide, debate bait; "
                "label = 'Opinion N'",
    "ratings": "episode ratings ('Edgerunners 2 episodes ranked by IMDb rating'): the COVER gets a rating chart drawn "
               "automatically from the creator's numbers — cover text = the show + 'IMDb ratings' only (max 6 words). "
               "Content slides = the episodes ranked from the HIGHEST rating to the lowest, one per slide: "
               "label = '#N · EP X', text = 'X.X ⭐ — one short spoiler-free line about the episode'. Use ONLY the "
               "ratings given by the creator, never invent or change a number. If the creator gives SEVERAL SEASONS "
               "(S1: …, S2: …): the cover chart is season 1 and a chart slide is added for each other season "
               "automatically; cover text = the show + 'Season 1' (max 6 words); content slides = the 5 best "
               "episodes across all seasons, label = '#N · S1E10'. End slide: 'Which season was better? 👇' "
               "(several seasons) or 'Which episode was your favourite? 👇'. If the creator gives ONE single "
               "episode or only the show's overall score: the post is ONLY the rating card — NO content slides "
               "(empty list), the end slide is dropped; cover text = the show (+ episode) only, max 6 words; the "
               "caption ends with a question ('Did it deserve this score? 👇')",
    "news": "a single NEWS card (anime news: release, episode date, announcement). The headline on the image is "
            "the creator's topic, written as is — you write NO content slides (empty list) and the end slide is "
            "dropped. Cover: set character/scene to pick a fitting image (main character of the show). Caption = "
            "the description: 2-4 short sentences with ONLY the details given by the creator (date, platform, "
            "episode…) plus well-known context, then one question for the comments. NEVER invent a date, time, "
            "platform or detail that was not given. If the creator's instructions contain lines starting with "
            "'>' (extra cards, e.g. a fun fact), write exactly ONE content slide per '>' line, in order, whose "
            "character/scene = who that line is about (the text will be replaced by the creator's line)",
    "wallpaper": "an aesthetic wallpaper dump ('JJK wallpapers for your lockscreen'): the cover text is replaced by "
                 "the creator's topic; content "
                 "slides have NO text at all (empty text and label) — only a character and a striking scene to show; "
                 "end slide: 'Which one is your lockscreen? 👇'",
}

# Formats dont le nombre de slides de contenu est fixé par le jeu (12 mois, 12 signes…).
FIXED_SLIDES = {"assign": 12, "zodiac": 12}
# Formats sans faits à vérifier (pas d'alerte « fait incertain »).
NO_FACTS = {"assign", "zodiac", "redflags", "as_people", "opinions", "wallpaper"}

IDEAS_SYSTEM = """You plan viral TikTok/Instagram photo slideshows for an English-speaking anime fan account.
A slideshow = 1 cover slide with a hook, {min_s}-{max_s} content slides with short text over an anime image, 1 end slide.

What performs: assignment games ("Your birth month = your JJK character", zodiac signs — people comment their \
result), "red flags of dating each character", "characters as your coworkers", unpopular opinions, aesthetic \
wallpaper dumps, strong debate-bait hooks ("Top 5 saddest deaths — #1 will hurt"), rankings fans will argue about \
in the comments, little-known but verifiable details, "if you liked X watch Y". Avoid spoilers in the HOOK \
(spoiler warnings are fine inside). Never invent facts.

Only use these anime: {animes}.
Allowed formats: {formats}."""

IDEAS_USER = """Propose {n} distinct slideshow ideas.
Do NOT repeat or closely paraphrase these existing topics:
{existing}

{trends}
For each: anime (exactly one of the allowed names, or "Mixed" for multi-anime recommendations/quizzes), \
format, topic (the slideshow title), hook (cover text, max 9 words, all caps friendly), angle (one sentence on \
what makes it engaging), score (0-100, your honest estimate of viral potential; use the whole scale), \
why (one short sentence), inspired_by (ids of the trending posts it builds on, if any)."""

TRENDS_BLOCK = """
What is performing RIGHT NOW in this niche (trend research, [id] then stats):
{rows}
Use these as signals: favour the formats, hook patterns and anime that are working, but ADAPT — new angle, different characters or a twist. Never copy a hook or topic word for word.
"audience" tells what viewers argued about or asked for in the comments: answering that is the best angle.
"""

ANILIST_BLOCK = """
Trending on AniList this week (what anime fans are watching now), with their fan-favourite characters:
{rows}
Prefer allowed anime that appear here, and their fan-favourite characters.
"""

FOCUS_BLOCK = """
Build ALL ideas around this one trending post (same winning mechanic, your own angle — never a copy):
{row}
"""

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {"ideas": {"type": "array", "items": {"type": "object", "properties": {
        "anime": {"type": "string"}, "format": {"type": "string"}, "topic": {"type": "string"},
        "hook": {"type": "string"}, "angle": {"type": "string"},
        "score": {"type": "integer", "minimum": 0, "maximum": 100}, "why": {"type": "string"},
        "inspired_by": {"type": "array", "items": {"type": "integer"}}},
        "required": ["anime", "format", "topic", "hook", "angle", "score", "why"]}}},
    "required": ["ideas"],
}

SCRIPT_SYSTEM = """You write the slides of an English anime photo slideshow for TikTok, Instagram and YouTube Shorts.

Rules:
- Cover: the hook, max 9 words.
{characters}- {min_s} to {max_s} content slides. Each: max {max_words} words, punchy, readable in 2 seconds. \
No hashtags or emojis on slides.
- Optional short label per content slide ("#5", "Fact 3", "Pick 2"…).
- End slide: for quizzes the answer(s); otherwise a comment-bait question, max 12 words. Do NOT add \
"follow/subscribe" — a follow line is added automatically under it.
- ACCURACY: only state things you are confident are canon/true. For each content slide give your \
confidence 0-100. Prefer well-known facts over obscure ones; never invent episode numbers or quotes.
- For every slide (cover and end included) name the anime, the main character to show (exact common English \
name, or "" if none) and a short visual scene description, so the right image can be picked.
- Caption (Instagram/TikTok search reads it, keywords now matter more than hashtags): line 1 = a short hook that names the anime, the characters and the topic with the words fans would TYPE in search (e.g. 'Jujutsu Kaisen wallpapers for your iPhone lock screen — Gojo, Sukuna, Toji'); line 2 = one natural sentence of context, no keyword stuffing; line 3 = a direct question that makes people comment (or 'Save this for later' for wallpapers/lists). 3-5 precise hashtags (lowercase, no #), anime + character + format, never generic ones like fyp/viral.
- YouTube Shorts title: max 70 characters, no hashtags. YouTube description: 1-2 sentences."""

SCRIPT_USER = """Format: {format_desc}
Anime: {anime}
Topic: {topic}
Hook idea: {hook}
Angle: {angle}{feedback}"""

SLIDE_ITEM = {"type": "object", "properties": {
    "label": {"type": "string"}, "text": {"type": "string"},
    "anime": {"type": "string"}, "character": {"type": "string"}, "scene": {"type": "string"},
    "confidence": {"type": "integer", "minimum": 0, "maximum": 100}},
    "required": ["text", "anime", "character", "scene"]}

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "cover": SLIDE_ITEM, "slides": {"type": "array", "items": SLIDE_ITEM}, "end": SLIDE_ITEM,
        "caption": {"type": "string"}, "hashtags": {"type": "array", "items": {"type": "string"}},
        "yt_title": {"type": "string"}, "yt_description": {"type": "string"},
    },
    "required": ["cover", "slides", "end", "caption", "hashtags", "yt_title", "yt_description"],
}

PICK_SYSTEM = """You pick the best background image for one slide of an anime slideshow.
Prefer: the named character clearly visible (face visible), matching the scene/mood, sharp, not a blank or \
transition frame, and leaving room for overlaid text. If the named character does not appear in any image, \
pick the most fitting image from the same anime and set character_match to false."""

PICK_SCHEMA = {
    "type": "object",
    "properties": {"index": {"type": "integer"}, "character_match": {"type": "boolean"},
                   "ranking": {"type": "array", "items": {"type": "integer"},
                               "description": "best 4 indices, best first"}},
    "required": ["index", "character_match"],
}

TAG_SYSTEM = """You sort anime screenshots from {anime} by character, for an image library.
For each numbered image, give the ONE main character clearly shown (face visible, takes a large part of the \
frame), using their common full English name. Reuse these exact spellings when it is one of them: {known}.
If there is no clear main character (group shot, back view, object, landscape, text card) or you are not sure, \
return an empty character. Confidence 0-100 = how sure you are of the identity. Never guess."""

TAG_SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "object", "properties": {
    "index": {"type": "integer"}, "character": {"type": "string"},
    "confidence": {"type": "integer", "minimum": 0, "maximum": 100}},
    "required": ["index", "character", "confidence"]}}}, "required": ["items"]}

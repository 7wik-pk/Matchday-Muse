"""Words the name check accepts besides the match's own people, teams and
venue. A capitalised word in mid-line that is in none of these is treated as
a name the poem may not use.

TEAM_ALIASES is keyed by ESPN's team display name; teams not listed simply
get no aliases.
"""

TEAM_ALIASES: dict[str, set[str]] = {
    "AFC Bournemouth": {"Cherries", "Bournemouth", "Vitality"},
    "Arsenal": {"Gunners", "Emirates", "Highbury"},
    "Aston Villa": {"Villa", "Villans", "Villa Park"},
    "Brentford": {"Bees", "Gtech"},
    "Brighton & Hove Albion": {"Seagulls", "Albion", "Brighton", "Amex"},
    "Burnley": {"Clarets", "Turf Moor"},
    "Chelsea": {"Blues", "Stamford Bridge"},
    "Coventry City": {"Sky Blues", "Coventry"},
    "Crystal Palace": {"Eagles", "Palace", "Selhurst"},
    "Everton": {"Toffees", "Blues", "Goodison", "Merseyside"},
    "Fulham": {"Cottagers", "Craven Cottage"},
    "Hull City": {"Tigers", "Hull"},
    "Ipswich Town": {"Tractor Boys", "Blues", "Ipswich", "Portman Road"},
    "Leeds United": {"Whites", "Peacocks", "Leeds", "Elland Road"},
    "Leicester City": {"Foxes", "Leicester"},
    "Liverpool": {"Reds", "Anfield", "Merseyside", "Kop"},
    "Manchester City": {"Citizens", "Sky Blues", "City", "Etihad"},
    "Manchester United": {"Red Devils", "United", "Old Trafford"},
    "Middlesbrough": {"Boro", "Riverside"},
    "Newcastle United": {"Magpies", "Toon", "Newcastle", "Geordies", "St James"},
    "Nottingham Forest": {"Forest", "Tricky Trees", "City Ground"},
    "Sheffield United": {"Blades", "Bramall Lane"},
    "Southampton": {"Saints", "St Mary"},
    "Sunderland": {"Black Cats", "Mackems", "Stadium of Light"},
    "Tottenham Hotspur": {"Spurs", "Lilywhites", "Tottenham"},
    "West Ham United": {"Hammers", "Irons", "West Ham"},
    "Wolverhampton Wanderers": {"Wolves", "Molineux"},
}

# The stock figures each form may invoke (design doc: The poem).
STOCK_FIGURES: dict[str, set[str]] = {
    "mock_heroic": {"Muse", "Muses", "Fate", "Fates", "Gods", "God", "Olympus", "Heaven", "Heavens", "Jove"},
    "sonnet": {"Fortune", "Time", "Fate"},
    "villanelle": {"Time", "Fate"},
}

GENERIC: set[str] = {
    "VAR", "O", "Oh", "God", "Lord", "Heaven", "Heavens", "Premier", "League", "England", "English",
    "Football", "Cup", "FA", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
    "November", "December",
}  # fmt: skip

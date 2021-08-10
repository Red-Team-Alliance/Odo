# Define patterns here

vibe_full = "Vibrate:20;"
vibe_half = "Vibrate:10;"
vibe_off = "Vibrate:0;"

foho = [(vibe_full, 0.2),
        (vibe_off, 0.1), 
        (vibe_half, 0.2), 
        (vibe_off, 0)
]
named_patterns = {
        "foho": foho
}

event_patterns = {
        "seen": foho,
        "selected": foho,
        "written": {
                "success": foho,
                "failure": foho
        }
}
from __future__ import annotations

SEGMENTS = [
    ("Kids Party & Papercraft", [
        "favor box", "favour box", "treat box", "papercraft", "pixel party",
        "voxel party", "block adventure", "cube party", "loot box",
        "cupcake topper", "party bag topper", "party mask", "party printable"
    ]),
    ("Craft & DIY", [
        "leather pattern", "wallet pattern", "sewing pattern", "woodworking plan",
        "laser cut", "cricut", "silhouette", "paper model", "stencil", "dxf", "svg cut"
    ]),
    ("Business Operations", ["business", "employee", "supplier", "kpi", "meeting", "operating procedure", "client onboarding"]),
    ("Freelance & Agency", ["freelance", "agency", "proposal", "retainer", "creative brief", "service pricing"]),
    ("Creator & Content", ["content", "social media", "youtube", "podcast", "newsletter", "sponsorship", "brand collaboration"]),
    ("Ecommerce & Retail", ["inventory", "etsy", "shopify", "ecommerce", "product launch", "order", "returns"]),
    ("Property & Home", ["property", "home", "cleaning", "moving", "renovation", "garden"]),
    ("Events & Weddings", ["wedding", "event", "party", "conference", "guest list", "vendor"]),
    ("Education & Study", ["study", "assignment", "exam", "teacher", "student", "reading", "homeschool", "course"]),
    ("Productivity & Personal Admin", ["project", "weekly planner", "habit", "goal", "personal budget", "subscription", "document expiry", "declutter"]),
    ("Travel", ["travel", "trip", "vacation", "packing", "road trip", "booking"]),
    ("Fitness & Lifestyle", ["fitness", "workout", "running", "cycling", "meal", "grocery", "hydration", "sleep"]),
    ("Pets", ["pet", "dog", "puppy", "vaccination", "feeding"]),
    ("Career & Job Search", ["job", "interview", "career", "resume", "networking", "professional development", "certification", "portfolio"]),
]


def segment_for_phrase(phrase: str) -> str:
    text = phrase.lower()
    for segment, keywords in SEGMENTS:
        if any(keyword in text for keyword in keywords):
            return segment
    return "Other"

from __future__ import annotations

SEGMENTS = [
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

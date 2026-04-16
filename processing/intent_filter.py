def intent_score(intent):

    if not intent:
        return 0.1

    intent = intent.lower().strip()

    mapping = {
        "order": 1.0,
        "offer": 0.9,
        "negotiation": 0.6,
        "inquiry": 0.3
    }

    return mapping.get(intent, 0.1)
from hashlib import sha256

def heuristic_user_score(username: str, bio: str = "") -> float:
    score = 50.0
    red_flags = ["scam", "card", "dump", "cheap", "unlock", "bypass"]
    for flag in red_flags:
        if flag in (username or "").lower() or flag in (bio or "").lower():
            score -= 10
    if username:
        score += (int(sha256(username.encode()).hexdigest(), 16) % 10) / 2
    return max(0.0, min(100.0, score))

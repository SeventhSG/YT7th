"""Playful copy for the in-app experience."""
import random

STARTING = [
    "Warming up the pipes...",
    "Negotiating with YouTube's robots...",
    "Summoning pixels...",
    "Reticulating splines...",
    "Bribing the buffering gods...",
    "Hold tight, magic incoming...",
]

DONE = [
    "Got it. Saved and sound.",
    "Done. Another one for the vault.",
    "Archived. You're welcome.",
    "Saved. Crisp and clean.",
    "Boom. That's yours now.",
]

EMPTY_HISTORY = [
    "Nothing here yet. Go grab something.",
    "Your vault is empty. For now.",
    "No downloads yet - the page is blank and full of potential.",
]

READY = "Ready when you are."


def starting():
    return random.choice(STARTING)


def done():
    return random.choice(DONE)


def empty_history():
    return random.choice(EMPTY_HISTORY)

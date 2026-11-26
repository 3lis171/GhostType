"""Generate a paced sequence of text and optional visible typo corrections."""
import random
import string


def typing_events(text, wpm=55, typo_rate=0.0, rng=None):
    """Yield (action, text, delay_after_seconds); five characters = one word."""
    if not 10 <= wpm <= 200:
        raise ValueError('WPM must be between 10 and 200.')
    if not 0 <= typo_rate <= 0.15:
        raise ValueError('Typo rate must be between 0 and 0.15.')
    if any(not ch.isprintable() for ch in text):
        raise ValueError('Human mode supports single-line printable text only. Use Ctrl+Shift+Space for multiline output.')
    rng = rng or random.Random()
    base = 60 / (wpm * 5)
    for index, ch in enumerate(text):
        # Avoid a mistake on the first character (which replaces the selection).
        if index and ch in string.ascii_letters and rng.random() < typo_rate:
            alphabet = string.ascii_uppercase if ch.isupper() else string.ascii_lowercase
            wrong = rng.choice(alphabet.replace(ch, ''))
            yield 'text', wrong, rng.uniform(0.12, 0.27)
            yield 'backspace', '', rng.uniform(0.07, 0.16)
        delay = base * rng.uniform(0.65, 1.35)
        if ch in '.!?':
            delay += rng.uniform(0.25, 0.65)
        elif ch in ',;:':
            delay += rng.uniform(0.10, 0.25)
        yield 'text', ch, delay

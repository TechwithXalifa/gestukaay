import os

# Les tests envoient beaucoup de requêtes depuis la même adresse : limites coupées,
# sauf dans test_securite.py qui les réactive.
os.environ.setdefault("GESTUKAAY_LIMITES", "off")

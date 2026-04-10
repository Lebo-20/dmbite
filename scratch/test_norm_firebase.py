from firebase_utils import normalize_title

test_cases = [
    ("Avengers Endgame", "avengers endgame"),
    ("  Avengers   Endgame  ", "avengers endgame"),
    ("Avengers.Endgame#2019", "avengersendgame2019"),
    ("Drama [Keren] $100", "drama keren 100"),
]

print("Testing Normalization Logic:")
for input_str, expected in test_cases:
    result = normalize_title(input_str)
    status = "PASS" if result == expected else f"FAIL (Got: '{result}')"
    print(f"Input: '{input_str}'\nResult: '{result}'\nStatus: {status}\n")

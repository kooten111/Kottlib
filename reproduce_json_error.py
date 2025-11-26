import json

def test_decode(s):
    try:
        json.loads(s)
        print(f"'{s}': Valid")
    except json.JSONDecodeError as e:
        print(f"'{s}': {e}")

test_decode("{}x")
test_decode("[]x")
test_decode("1 2")
test_decode('""x')
test_decode("{} {}")
test_decode("{}\x00")

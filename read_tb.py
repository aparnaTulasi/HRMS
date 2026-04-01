import re
with open('backend_error.log', 'r') as f:
    text = f.read()

tracebacks = text.split('Traceback (most recent call last):')
if len(tracebacks) > 1:
    last_tb = tracebacks[-1].strip()
    with open('last_tb.txt', 'w') as out:
        out.write(last_tb)
    print("Wrote to last_tb.txt")
else:
    print("No traceback found in log.")

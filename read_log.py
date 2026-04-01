with open('backend_error.log', 'r') as f:
    lines = f.readlines()
    print(''.join(lines[-40:]))

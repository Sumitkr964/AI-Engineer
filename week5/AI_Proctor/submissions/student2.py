def is_prime(n):
    if n < 2:
        return False

    for divisor in range(2, n):
        if n % divisor == 0:
            return False

    return True


value = 17

if is_prime(value):
    print("Prime Number")
else:
    print("Not Prime")
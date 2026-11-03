def prime_check(number):
    if number <= 1:
        return False

    count = 0

    for x in range(1, number + 1):
        if number % x == 0:
            count += 1

    return count == 2


num = 17

if prime_check(num):
    print("Prime Number")
else:
    print("Not Prime")
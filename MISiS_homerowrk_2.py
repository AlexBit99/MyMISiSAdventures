import math


class Rational:
    def __init__(self, a=0, b=1):
        if b == 0:
            raise ValueError('На 0 делить нельзя!')

        if b < 0:
            a = -a
            b = -b

        g = math.gcd(abs(a), b)
        self.a = a // g
        self.b = b // g

    def __add__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        new_a = self.a * thng.b + thng.a * self.b
        new_b = self.b * thng.b
        return Rational(new_a, new_b)

    def __radd__(self, thng):
        return self + thng

    def __sub__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        new_a = self.a * thng.b - thng.a * self.b
        new_b = self.b * thng.b
        return Rational(new_a, new_b)

    def __rsub__(self, other):
        return Rational(other, 1) - self

    def __mul__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        new_a = self.a * thng.a
        new_b = self.b * thng.b
        return Rational(new_a, new_b)

    def __rmul__(self, thng):
        return self * thng

    def __truediv__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        if thng.a == 0:
            raise ValueError('На 0 делить нельзя!')
        new_a = self.a * thng.b
        new_b = self.b * thng.a
        return Rational(new_a, new_b)

    def __rtruediv__(self, thng):
        return Rational(thng, 1) / self

    def __eq__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        return self.a == thng.a and self.b == thng.b

    def __lt__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        return self.a * thng.b < thng.a * self.b

    def __le__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        return self.a * thng.b <= thng.a * self.b

    def __gt__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        return self.a * thng.b > thng.a * self.b

    def __ge__(self, thng):
        if isinstance(thng, int):
            thng = Rational(thng, 1)
        return self.a * thng.b >= thng.a * self.b

    def __str__(self):
        if self.b == 1:
            return str(self.a)
        return f"{self.a}/{self.b}"


if __name__ == "__main__":
    primer1 = Rational(1, 3)
    primer2 = Rational(2, 4)
    primer3= Rational(3, 4)

    print(f"r1 = {primer1}")
    print(f"r2 = {primer2}")
    print(f"r3 = {primer3}")

    print(f"r1 == r2: {primer1 == primer2}")
    print(f"r1 == r3: {primer1 == primer3}")
    print(f"r1 < r3: {primer1 < primer3}")

    print(f"r1 + r3 = {primer1 + primer3}")
    print(f"r1 - r3 = {primer1 - primer3}")
    print(f"r1 * r3 = {primer1 * primer3}")
    print(f"r1 / r3 = {primer1 / primer3}")

    print(f"r1 + 1 = {primer1 + 1}")
    print(f"2 * r1 = {2 * primer1}")

    primer4 = Rational(-1, 2)
    primer5 = Rational(1, -2)
    print(f"r4 = {primer4}")
    print(f"r5 = {primer5}")

    primer6 = Rational(0, 5)
    print(f"r6 = {primer6}")
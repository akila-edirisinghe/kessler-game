from math import inf, nan, sqrt
from typing import Tuple

def is_nearly_zero(value: float, epsilon: float = 1e-7) -> bool:
    return abs(value) < epsilon

def solve_quadratic(a: float, b: float, c: float) -> Tuple[float, float]:
    discriminant = b**2 - 4*a*c
    if discriminant < 0:
        return nan, nan
    elif is_nearly_zero(discriminant):
        t = -b / (2*a)
        return t, t
    else:
        sqrt_disc = sqrt(discriminant)
        t1 = (-b + sqrt_disc) / (2*a)
        t2 = (-b - sqrt_disc) / (2*a)
        if t1 > t2:
            t1, t2 = t2, t1
        return t1 , t2

def are_both_stationary(vel1: Tuple[float, float], vel2: Tuple[float, float]) -> bool:
    return all(is_nearly_zero(v) for v in vel1 + vel2)

def check_immediate_collision(pos1: Tuple[float, float], pos2: Tuple[float, float], combined_radius: float) -> bool:
    delta_x = pos1[0] - pos2[0]
    delta_y = pos1[1] - pos2[1]
    return delta_x**2 + delta_y**2 <= combined_radius**2

def predict_collision(
    pos1: Tuple[float, float], vel1: Tuple[float, float], radius1: float,
    pos2: Tuple[float, float], vel2: Tuple[float, float], radius2: float
) -> Tuple[float, float]:
    """
    Predicts the collision time between two moving circles.

    :param pos1: Position (x, y) of circle 1
    :param vel1: Velocity (x, y) of circle 1
    :param radius1: Radius of circle 1
    :param pos2: Position (x, y) of circle 2
    :param vel2: Velocity (x, y) of circle 2
    :param radius2: Radius of circle 2
    :return: Tuple of times when the circles will collide (nan, nan if no collision)
    """
    combined_radius = radius1 + radius2
    delta_pos = (pos1[0] - pos2[0], pos1[1] - pos2[1])

    if are_both_stationary(vel1, vel2):
        if check_immediate_collision(pos1, pos2, combined_radius):
            return -inf, inf
        else:
            return nan, nan

    delta_vel = (vel1[0] - vel2[0], vel1[1] - vel2[1])
    a = delta_vel[0]**2 + delta_vel[1]**2
    b = 2.0 * (delta_pos[0] * delta_vel[0] + delta_pos[1] * delta_vel[1])
    c = delta_pos[0]**2 + delta_pos[1]**2 - combined_radius**2

    return solve_quadratic(a, b, c)

# Example usage:
# print(predict_collision((0, 0), (1, 1), 1, (10, 10), (-1, -1), 1))

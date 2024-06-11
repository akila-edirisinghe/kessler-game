from src.kesslergame import Scenario

import numpy as np

pad = 50
width = 1000
height = 800

ex_adv_four_corners_pt1 = Scenario(
    name='ex_adv_four_corners_pt1',
    asteroid_states=[
        {'position': (pad, pad), 'angle': 0.0, 'speed': 0, 'size': 1},
        {'position': (width - pad, pad), 'angle': 0.0, 'speed': 0, 'size': 4},
        {'position': (pad, height - pad), 'angle': 0.0, 'speed': 0, 'size': 2},
        {'position': (width - pad, height - pad), 'angle': 0.0, 'speed': 0, 'size': 3},
    ],
    ship_states=[{'position': (width//2, height//2), 'lives': 3, 'angle': 0, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height//2), 'lives': 3, 'angle': 0, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ex_adv_four_corners_pt2 = Scenario(
    name='ex_adv_four_corners_pt2',
    asteroid_states=[
        {'position': (pad, pad), 'angle': 0.0, 'speed': 0, 'size': 4},
        {'position': (width - pad, pad), 'angle': 0.0, 'speed': 0, 'size': 4},
        {'position': (pad, height - pad), 'angle': 0.0, 'speed': 0, 'size': 4},
        {'position': (width - pad, height - pad), 'angle': 0.0, 'speed': 0, 'size': 4},
    ],
    ship_states=[{'position': (width//2, height//2), 'lives': 3, 'angle': 0, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height//2), 'lives': 3, 'angle': 0, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=30,
)

height_off_edge = 100

ex_adv_asteroids_down_up_pt1 = Scenario(
    name='ex_adv_asteroids_down_up_pt1',
    asteroid_states=[
        {'position': (width*2//5, height_off_edge), 'angle': 90.0, 'speed': 100, 'size': 2},
        {'position': (width*2//5, height - height_off_edge), 'angle': -90.0, 'speed': 100, 'size': 2},
    ],
    ship_states=[{'position': (width*4/10, height//2), 'angle': 0, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height//2), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ex_adv_asteroids_down_up_pt2 = Scenario(
    name='ex_adv_asteroids_down_up_pt2',
    asteroid_states=[
        {'position': (width*2//5, 0), 'angle': 90.0, 'speed': 100, 'size': 2},
        {'position': (width*2//5, height - 0), 'angle': -90.0, 'speed': 100, 'size': 2},
    ],
    ship_states=[{'position': (width/2, height//2), 'angle': 0, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height//2), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ex_adv_direct_facing = Scenario(
    name='ex_adv_direct_facing',
    asteroid_states=[
        {'position': (width*2//3, height*2//5), 'angle': 180.0, 'speed': 100, 'size': 2},
    ],
    ship_states=[{'position': (width*2//10, height*2//5), 'angle': 0, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height*5/100), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ex_adv_two_asteroids_pt1 = Scenario(
    name='ex_adv_two_asteroids_pt1',
    asteroid_states=[
        {'position': (width*17//24, height//10), 'angle': 90.0, 'speed': 100, 'size': 3},
        {'position': (width*17//24, height*9//10), 'angle': -90.0, 'speed': 100, 'size': 3},
    ],
    ship_states=[{'position': (width/10, height//2), 'angle': 180, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width/10, height*9/10), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ex_adv_two_asteroids_pt2 = Scenario(
    name='ex_adv_two_asteroids_pt2',
    asteroid_states=[
        {'position': (width//10, height//10), 'angle': 90.0, 'speed': 100, 'size': 3},
        {'position': (width//10, height*9//10), 'angle': -90.0, 'speed': 100, 'size': 3},
    ],
    ship_states=[{'position': (width/10, height//2), 'angle': 180, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*7/10, height*9/10), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=20,
)

ring_radius = 150
num_asteroids = 18
ship_position = (width*4//10, height//3)
# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi - 1/num_asteroids*2*np.pi, num_asteroids, endpoint=False)
ast_x = [ring_radius * np.cos(angle - np.pi/2) + ship_position[0] for angle in theta]
ast_y = [ring_radius * np.sin(angle - np.pi/2) + ship_position[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(ship_position[1] - y, ship_position[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states = [{"position": (x, y), "angle": angle, "speed": 0, 'size': 1} for x, y, angle in zip(ast_x, ast_y, init_angle)]
asteroid_states.append({"position": (width*4//10, height), "angle": 270, "speed": 150, 'size': 1})
ex_adv_ring_pt1 = Scenario(
    name="ex_adv_ring_pt1",
    asteroid_states=asteroid_states,
    ship_states=[{"position": ship_position, 'angle': 180, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {'position': (width/10, height*9/10), 'angle': 0, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    time_limit=20,
)





adv_random_big_1 = Scenario(
    name='adv_random_big_1',
    asteroid_states=[{'position': (width*0.18, height*0.1), 'angle': 0.0, 'speed': 0, 'size': 4},
                     {'position': (width*0.11, height*0.35), 'angle': 180.0, 'speed': 100, 'size': 4},
                     {'position': (width*0.4, height*0.4), 'angle': 115.0, 'speed': 90, 'size': 3},
                     {'position': (width*0.44, height*0.44), 'angle': 290.0, 'speed': 110, 'size': 4},
                     {'position': (width*0.16, height*0.53), 'angle': 170.0, 'speed': 95, 'size': 3},
                     {'position': (width*0.18, height*0.7), 'angle': 280.0, 'speed': 40, 'size': 3},
                     {'position': (width*0.39, height*0.71), 'angle': 30.0, 'speed': 100, 'size': 4},
                     {'position': (width*0.1, height*0.9), 'angle': 250.0, 'speed': 30, 'size': 4},
                     {'position': (width*0.38, height*0.97), 'angle': 40.0, 'speed': 40, 'size': 4},
                     ],
    ship_states=[{'position': (width*0.25, height*0.12), 'angle': 180, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {'position': (width*0.05, height*0.14), 'angle': 180, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    time_limit=45,
)


adv_random_big_2 = Scenario(
    name='adv_random_big_2',
    asteroid_states=[{'position': (width*0.18, height*0.1), 'angle': 0.0, 'speed': 0, 'size': 4},
                     {'position': (width*0.11, height*0.35), 'angle': 180.0, 'speed': 100, 'size': 4},
                     {'position': (width*0.4, height*0.4), 'angle': 115.0, 'speed': 90, 'size': 3},
                     {'position': (width*0.44, height*0.44), 'angle': 290.0, 'speed': 110, 'size': 4},
                     {'position': (width*0.16, height*0.53), 'angle': 170.0, 'speed': 95, 'size': 3},
                     {'position': (width*0.18, height*0.7), 'angle': 280.0, 'speed': 40, 'size': 3},
                     {'position': (width*0.39, height*0.71), 'angle': 30.0, 'speed': 100, 'size': 4},
                     {'position': (width*0.1, height*0.9), 'angle': 250.0, 'speed': 30, 'size': 4},
                     {'position': (width*0.38, height*0.97), 'angle': 40.0, 'speed': 40, 'size': 4},
                     ],
    ship_states=[{'position': (width*0.05, height*0.14), 'angle': 180, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {'position': (width*0.25, height*0.12), 'angle': 180, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    time_limit=45,
)



adv_random_big_3 = Scenario(
    name='adv_random_big_3',
    asteroid_states=[{'position': (width*0.1, height*0.83), 'angle': 250.0, 'speed': 150, 'size': 4},
                     {'position': (width*0.11, height*0.65), 'angle': 180.0, 'speed': 10, 'size': 4},
                     {'position': (width*0.61, height*0.7), 'angle': 165.0, 'speed': 140, 'size': 4},
                     {'position': (width*0.09, height*0.4), 'angle': 220.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.1, height*0.44), 'angle': 45.0, 'speed': 130, 'size': 3},
                     {'position': (width*0.18, height*0.47), 'angle': 0.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.53, height*0.52), 'angle': 30.0, 'speed': 80, 'size': 4},
                     {'position': (width*0.6, height*0.44), 'angle': 35.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.3, height*0.07), 'angle': 190.0, 'speed': 60, 'size': 3},
                     {'position': (width*0.66, height*0.33), 'angle': 195.0, 'speed': 40, 'size': 4},
                     ],
    ship_states=[{'position': (width*0.72, height*0.04), 'angle': 0, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {'position': (width*0.72, height*0.92), 'angle': 0, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    time_limit=45,
)


adv_random_big_4 = Scenario(
    name='adv_random_big_4',
    asteroid_states=[{'position': (width*0.1, height*0.83), 'angle': 250.0, 'speed': 150, 'size': 4},
                     {'position': (width*0.11, height*0.65), 'angle': 180.0, 'speed': 10, 'size': 4},
                     {'position': (width*0.61, height*0.7), 'angle': 165.0, 'speed': 140, 'size': 4},
                     {'position': (width*0.09, height*0.4), 'angle': 220.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.1, height*0.44), 'angle': 45.0, 'speed': 130, 'size': 3},
                     {'position': (width*0.18, height*0.47), 'angle': 0.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.53, height*0.52), 'angle': 30.0, 'speed': 80, 'size': 4},
                     {'position': (width*0.6, height*0.44), 'angle': 35.0, 'speed': 70, 'size': 4},
                     {'position': (width*0.3, height*0.07), 'angle': 190.0, 'speed': 60, 'size': 3},
                     {'position': (width*0.66, height*0.33), 'angle': 195.0, 'speed': 40, 'size': 4},
                     ],
    ship_states=[{'position': (width*0.72, height*0.92), 'angle': 0, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {'position': (width*0.72, height*0.04), 'angle': 0, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    time_limit=45,
)



num_asteroids = 9
side_padding = 60
asteroid_spacing = (width - 2*side_padding) // num_asteroids  # Spacing between asteroids
asteroid_speed = 90  # Constant speed of the asteroids
asteroid_start_y = 0  # Starting height at the top of the screen

# Create asteroid states
asteroid_states = []
for i in range(num_asteroids):
    x_position = side_padding + i * asteroid_spacing + asteroid_spacing / 2  # Centering each asteroid
    asteroid_states.append({
        'position': (x_position, asteroid_start_y),
        'angle': -90,  # Moving straight down
        'speed': asteroid_speed,
        'size': 4,
    })

# Create the scenario
adv_multi_wall_bottom_hard_1 = Scenario(
    name='adv_multi_wall_bottom_hard_1',
    asteroid_states=asteroid_states,
    ship_states=[{'position': (width/4, height*9//10), 'angle': 90, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width*3/4, height*9//10), 'angle': 90, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=45,
)




num_asteroids = 7
side_padding = 60
asteroid_spacing = (height - 2*side_padding)/num_asteroids  # Spacing between asteroids
asteroid_speed = 150  # Constant speed of the asteroids
asteroid_start_x = width*4/5  # Starting height at the top of the screen

# Create asteroid states
asteroid_states = []
for i in range(num_asteroids):
    y_position = side_padding + i * asteroid_spacing + asteroid_spacing/2  # Centering each asteroid
    asteroid_states.append({
        'position': (asteroid_start_x, y_position),
        'angle': 180,
        'speed': asteroid_speed,
        'size': 4,
    })

# Create the scenario
adv_multi_wall_right_hard_1 = Scenario(
    name='adv_multi_wall_right_hard_1',
    asteroid_states=asteroid_states,
    ship_states=[{'position': (width/5, height*3/4), 'angle': 90, 'lives': 3, 'team': 1, 'mines_remaining': 3},
                 {'position': (width/5, height/4), 'angle': 90, 'lives': 3, 'team': 2, 'mines_remaining': 3}],
    map_size=(width, height),
    time_limit=45,
)






# Parameters for the ring of asteroids
R_initial = 300  # Initial radius of the ring, large enough to enclose the ship
num_asteroids = 16  # Number of asteroids in the ring
speed = 40  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
ship_position = (width/5, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + ship_position[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(ship_position[1] - y, ship_position[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states = [{"position": (x, y), "angle": angle, "speed": speed} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
adv_multi_ring_closing_left = Scenario(
    name="adv_multi_ring_closing_left",
    asteroid_states=asteroid_states,
    ship_states=[{"position": ship_position, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=120,
)







# Parameters for the ring of asteroids
R_initial = 300  # Initial radius of the ring, large enough to enclose the ship
num_asteroids = 16  # Number of asteroids in the ring
speed = 40  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
ship_position = (width/5, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position_2[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + ship_position_2[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(ship_position_2[1] - y, ship_position_2[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states = [{"position": (x, y), "angle": angle, "speed": speed} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
adv_multi_ring_closing_right = Scenario(
    name="adv_multi_ring_closing_right",
    asteroid_states=asteroid_states,
    ship_states=[{"position": ship_position, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=120,
)








# Parameters for the ring of asteroids
R_initial = 300  # Initial radius of the ring, large enough to enclose the ship
num_asteroids = 16  # Number of asteroids in the ring
speed = 40  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
ship_position_1 = (width/5, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position_1[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + ship_position_1[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(ship_position_1[1] - y, ship_position_1[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states_1 = [{"position": (x, y), "angle": angle, "speed": speed} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position_2[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + ship_position_2[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(ship_position_2[1] - y, ship_position_2[0] - x)) for x, y in zip(ast_x, ast_y)]

asteroid_states_2 = [{"position": (x, y), "angle": angle, "speed": speed} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
adv_multi_two_rings_closing = Scenario(
    name="adv_multi_two_rings_closing",
    asteroid_states=asteroid_states_1 + asteroid_states_2,
    ship_states=[{"position": ship_position_1, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=120,
)










# Parameters for the ring of asteroids
R_initial = 300  # Initial radius of the ring, large enough to enclose the ship
R_initial_2 = 315
num_asteroids = 48  # Number of asteroids in the ring
speed = 40  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
ship_position_1 = (width/5, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position_1[0] for angle in theta]
ast_x.extend([R_initial_2 * np.cos(angle) + ship_position_1[0] for angle in theta])
ast_y = [R_initial * np.sin(angle) + ship_position_1[1] for angle in theta]
ast_y.extend([R_initial_2 * np.sin(angle) + ship_position_1[1] for angle in theta])
init_angle = [np.rad2deg(np.arctan2(ship_position_1[1] - y, ship_position_1[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states_1 = [{"position": (x, y), "angle": angle, "speed": speed, 'size': 1} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + ship_position_2[0] for angle in theta]
ast_x.extend([R_initial_2 * np.cos(angle) + ship_position_2[0] for angle in theta])
ast_y = [R_initial * np.sin(angle) + ship_position_2[1] for angle in theta]
ast_y.extend([R_initial_2 * np.sin(angle) + ship_position_2[1] for angle in theta])
init_angle = [np.rad2deg(np.arctan2(ship_position_2[1] - y, ship_position_2[0] - x)) for x, y in zip(ast_x, ast_y)]

asteroid_states_2 = [{"position": (x, y), "angle": angle, "speed": speed, 'size': 1} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
avg_multi_ring_closing_both2 = Scenario(
    name="avg_multi_ring_closing_both2",
    asteroid_states=asteroid_states_1 + asteroid_states_2,
    ship_states=[{"position": ship_position_1, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=60,
)









# Parameters for the ring of asteroids
R_initial = 400  # Initial radius of the ring, large enough to enclose the ship
num_asteroids = 22  # Number of asteroids in the ring
speed = 40  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
center_position = (width/2, height/2)
ship_position = (width*4/10, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + center_position[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + center_position[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(center_position[1] - y, center_position[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states = [{"position": (x, y), "angle": angle, "speed": speed} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
adv_multi_ring_closing_both_inside = Scenario(
    name="adv_multi_ring_closing_both_inside",
    asteroid_states=asteroid_states,
    ship_states=[{"position": ship_position, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=60,
)










# Parameters for the ring of asteroids
R_initial = 400  # Initial radius of the ring, large enough to enclose the ship
num_asteroids = 26  # Number of asteroids in the ring
speed = 300  # Speed at which asteroids close in

# Ship's initial position (center of the screen)
center_position = (width/2, height/2)
ship_position = (width*4/10, height/2)
ship_position_2 = (width*6/10, height/2)

# Calculating initial positions and angles for the asteroids
theta = np.linspace(0, 2*np.pi, num_asteroids, endpoint=False)
ast_x = [R_initial * np.cos(angle) + center_position[0] for angle in theta]
ast_y = [R_initial * np.sin(angle) + center_position[1] for angle in theta]
init_angle = [np.rad2deg(np.arctan2(center_position[1] - y, center_position[0] - x)) for x, y in zip(ast_x, ast_y)]

# Creating asteroid states
asteroid_states = [{"position": (x, y), "angle": angle, "speed": speed, 'size': 2} for x, y, angle in zip(ast_x, ast_y, init_angle)]

# Creating the scenario
adv_multi_ring_closing_both_inside_fast = Scenario(
    name="adv_multi_ring_closing_both_inside_fast",
    asteroid_states=asteroid_states,
    ship_states=[{"position": ship_position, 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                 {"position": ship_position_2, 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3}],
    map_size=(width, height),
    time_limit=30,
)

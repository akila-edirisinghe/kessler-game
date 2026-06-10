import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import os, time, math

# Define the ranges of our variables
size_range = np.arange(1, 5, 1)
impact_time_range = np.arange(0,300, 1)  # Let's assume 100 as a practical upper limit for time of impact
turn_time_range = np.arange(0, 30, 1)    # Similarly, assume 100 as a practical upper limit for turn time
priority_range = np.arange(1, 11, 1)

# Create the fuzzy variables
size = ctrl.Antecedent(size_range, 'size')
impact_time = ctrl.Antecedent(impact_time_range, 'impact_time')
turn_time = ctrl.Antecedent(turn_time_range, 'turn_time')
priority = ctrl.Consequent(priority_range, 'priority')


# Define fuzzy membership functions for each variable
size['small'] = fuzz.trimf(size_range, [1, 1, 2])
size['medium'] = fuzz.trimf(size_range, [1, 2, 3])
size['large'] = fuzz.trimf(size_range, [2, 3, 4])
size['huge'] = fuzz.trimf(size_range, [3, 4, 4])

impact_time['imminent'] = fuzz.trimf(impact_time_range, [0, 0, 75])#75>100
impact_time['soon'] = fuzz.trimf(impact_time_range,     [0, 75, 150])#150>175
impact_time['later'] = fuzz.trimf(impact_time_range,    [75, 150, 200])#200>225
impact_time['distant'] = fuzz.trimf(impact_time_range,  [75, 300, 300])


turn_time['short'] = fuzz.trimf(turn_time_range,    [0, 0, 4])#5>7.5>3  maybe 4 as well. 
turn_time['moderate'] = fuzz.trimf(turn_time_range, [0, 4, 15])#15>20
turn_time['long'] = fuzz.trimf(turn_time_range,     [4, 15, 30])
turn_time['very_long'] = fuzz.trimf(turn_time_range,[15, 30, 30])

priority['very_low'] = fuzz.trimf(priority_range, [1, 1, 3])
priority['low'] = fuzz.trimf(priority_range,      [1, 3, 5])
priority['medium'] = fuzz.trimf(priority_range,   [3, 5, 7])
priority['high'] = fuzz.trimf(priority_range,     [5, 7, 9])
priority['very_high'] = fuzz.trimf(priority_range,[7, 9, 10])

# Define the fuzzy rules
rule1 = ctrl.Rule(size['huge'] & impact_time['imminent'] & turn_time['short'], priority['very_high'])
rule2 = ctrl.Rule(size['large'] & impact_time['imminent'] & turn_time['short'], priority['very_high'])
rule3 = ctrl.Rule(size['medium'] & impact_time['imminent'] & turn_time['short'], priority['very_high'])
rule4 = ctrl.Rule(size['small'] & impact_time['imminent'] & turn_time['short'], priority['very_high'])

rule5 = ctrl.Rule(size['huge'] & impact_time['soon'] & turn_time['moderate'], priority['very_high'])
rule6 = ctrl.Rule(size['large'] & impact_time['soon'] & turn_time['moderate'], priority['very_high'])
rule7 = ctrl.Rule(size['medium'] & impact_time['soon'] & turn_time['moderate'], priority['high'])
rule8 = ctrl.Rule(size['small'] & impact_time['soon'] & turn_time['moderate'], priority['high'])

rule9 = ctrl.Rule(size['huge'] & impact_time['later'] & turn_time['long'], priority['medium'])
rule10 = ctrl.Rule(size['large'] & impact_time['later'] & turn_time['long'], priority['low'])
rule11 = ctrl.Rule(size['medium'] & impact_time['later'] & turn_time['long'], priority['very_low'])
rule12 = ctrl.Rule(size['small'] & impact_time['later'] & turn_time['long'], priority['very_low'])

rule13 = ctrl.Rule(size['huge'] & impact_time['distant'] & turn_time['very_long'], priority['very_low'])
rule14 = ctrl.Rule(size['large'] & impact_time['distant'] & turn_time['very_long'], priority['very_low'])
rule15 = ctrl.Rule(size['medium'] & impact_time['distant'] & turn_time['very_long'], priority['very_low'])
rule16 = ctrl.Rule(size['small'] & impact_time['distant'] & turn_time['very_long'], priority['very_low'])

rule17 = ctrl.Rule(impact_time['imminent'] & turn_time['short'], priority['very_high'])
rule18 = ctrl.Rule(impact_time['imminent'] & turn_time['moderate'], priority['very_high'])
rule19 = ctrl.Rule(impact_time['imminent'] & turn_time['long'], priority['very_high'])#h>vh*
rule20 = ctrl.Rule(impact_time['imminent'] & turn_time['very_long'], priority['very_high'])#h>vh*

rule21 = ctrl.Rule(impact_time['soon'] & turn_time['short'], priority['very_high'])
rule22 = ctrl.Rule(impact_time['soon'] & turn_time['moderate'], priority['very_high'])
rule23 = ctrl.Rule(impact_time['soon'] & turn_time['long'], priority['very_high'])
rule24 = ctrl.Rule(impact_time['soon'] & turn_time['very_long'], priority['very_high'])

rule25 = ctrl.Rule(impact_time['later'] & turn_time['short'], priority['high'])#h > vh* > h
rule26 = ctrl.Rule(impact_time['later'] & turn_time['moderate'], priority['high'])#m>h*
rule27 = ctrl.Rule(impact_time['later'] & turn_time['long'], priority['very_low'])#l>vl*
rule28 = ctrl.Rule(impact_time['later'] & turn_time['very_long'], priority['very_low'])

rule29 = ctrl.Rule(impact_time['distant'] & turn_time['short'], priority['high']) #vh>h
rule30 = ctrl.Rule(impact_time['distant'] & turn_time['moderate'], priority['high'])#vh>h
rule31 = ctrl.Rule(impact_time['distant'] & turn_time['long'], priority['very_low'])
rule32 = ctrl.Rule(impact_time['distant'] & turn_time['very_long'], priority['very_low'])





# Create the control system and simulation
priority_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, 
                                    rule9, rule10, rule11, rule12, rule13, rule14, rule15, rule16, rule17, rule18, rule19, rule20,rule21, rule22, rule23, rule24, rule25, rule26, rule27, rule28, rule29, rule30, rule31, rule32])
priority_simulation = ctrl.ControlSystemSimulation(priority_ctrl)

# Example usage
def get_priority(size_val, impact_time_val, turn_time_val):
    priority_simulation.input['size'] = size_val
    priority_simulation.input['impact_time'] = impact_time_val
    priority_simulation.input['turn_time'] = turn_time_val
    priority_simulation.compute()
    return priority_simulation.output['priority']


# Test the system with some example inputs
#print(get_priority(4, 10, 10))  # Example input: huge size, imminent impact, short turn time
#print(get_priority(3, 25, 30))  # Example input: large size, soon impact, moderate turn time
print(get_priority(1, math.inf, 25))

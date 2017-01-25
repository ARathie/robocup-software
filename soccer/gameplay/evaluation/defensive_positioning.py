import main
import robocup
import math
import constants
import evaluation.ball
# Defensive positioning
# 2 main schools of thought
# Man to man coverage
# Zone coverage

# A mix of two will be the best
# We need to figure out good algorithms to find a position for each robot

# Zone defense works on keep robots somewhat spread for the incoming cross pass
# This also helps with a counter attack as one robot is free on the side of the field

# With defense, you want to push the opponents outside and cover the middle and any cross passes
# In robocup, covering crosses is a little harder due to how quickly the ball moves in comparison
# to the robots themselves.
# With that, a stronger angle defense is needed.
# Angle defense is needed to close distance to cover a wider angle
# Figure out the mathimatical relationship between distance and angle coverage
# I would imagine it is somewhat of a power / exp situation

# (1) Next, figure out a quick way to estimate the shot chance of a robot on the opponent side
# This is due to win_eval is very slow (From what I have heard)

# Can be estimated most likely with some sort of distance function and delta for the robots in the way

# Zones will need to be figured out physically until we can test multiple different ones against each other
# One basic system would be to just do a third of the field on either side of the center line

# (2) Defense wise, the robots can only pass form their mouth
# we can get that angle as well as the angle of their approach to do some early estimations
# of pass / shot direction
# A complementary filter on those two shouldn't be too hard
# Mostly likely weight towards the predicted mouth angle a little bit more (use at the very least velocity, hopefully acceleration too)

# (3) Next we need to get a list of robot positions that we should move into
# This would require figureing out their best pass / shot posiitions
# Move to block both their current positions
# As well stay in positions to block future pass positions
# Use space_coeff to find large pockets of open space and good shots from that positions
# Only one need to defend there

# (4) Area  defense will be used for zones further away from the ball
# We ened to cover as many zones as possible further away so finding a good area for each robot away from the action is needed
# To do this, we need to find where there is a significant amount of space
# What the best angle is from the ball
# And any nearby robots that we will need to move into defense for
# We can find a good position to pass to (using eight furthest time if multiple points are needed to be covered
# or just the center of the group if they are somewhat close)
# We also need to find the closest bot that is incoming that we need to cover
# Decide if covering the pass or the shot is better
# Minimize risk to find the best
# (5) Risk can be considered the closeness of another robot inc to the shot / pass location and their possible leathality
# in that position
# Risk must take into account the direction of attack onto the ball
# As well as the defense in those positions

###############################
## Most likely needed functions
###############################
#
#
# (1) estimate_kick_block_percent(point, our_pos[])
# (2) predict_kick_direction(robot)
# (3) best_defense_positions(ball_pt)
# (4) create_area_defense_zones()
# (5) esteimate_risk_score(pt)

## Estimates the chance a kick will be blocked
#
# @param kick_point: Point at which we will kick from
# @param recieve_point: Point at which they are kicking to
# @param blocking_robots[]: list of robots that we should estimate the block for
# @return A percentage chance of block
def estimate_kick_block_percent(kick_point, recieve_point, blocking_robots=main.their_robots()):

    # 1. For each robot, get their position in polar coords
    #       in reference to the kick_point -> recieve_point vector
    # 2. Create a set of rays moving out from the kick point
    # 3. Use a kernal function to estimate the chance it will
    #       intercept the ball moving along that ray
    # 4. Take the minimum interception estimate along that ray
    # 5. Throw all the rays together scaled by their distance from the target angle

    blocks = []
    kick_direction = (recieve_point - kick_point)
    kick_angle = math.atan2(kick_direction.y, kick_direction.x)
    max_ball_vel = 8

    # Convert all robot positions to polar with zero being the kick direction
    # TODO: Use velocity / accel with robots to predict where they will be based on
    # their distance from the robot
    for bot in blocking_robots:
        if bot.visible and bot:
            pos = bot.pos
            block_direction = (pos - kick_point)
            dist = block_direction.mag()
            angle = math.atan2(block_direction.y, block_direction.x) - kick_angle
            future_bot_pos = bot.pos + bot.vel * ((bot.pos - main.ball().pos).mag() / max_ball_vel)
            pos = future_bot_pos

            # Kill any that are over pi/2 away
            # Kill any that are too far away (TOOD: Include this in the function)
            if (math.fabs(angle) < math.pi / 2 and dist > 0 and dist < 2*kick_direction.mag()):
                blocks.extend([(angle, dist)])

    # Quit early if there is nobody near to defend
    if (len(blocks) == 0):
        return 1

    # Standard deviation basically
    half_kick_width = 0.1*math.pi
    # Resolution of the estimation
    num_of_estimates = 16
    # controls distribution of values overall (Higher the number, the less sensitive)
    overall_sens = 2
    # Constrols how much to decrease for further away values (Lower the number, the more it decreases)
    distance_sens = -1/7
    # How much to scale the outer lines by
    min_offset_scale = .1

    total = 0
    max_total = 0
    line_offset = -half_kick_width
    inc = 2 * half_kick_width / num_of_estimates

    # For each radial line (Multiplies by 1.01 because of float errors)
    while line_offset <= half_kick_width*1.01:
        subtotal = []
        # For each blocking robot (Angle, Dist)
        for bot  in blocks:
            delta_angle = bot[0] - line_offset

            # Produces a u based on distance / angle
            u = math.sin(delta_angle) * bot[1] * overall_sens * math.exp(bot[1] * distance_sens)
            u = min(1, u)
            u = max(-1, u)

            # Add the kernel estimate to the list
            subtotal.extend([1 - max(pow((1-pow(u,2)), 3), 0)])

        # Decrease the impact of lines further away from the center
        line_offset_scale = 1 - (math.fabs(line_offset) / ( (1 + min_offset_scale) * half_kick_width))

        # Uses the min because we only care about the closest robot to blocking
        # Each line
        total += min(subtotal) * line_offset_scale
        max_total += line_offset_scale
        line_offset += inc

    return total / max_total


## Predicts the impending kick direction based on the orientation of the robot and the
#  angle of approach
#
# @param robot: The robot which we want to estimate
# @return Angle of most likely kick
def predict_kick_direction(robot):
    angle = robot.angle
    pos = robot.pos
    angle_vel = robot.angle_vel

    # Use distance from bot to ball to predict time it takes to intercept
    # Calculates direct robot to future ball position
    inst_ball_time = evaluation.ball.time_to_ball(robot)
    future_ball_pos = evaluation.ball.predict(main.ball().pos, main.ball().vel, inst_ball_time)
    direction = (future_ball_pos - pos).normalized()
    # TODO: Make sure the angle is in  the correct direction
    ball_angle_predict = direction.angle()

    # Predict the robot direction based on angular velocity and angle
    robot_angle_predict = angle + angle_vel*inst_ball_time

    # TODO: Change to 0.7 before running outside of the test function
    filter_coeff = 0
    return filter_coeff * robot_angle_predict + (1 - filter_coeff) * ball_angle_predict


## Creates a zone that may cause a risk in the future
#  Based off the...
#   Risk score in that position
#   Adviailbity of opponent robots to reach that point
#   Space in that area
#
# @return List of the top 2 rectangle zones and their scores
def create_area_defense_zones():
    pass
    # Find out areas with a strong pass chance (Estimate_risk_score)
    # Weight space significantly higher, decrease areas away from center
    # Increase weight for areas that other robots can move into easily
    # (Create a cone away from the goal with robot distance being the weighted value)
    #
    # Merge areas that are further away from the ball along the same angle

## Estimates how dangerous an enemy robot can be at a certain point
#  Takes pass / shot and time to execute on ball into account
#
# @param pos: Position in which to estimate score at
# @return Risk score at that point
def estimate_risk_score(pos):
    our_goal = robocup.Point(0, 0)
    max_time = 1
    # TODO: Double check this constant
    max_ball_vel = 8 # m/s per the rules IIRC
    est_turn_vel = 4 # rad/s per a random dice roll (Over estimates oppnents abilities)

    # Invert both scores as kick_block produces a percentage that it is blocked
    # We want how likely to succed
    pass_score = estimate_kick_block_percent(main.ball().pos, pos, main.our_robots())
    shot_score = estimate_kick_block_percent(pos, our_goal, main.our_robots())

    # Dist to ball
    ball_pos_vec = pos - main.ball().pos
    dist = ball_pos_vec.mag()

    # Closest opp robot
    closest_opp_bot = evaluation.opponent.get_closest_opponent(main.ball().pos)
    delta_angle = (ball_pos_vec.angle() - predict_kick_direction(closest_opp_bot))
    delta_angle = math.atan2(math.sin(delta_angle), math.cos(delta_angle))
    # Underestimates max time to execute on ball
    # Assumes perfect opponent
    time = dist/max_ball_vel + math.fabs(delta_angle)/est_turn_vel
    # Limits to max time so we can invert it later on
    time = min(time, max_time)

    # Shot only matters if its a good pass
    # Add pass back in for checking if pass is good (while shot is not)
    # Multiple it all by time to scale closer robots to ball higher
    return (shot_score * pass_score + pass_score) * (max_time - time)

## Decides where to move the three robots
#
# @return List of the 3 defensive positions
def find_defense_positions():
    pass
    # The bread and butter of this whole thing
    # Returns the list of best defense positions (TOP N Amounts)

    # Take in a list of area defense zones (create_area_defense_zones)
    # Produce a list of the highest threat robots (estimate_risk_score(robot_pos))

    # Grab the closest robot to the ball
    # Approach the ball slow-ish but be very sensitive to side to side movement
    # Block goal on approach

    # Move second robot to block pass / second robot shot
    # TODO: Decide whether it is better to blcok pass or block shot
    # Shot is lower risk to block
    # Pass is higher reward to block
    # Can base on score as well previous pass block success rates
    # Can also position to be able to get both
    # Mirror movements of other robot

    # Move third to defend the area defense
    # or defend the pass / shot of the last robot
    # Best would be to find best position to defend both

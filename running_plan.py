def gather_information_from_user(question):
    """Questions to gather information from the user in order to generate their 
    running plan.
    """
    print question
    response = raw_input("> ")
    return float(response)

def calculate_mileage_increment_per_week(current_ability, 
                                         goal_distance, 
                                         weeks_to_goal):
    """Calculates the mileage runners will need to increment their long run by
    each week.
    """
    increment = (goal_distance - current_ability) / weeks_to_goal
    return increment

def round_quarter(x):
    return round(x * 4) / 4.0

def build_plan(weeks_to_goal, current_ability, goal_distance, increment):
    """Builds a dictionary with how much user needs to run each day leading up
    to their goal.
    """

    weekly_plan = {}

    for week in range(int(weeks_to_goal)):
        weekly_plan[week] = {}
        weekly_plan[week]['Tues'] = 0
        weekly_plan[week]['Fri'] = 0
        if week == 0:
            long_run = current_ability
        elif week == weeks_to_goal:
            long_run = goal_distance
        else: 
            long_run = float('%.2f' % (current_ability + (week * increment)))   
        weekly_plan[week]['Sun'] = round_quarter(long_run)
        weekly_plan[week]['Mon'] = round_quarter(long_run / 2)
        weekly_plan[week]['Wed'] = round_quarter(long_run / 4)
        weekly_plan[week]['Thurs'] = round_quarter(long_run / 2)
        weekly_plan[week]['Sat'] = round_quarter(long_run / 4)

    return weekly_plan

def build_plan_alternate(weeks_to_goal, current_ability, goal_distance, increment):
    """Generates plan using a list of lists, where each internal list includes
    all the runs for the week at that index.

    Long runs are incremented by the increment each week.
    Mid-week runs are 10 percent or 20 percent of the long-run.
    There are two off days with zero mileage. 

    """

    weekly_plan = []

    for week in range(int(weeks_to_goal)):
        week_runs = []

        if week == 0:
            long_run = current_ability
        elif week == weeks_to_goal:
            long_run = goal_distance
        else: 
            long_run = float('%.2f' % (current_ability + (week * increment)))
        
        week_runs.append(round_quarter(long_run / 2))  # Monday
        week_runs.append(0)  # Tuesday
        week_runs.append(round_quarter(long_run / 4))  # Wednesday
        week_runs.append(round_quarter(long_run / 2))  # Thursday
        week_runs.append(0)  # Friday
        week_runs.append(round_quarter(long_run / 4))  # Saturday
        week_runs.append(round_quarter(long_run))  # Sunday

        weekly_plan.append(week_runs)

    return weekly_plan


def print_alternate_plan(weekly_plan):
    """Prints out the running plan in a nice format."""
    for i in range(len(weekly_plan)):
        print "\n\nWeek %s" % i
        print 'Mon\t', 'Tues\t', 'Wed\t', 'Thurs\t', 'Fri\t', 'Sat\t', 'Sun\t'
        for day in weekly_plan[i]:
            print "%s \t"  % day, 


def print_plan(weekly_plan):
    """Prints out the running plan in a nice format."""

    for week in sorted(weekly_plan.keys()):
        print '\nWeek %s' % week
        print 'Mon\t', 'Tues\t', 'Wed\t', 'Thurs\t', 'Fri\t', 'Sat\t', 'Sun\t'
        print "%s \t %s \t %s \t %s \t %s \t %s \t %s \t" % (weekly_plan[week]['Mon'], 
                                                             weekly_plan[week]['Tues'], 
                                                             weekly_plan[week]['Wed'], 
                                                             weekly_plan[week]['Thurs'], 
                                                             weekly_plan[week]['Fri'], 
                                                             weekly_plan[week]['Sat'], 
                                                             weekly_plan[week]['Sun'])


def generate_plan():
    """Uses informaiton from user to generate their running plan.
    These will be entered using dropdown menus in the actual application to help
    avoid user error.
    """
    current_ability = gather_information_from_user("How many miles can you currently run without stopping?")

    goal_distance = gather_information_from_user("What is the goal distance you would like to run?")

    weeks_to_goal = gather_information_from_user("How many weeks are there until your running goal?")

    increment = round_quarter(calculate_mileage_increment_per_week(current_ability, 
                                                     goal_distance, 
                                                     weeks_to_goal))

    if increment > 1:
        print """We're sorry, but it will be very difficult for you to achieve 
        your goal in the time that you have. Please consider a race that 
        will provide you with more weeks for training."""

    if (goal_distance * .8) <= current_ability:
        print """We believe that you already have the ability to achieve your goal. 
        If you would like to try a more difficult race, or a faster time, 
        we would be happy to assist you!"""

    weekly_plan = build_plan_alternate(weeks_to_goal, current_ability, goal_distance, increment)
    print_alternate_plan(weekly_plan)

    # weekly_plan = build_plan(weeks_to_goal, current_ability, goal_distance, increment)
    # print_plan(weekly_plan)

generate_plan()

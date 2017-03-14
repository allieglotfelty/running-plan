def gather_information_from_user(question):
    """Questions to gather information from the user in order to generate their 
    running plan.
    """
    print question
    response = raw_input("> ")
    return response

def calculate_mileage_increment_per_week(current_ability, 
                                         goal_distance, 
                                         weeks_to_goal):
    """Calculates the mileage runners will need to increment their long run by
    each week.
    """
    increment = (goal_distance - current_ability) / weeks_to_goal
    return increment

def create_weeks(weeks_to_goal):
    """Creates the training weeks to outline the plan."""
    
    day_of_the_week_dictionary = {'Mon': 0,
                                  'Tues': 0,
                                  "Wed": 0,
                                  "Thurs": 0,
                                  "Fri": 0,
                                  "Sat": 0,
                                  "Sun": 0
                                  }

    weeks = {}
    for week in range(int(weeks_to_goal)):
        weeks[week] = {'Mon': 0,'Tues': 0, "Wed": 0, "Thurs": 0, "Fri": 0, "Sat": 0, "Sun": 0}
    return weeks

def round_quarter(x):
    return round(x * 4) / 4.0

def generate_plan():
    """Uses informaiton from user to generate their running plan."""
    current_ability = int(gather_information_from_user("How many miles can you currently run without stopping?"))

    goal_distance = float(gather_information_from_user("What is the goal distance you would like to run?"))

    weeks_to_goal = int(gather_information_from_user("How many weeks are there until your running goal?"))

    increment = round_quarter(calculate_mileage_increment_per_week(current_ability, 
                                                     goal_distance, 
                                                     weeks_to_goal))

    if increment > 1:
        print "We're sorry, but it will be very difficult for you to achieve"
        print "your goal in the time that you have. Please consider a race that"
        print "will provide you with more weeks for training."

    if (goal_distance * .8) <= current_ability:
        print "We believe that you already have the ability to achieve your goal."
        print "If you would like to try a more difficult race, or a faster time,"
        print "we would be happy to assist you!"

    print "Weekly long runs will increase by %s each week." % increment
    print "You are currently able to run %s miles at once." % current_ability
    print "You have %s weeks until your race." % int(weeks_to_goal)
    print "You are working towards a goal of %s miles." % goal_distance

    weekly_plan = create_weeks(weeks_to_goal)

    for week in range(weeks_to_goal):
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

    
generate_plan()

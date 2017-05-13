$(document).ready(function() {

  "use strict";

  $("#plan-name-change-box").hide();
  $("#warning-complete-all-fields").hide();
  $("#download-to-excel").hide();
  $("#sign-up").hide();
  $("#options-below").hide();


  // Displays running plan on homepage
  function showPlanResults(results) {
    var runPlan = results;
    console.log(runPlan);
    if ('response' in runPlan) {
      $('#warning-complete-all-fields').show().delay(5000).queue(function() {
        $(this).hide();
      });
    } else {
    $("#run-info-chart").empty();
    for (var week in runPlan) {
      $("#run-info-chart").append('<tr>');
      $("#run-info-chart").append('<td class="week-number">Week ' + week + '</td>');
      var weeklyPlan = runPlan[week];
      for (var date in weeklyPlan) {
        var newDate = new Date(date);
        newDate.setDate(newDate.getDate() + 1);
        var month = (newDate.getMonth()+1)+ "";
        var day = newDate.getDate();
        if (weeklyPlan[date]) {
          var distance = weeklyPlan[date].toFixed(1);
          $("#run-info-chart").append('<td class="run-event"><span class="distance">' + distance + '</span><br>miles on ' + month + "/" + day  + '</td>');
          // $("#run-info-chart").append('<td>  ' + date + '<br><br>  ' + weeklyPlan[date] + ' miles</td>');
        } else {
          $("#run-info-chart").append('<td class="off-day run-event"><span class="distance">Off day!</span><br>' + month + "/" + day + '</td>');
        }
      }
      $("#run-info-chart").append('</tr>');
    }
    $("#plan-calendar").removeAttr("hidden");
    $("#generate-plan").attr('value', 'Update Plan');
    $("#download-to-excel").show();
    $("#sign-up").show();
    $("#warning-complete-all-fields").empty();
    }
  }

  // Ajax call to compute running plan based on user input
  function getPlanResults(evt) {
    evt.preventDefault();
    var currentAbility = $("#current-ability").val();
    var goalDistance = $("#goal-distance").val();
    var goalDate = $("#goal-date").val();
    $.get("/plan.json", {"current-ability": currentAbility,
                          "goal-distance": goalDistance,
                          "goal-date": goalDate}, showPlanResults);
    }

  // Configures downloadable version of running plan
  function getPlanResultsForDownload(evt) {
    var currentAbility = $("#current-ability").val();
    var goalDistance = $("#goal-distance").val();
    var goalDate = $("#goal-date").val();

    // Routes to /download (download? below) with the following values from the DOM
    window.location = 'download?current-ability=' + currentAbility +
                      '&goal-distance=' + goalDistance + '&goal-date=' +
                      goalDate;
  }

  // Ajax call to update running calendar as completed on click
  $(".run").on("click", function() {
    var runId = $(this).attr('id');
    if ($(this).hasClass("incompleted-run")) {
      $(this).removeClass("incompleted-run").addClass("completed-run");
      $.post("/update-run.json", {'run-id': runId}, function(results) {
        $("#total-miles").html(results['total_miles_completed']);
        $("#total-workouts").html(results['total_workouts_completed']);
      });
    } else if ($(this).hasClass("completed-run")) {
      $(this).addClass("incompleted-run").removeClass("completed-run");
      $.post("/update-run-incomplete.json", {'run-id': runId}, function(results) {
        $("#total-miles").html(results['total_miles_completed']);
        $("#total-workouts").html(results['total_workouts_completed']);
      });
    }
  });

  // Displays prompt to fill in timezone and start time if user clicks opt into
  // Google Calendar
  $('input[type=checkbox][name=opt-gcal]').change(function() {
    if ($(this).is(":checked")) {
      $("#options-below").show();
    } else {
      $("#options-below").hide();
    }
  });

  // Allows user to updated their Running Plan Name
  function planNameUpdated(results) {
    $("#plan-name-change-box").hide();
    var title = $("#plan-name-title");
    title.html(results['newName']);
  }

  function updatePlanName(evt) {
    evt.preventDefault();
    var newName = $("#new-plan-name").val();
    var planId = $("#plan-id").attr('name');
    console.log(planId);
    $.post("/update-plan-name.json", {"newName": newName, "planId": planId}, planNameUpdated);
  }

  function showUpdatePlanNameBox() {
    $("#plan-name-change-box").show();
  }

  $("#generate-plan").on('click', getPlanResults);
  $("#download-to-excel").on('click', getPlanResultsForDownload);
  $("#update-plan-name").on('click', showUpdatePlanNameBox);
  $("#plan-name-change-box").on('submit', updatePlanName);


});

// Checkbox feature of checking off runs. Less attractive UI thank clicking box itself:
  // $('input:checkbox.workout').change(function() {
  //     var runId = $(this).attr('id');
  //     if ($(this).is(":checked")) {
  //         $(this).attr("checked", true);
  //         $(this).toggleClass("completed-run");
  //         $.post("/update-run.json", {'run-id': runId}, function(results) {
  //           alert("Congrats on completing a run!");
  //           $("#total-miles").html(results['total_miles_completed']);
  //           $("#total-workouts").html(results['total_workouts_completed']);
  //         });
  //     } else {
  //         $(this).attr("checked", false);
  //         $.post("/update-run-incomplete.json", {'run-id': runId}, function(results) {
  //           alert("We have removed this run from your total!");
  //           $("#total-miles").html(results['total_miles_completed']);
  //           $("#total-workouts").html(results['total_workouts_completed']);
  //         });
  //     }
  //   });


// Alternative way to capture user timezone and start time for Google Calendar. 
// Less friendly UI and disconnected process.
  // function getEventInfoForGoogleCal(evt) {
  //   evt.preventDefault();
  //   var timezone = $("#time-zone").val();
  //   console.log(timezone);
  //   var time = $("#cal-run-start-time").val();
  //   console.log(time);
  //   $("#cal-run-start-time").attr('selected', 'selected');
  //   $("#time-zone").attr('selected', 'selected');
  //   $.post("/add-to-google-calendar", {"time-zone": timezone,
  //                                     "cal-run-start-time": time}, function() {
  //                                       window.location.replace('/dashboard');
  //                                     });
  // }

  // function timezoneUpdated(results) {
  //   console.log(results.message);
  // }

  // function getTimezoneForGoogleCal(evt) {
  //   var timezone = $("#time-zone").val();
  //   console.log(timezone);
  //   $("#time-zone").attr('selected', 'selected');
  //   $.get("/add-timezone-to-session", {"time-zone": timezone}, timezoneUpdated);
  // }

  // function startTimeUpdated(results) {
  //   console.log(results.message);
  // }

  // function getStartTimeForGoogleCal(evt) {
  //   var time = $("#cal-run-start-time").val();
  //   console.log(time);
  //   $("#time-zone").attr('selected', 'selected');
  //   $.get("/add-start-time-to-session", {"cal-run-start-time": time}, startTimeUpdated);
  // }


// Alternative way to capture user information for opting into text message reminders.
// Less user friendly and unattractive UI
  // function showOptIntoTextsForm() {
  //   $("#opt-in-for-texts-form").show();
  // }

  // function optInUpdated(results) {
  //   $("#opt-in-for-texts-form").hide();
  //   $("#opt-into-texts-button").hide();
  //   $("#opt-out-of-texts-button").show();
  // }

  // function updatePhone(evt) {
  //   evt.preventDefault();
  //   var phone = $("#phone-number").val();
  //   var runnerId = $("#runner-id").attr('name');
  //   $.post("/opt-into-text-reminders.json", {"phone": phone, "runnerId": runnerId}, optInUpdated);
  // }

  // function showOptInButton(results) {
  //   $("#opt-out-of-texts-button").hide();
  //   $("#opt-into-texts-button").show();
  //   console.log(results);
  // }

  // function optOutOfTexts(evt) {
  //   var runnerId = $("#runner-id").attr('name');
  //   $("#opt-out-of-texts-button").hide();
  //   $("#opt-into-texts-button").show();
  //   $.post("/opt-out-of-text-reminders.json", {"runnerId": runnerId}, showOptInButton);

  // }

// Alternative way to capture user information for opting into email reminders.
// Less user friendly and unattractive UI

  // function optOutOfEmails(evt) {
  //   $("#you-will-no-longer-receive-emails").show().delay(5000).queue(function() {
  //       $(this).hide();
  //     });
  //   $("#opt-out-of-email-button").hide();
  //   $("#opt-into-email-button").show();
    
  // }
   
  // function updateOptInToEmail(results) {
  //   if (results['response'] === 'yes') {
  //     $("#your-email-subscription-has-been-updated").show().delay(5000).queue(function() {
  //       $(this).hide();
  //     });
  //     $("#opt-out-of-email-button").show();
  //     $("#opt-into-email-form").hide();
  //     $("#opt-into-email-button").hide();

  //   } else {
  //     $("#opt-into-email-form").hide();
  //     $("#opt-into-email-button").show();
  //   }
  // }

  // function updateSubscription(evt) {
  //   evt.preventDefault();
  //   var subscription = $("input[name=email-sub]:checked").val();
  //   var runnerId = $("#runner-id").attr("name");
  //   $.post("/opt-into-email-reminders.json", {"subscription": subscription,
  //                                             "runnerId": runnerId},
  //                                             updateOptInToEmail);
  // }

  // function showOptIntoEmailForm() {
  //   $("#opt-into-email-form").show();
  // }

 

  // $("#cal-run-start-time").change(getStartTimeForGoogleCal);
  // $("#time-zone").change(getTimezoneForGoogleCal);

  // $("#opt-into-texts-button").on('click', showOptIntoTextsForm);
  // $("#opt-in-for-texts-form").on('submit', updatePhone);
  // $("#opt-out-of-texts-button").on('click', optOutOfTexts);

  // $("#opt-into-email-button").on('click', showOptIntoEmailForm);
  // $("#opt-into-email-form").on('submit', updateSubscription);
  // $("#opt-out-of-email-button").on('click', optOutOfEmails);

  // $("#add-to-google-calendar-form").on('submit', getEventInfoForGoogleCal);

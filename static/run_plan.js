$(document).ready(function() {

  "use strict";

  $("#plan-name-change-box").hide();
  $("#warning-complete-all-fields").hide();
  $("#opt-in-for-texts-form").hide();
  // $("#opt-out-of-texts-button").hide();
  $("#opt-into-email-form").hide();
  $("#your-email-subscription-has-been-updated").hide();
  $("#you-will-no-longer-receive-emails").hide();

  function showPlanResults(results) {
    var runPlan = results;
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
          // var newDate = new Date(date);
          // var month = (newDate.getMonth()+1)+ "";
          // var day = newDate.getDate();
          if (weeklyPlan[date]) {
            // $("#run-info-chart").append('<td>  ' + month + "/" + day + '<br><br>  ' + weeklyPlan[date] + ' miles</td>');
            $("#run-info-chart").append('<td>  ' + date + '<br><br>  ' + weeklyPlan[date] + ' miles</td>');
          } else {
            // $("#run-info-chart").append('<td class="off-day">  ' + month + "/" + day + '<br><br>  off day</td>');
            $("#run-info-chart").append('<td class="off-day">  ' + date + '<br><br>  off day</td>');
          }
        }
        $("#run-info-chart").append('</tr>');
      }
      $("#plan-calendar").removeAttr("hidden");
      $("#generate-plan").attr('value', 'Update Plan');
      $("#download-to-excel").removeAttr("hidden");
      $("#sign-up").removeAttr("hidden");
      $("#warning-complete-all-fields").empty();
    }
  }

  function getPlanResults(evt) {
    evt.preventDefault();
    var currentAbility = $("#current-ability").val();
    var goalDistance = $("#goal-distance").val();
    var goalDate = $("#goal-date").val();
    $.post("/plan.json", {"current-ability": currentAbility,
                          "goal-distance": goalDistance,
                          "goal-date": goalDate}, showPlanResults);
    }

  function getPlanResultsForDownload(evt) {
    var currentAbility = $("#current-ability").val();
    var goalDistance = $("#goal-distance").val();
    var goalDate = $("#goal-date").val();

    // Routes to /download (download? below) with the following values from the DOM
    window.location = 'download?current-ability=' + currentAbility +
                      '&goal-distance=' + goalDistance + '&goal-date=' +
                      goalDate;
  }

  $('input:checkbox').change(
    function(){
      var runId = $(this).attr('id');
      if ($(this).is(":checked")) {
          $(this).attr("checked", true);
          $.post("/update-run.json", {'run-id': runId}, function(results) {
            alert("Congrats on completing a run!");
            $("#total-miles").html(results['total_miles_completed']);
            $("#total-workouts").html(results['total_workouts_completed']);
          });
      } else {
          $(this).attr("checked", false);
          $.post("/update-run-incomplete.json", {'run-id': runId}, function(results) {
            alert("We have removed this run from your total!");
            $("#total-miles").html(results['total_miles_completed']);
            $("#total-workouts").html(results['total_workouts_completed']);
          });
      }
    });

  function addEventsToGoogleCal(results) {
    console.log("Events added to Google Calendar");
  }


  function getEventInfoForGoogleCal(evt) {
    evt.preventDefault();
    var timezone = $("#time-zone").val();
    console.log(timezone);
    var time = $("#cal-run-start-time").val();
    console.log(time);
    $("#cal-run-start-time").attr('selected', 'selected');
    $("#time-zone").attr('selected', 'selected');
    $.post("/add-to-google-calendar", {"time-zone": timezone,
                                      "cal-run-start-time": time}, function() {
                                        window.location.replace('/dashboard');
                                      });
  }

  function timezoneUpdated(results) {
    console.log(results.message);
  }

  function getTimezoneForGoogleCal(evt) {
    var timezone = $("#time-zone").val();
    console.log(timezone);
    $("#time-zone").attr('selected', 'selected');
    $.get("/add-timezone-to-session", {"time-zone": timezone}, timezoneUpdated);
  }

  function startTimeUpdated(results) {
    console.log(results.message);
  }

  function getStartTimeForGoogleCal(evt) {
    var time = $("#cal-run-start-time").val();
    console.log(time);
    $("#time-zone").attr('selected', 'selected');
    $.get("/add-start-time-to-session", {"cal-run-start-time": time}, startTimeUpdated);
  }


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

  function showOptIntoTextsForm() {
    $("#opt-in-for-texts-form").show();
  }

  function optInUpdated(results) {
    $("#opt-in-for-texts-form").hide();
    $("#opt-into-texts-button").hide();
    $("#opt-out-of-texts-button").show();
  }

  function updatePhone(evt) {
    evt.preventDefault();
    var phone = $("#phone-number").val();
    var runnerId = $("#runner-id").attr('name');
    $.post("/opt-into-text-reminders.json", {"phone": phone, "runnerId": runnerId}, optInUpdated);
  }

  function showOptInButton(results) {
    $("#opt-out-of-texts-button").hide();
    $("#opt-into-texts-button").show();
    console.log(results);
  }

  function optOutOfTexts(evt) {
    var runnerId = $("#runner-id").attr('name');
    $("#opt-out-of-texts-button").hide();
    $("#opt-into-texts-button").show();
    $.post("/opt-out-of-text-reminders.json", {"runnerId": runnerId}, showOptInButton);

  }

  function showUpdatePlanNameBox() {
    $("#plan-name-change-box").show();
  }

  function optOutOfEmails(evt) {
    $("#you-will-no-longer-receive-emails").show().delay(5000).queue(function() {
        $(this).hide();
      });
    $("#opt-out-of-email-button").hide();
    $("#opt-into-email-button").show();
    
  }
   
  function updateOptInToEmail(results) {
    if (results['response'] === 'yes') {
      $("#your-email-subscription-has-been-updated").show().delay(5000).queue(function() {
        $(this).hide();
      });
      $("#opt-out-of-email-button").show();
      $("#opt-into-email-form").hide();
      $("#opt-into-email-button").hide();

    } else {
      $("#opt-into-email-form").hide();
      $("#opt-into-email-button").show();
    }
  }

  function updateSubscription(evt) {
    evt.preventDefault();
    var subscription = $("input[name=email-sub]:checked").val();
    var runnerId = $("#runner-id").attr("name");
    $.post("/opt-into-email-reminders.json", {"subscription": subscription,
                                              "runnerId": runnerId},
                                              updateOptInToEmail);
  }

  function showOptIntoEmailForm() {
    $("#opt-into-email-form").show();
  }

  // For workout chart
  var options = { responsive: true };

  var ctx_donut = $("#donutChart").get(0).getContext("2d");

  $.get("/workout-info.json", displayWorkoutInfo);

  function displayWorkoutInfo(data) {
    var myDonutChart = new Chart(ctx_donut, {
                                            type: 'doughnut',
                                            data: data,
                                            options: options
                                          });
    $('#donutLegend').html(myDonutChart.generateLegend());
  }



  $("#cal-run-start-time").change(getStartTimeForGoogleCal);
  $("#time-zone").change(getTimezoneForGoogleCal);
  $("#planning-form").on('submit', getPlanResults);
  $("#download-to-excel").on('click', getPlanResultsForDownload);
  // $("#planning-form").on('submit', displaySignUpAndSaveButton);
  // $("#planning-form").on('submit', displayCalendar);
  // $("#planning-form").change(getPlanResults);
  $("#update-plan-name").on('click', showUpdatePlanNameBox);
  $("#plan-name-change-box").on('submit', updatePlanName);
  $("#opt-into-texts-button").on('click', showOptIntoTextsForm);
  $("#opt-in-for-texts-form").on('submit', updatePhone);
  $("#opt-out-of-texts-button").on('click', optOutOfTexts);

  $("#opt-into-email-button").on('click', showOptIntoEmailForm);
  $("#opt-into-email-form").on('submit', updateSubscription);
  $("#opt-out-of-email-button").on('click', optOutOfEmails);

  // $("#add-to-google-calendar-form").on('submit', getEventInfoForGoogleCal);

});
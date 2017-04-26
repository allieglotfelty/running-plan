$(document).ready(function() {

  "use strict";

 // For workout chart
  var workoutOptions = {
                        responsive: true,
                        title: {
                                display: false,
                                text: 'Total Workouts Completed',
                                fontSize: 18,
                                },
                        legend: {
                                 display: false,
                                 position: 'right',
                                }
                        };
  var ctx_donut = $("#donutChartWorkouts");

  function displayWorkoutInfo(data) {
    var myDonutChart = new Chart(ctx_donut, {
                                            type: 'doughnut',
                                            data: data,
                                            options: workoutOptions
                                          });
    // $('#donutLegend').html(myDonutChart.generateLegend());
  }




  // For mileage chart
  var mileageOptions = {
                        responsive: true,
                        title: {
                                display: false,
                                text: 'Total Miles Completed'
                                },
                        legend: {
                                 display: false,
                                 position: 'right',
                                }
                      };
  var ctx_donut_2 = $("#donutChartMileage");

  
  function displayMileageInfo(data) {
    var myDonutChart = new Chart(ctx_donut_2, {
                                            type: 'doughnut',
                                            data: data,
                                            options: mileageOptions,
                                          });
    // $('#donutLegend').html(myDonutChart.generateLegend());
  }

  function updateDoughnutChartInfo () {
    $.get("/workout-info.json", displayWorkoutInfo);
    $.get("/mileage-info.json", displayMileageInfo);
  }

  var phones = [{ "mask": "(###) ###-####"}];
    $('.phone').inputmask({
                            mask: phones,
                            greedy: false,
                            definitions: { '#': { validator: "[0-9]", cardinality: 1}} }
  );


  $('input:checkbox.workout').change(updateDoughnutChartInfo);
  $(".run.incompleted-run").on("click", updateDoughnutChartInfo);
  $(".run.completed-run").on("click", updateDoughnutChartInfo);
  $.get("/workout-info.json", displayWorkoutInfo);
  $.get("/mileage-info.json", displayMileageInfo);
});
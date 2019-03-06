function bankBalance(endpoint){
  $.get(endpoint,
          function(data){
            labels = data["dates"];
            values = data["totals"];
            var ctx = document.getElementById(data["element-id"]).getContext("2d");
            var chart = new Chart(ctx, {
                  type: "line",
                  data: {
                      labels: labels,
                      datasets: [{
                        fill: false,
                        borderColor: "#53B5AE",
                        data: values,
                      },
                      ]
                  },
                  options: {
                                  legend: {
                                    display: false
                                  },
                                  animation: {
                                    duration: 2500,
                                  },
                                  title: {
                                    display: true,
                                    fontSize: 30,
                                    padding: 20,
                                    text: "Bank Balance",
                                    fontColor: "black",
                                  },
                                  scales: {
                                              xAxes: [{
                                                ticks: {
                                                    fontSize: 16,
                                                    autoSkip: true,
                                                    maxTicksLimit: 5,
                                                    callback: function(value) {
                                                      return new Date(value).toLocaleDateString("en-EN", {month:"short", year:"numeric"});
                                                    },
                                                },
                                                gridLines: {
                                                    display:false,
                                                    color: "white",
                                                }
                                              }],
                                    yAxes: [
                                        {
                                            id: "Value",
                                            type: "linear",
                                            position: "left",
                                            ticks: {
                                                fontSize: 16,
                                                callback: function(value, index, values) {
                                                  if(parseInt(value) >= 1000){
                                                    var val = value / 1000;
                                                    return "$" + val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                                                  } else {
                                                    return "$" + val;
                                                  }
                                                },
                                            },
                                            gridLines: {
                                                display:false,
                                                color: "white",
                                            },
                                        },
                                    ]
                                  }
                  }
                });
                Chart.defaults.global.defaultFontColor = "#000";
          }
  );
}

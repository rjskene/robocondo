function reserveFundTotal(endpoint){
  $.get(endpoint,
          function(data){
            labels = data["dates"];
            totals = data["totals"]
            expenditures = data["expenditures"]
            var ctx = document.getElementById(data["element-id"]).getContext("2d");
            var chart = new Chart(ctx, {
                  type: "bar",
                  data: {
                      labels: labels,
                      datasets: [
                                  {
                                    yAxisID: "Reserve Fund Total",
                                    type: "line",
                                    backgroundColor: "#53B5AE",
                                    borderColor: "#53B5AE",
                                    data: totals,
                                    fill: false,
                                  },
                                  {
                                    yAxisID: "Expenditures",
                                    type: "bar",
                                    backgroundColor: "#AD304D",
                                    borderColor: "#AD304D",
                                    data: expenditures,
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
                                  elements: { point: { radius: 0 } },
                                  title: {
                                    display: true,
                                    fontSize: 30,
                                    padding: 20,
                                    text: "Reserve Fund Total",
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
                                                    lineWidth: 2,
                                                    color: "white",
                                                }
                                              }],
                                    yAxes: [
                                            {
                                            id: "Reserve Fund Total",
                                            type: "linear",
                                            position: "left",
                                            ticks: {
                                                fontSize: 16,
                                                callback: function(value, index, totals) {
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
                                                lineWidth: 2,
                                                color: "white",
                                            },
                                          },
                                              {
                                                id: "Expenditures",
                                                type: "linear",
                                                position: "right",
                                                ticks: {
                                                    fontSize: 14,
                                                    maxTicksLimit: 4,
                                                    callback: function(value, index, expenditures) {
                                                      if(parseInt(value) >= 1000){
                                                        var val = value / 1000;
                                                        return "$" + val.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                                                      } else if(parseInt(value) <= -1000) {

                                                      } else {
                                                        return "$" + value;
                                                      }

                                                    },
                                                },
                                                gridLines: {
                                                    display:false,
                                                    lineWidth: 2,
                                                    color: "white",
                                                },
                                              }

                                    ]
                                  }
                  }
                });
                Chart.defaults.global.defaultFontColor = "#000";
          }
  );
}

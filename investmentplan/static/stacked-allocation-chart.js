function stackedAllocation(endpoint){
  $.get(endpoint,
    function(data){
      var ctx = document.getElementById(data["element-id"]);
      var chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data['dates'],
                datasets: [
                            {
                              label: 'Bank Account',
                              fill: true,
                              backgroundColor: "orange",
                              data: data['bank_balances'],
                            },
                            {
                              label: 'Term 1',
                              fill: true,
                              backgroundColor: "#8e5ea2",
                              data: data['term_1'],
                              },
                            {
                              label: 'Term 2',
                              fill: true,
                              backgroundColor: 'green',
                              data: data['term_2'],
                              },
                            {
                              label: 'Term 3',
                              fill: true,
                              backgroundColor: "#3e95cd",
                              data: data['term_3'],
                              },
                            {
                              label: 'Term 4',
                              fill: true,
                              backgroundColor: "pink",
                              data: data['term_4'],
                              },
                            {
                              label: 'Term 5',
                              fill: true,
                              backgroundColor: "blue",
                              data: data['term_5'],
                              },
                ]
            },
            options: {
                legend: {
                  display: false
                },
                elements: {
                    point: {
                        radius: 0
                    }
                },
                title: {
                  display: true,
                  fontSize: 30,
                  padding: 20,
                  text: "Investment Allocation",
                  fontColor: "black",
                },
                scales: {
                  xAxes: [
                      {
                        afterTickToLabelConversion: function(scaleInstance) {
                          scaleInstance.ticks[0] = null;
                      },
                      ticks: {
                          maxTicksLimit: 8,
                          fontSize: 16,
                      },
                            gridLines: {
                                display:false
                            },
                  }],
                  yAxes: [
                    {
                    stacked: true,
                    scaleLabel:{
                         display: true,
                         labelString: 'Amount',
                         fontSize: 16
                    },
                    ticks: {
                        fontSize: 16,
                        callback: function(value, index, values) {
                          if(parseInt(value) >= 1000){
                            return '$' + value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                          } else {
                            return '$' + value;
                          }
                        },
                    },
                    gridLines: {
                        display:false
                    },
                  }]
                },
          }
    });
  });
}

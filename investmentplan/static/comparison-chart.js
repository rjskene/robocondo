function comparison(endpoint){
  $.get(endpoint, function(data){
    expenditures = data["expenditures"];
    var ctx = document.getElementById(data["element-id"]).getContext("2d");
    new Chart(ctx, {
        type: 'bar',
        data: {
          labels: data["dates"],
          datasets: [
            {
              label: "Contributions",
              backgroundColor: "#3e95cd",
              data: data["contributions"]
            }, {
              label: "Expenditures",
              backgroundColor: "#8e5ea2",
              data: data["expenditures"]
            }
          ]
        },
        options: {
          title: {
            display: true,
            text: "Contributions vs. Expenditures"
          }
        }
    });
  }
  );
}

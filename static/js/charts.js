new Chart(ctx, {
  type: 'pie',
  data: {
    labels: ['Drilling', 'Mechanical', 'Electrical'],
    datasets: [{
      data: [120, 45, 30]
    }]
  }
});

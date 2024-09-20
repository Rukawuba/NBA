document.addEventListener('DOMContentLoaded', function() {
    // Get the canvas element for the chart
    var ctx = document.getElementById('timeSeriesChart').getContext('2d');

    // Fetch the time series data from the Flask server
    var timeLabels = JSON.parse(document.getElementById('timeLabels').textContent);
    var timeData = JSON.parse(document.getElementById('timeData').textContent);

    // Create the line chart using Chart.js
    var timeSeriesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: 'Total Time (Minutes)',
                data: timeData,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                x: {
                    beginAtZero: true
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
